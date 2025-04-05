import asyncio
from datetime import timedelta
from enum import Enum
import random
from typing import Any, Awaitable, Callable, Dict, List, Optional

import discord
from discord.ext import commands
from .components import YesNoView

import string


# Session status types
class SessionStatus(Enum):
    STARTING = "starting"
    PROCESSING = "processing"
    WAITING_FOR_INPUT = "waiting_for_input"
    REQUESTING_INPUT = "requesting_input"
    INPUT_RECEIVED = "input_received"
    CONTINUING = "continuing"
    COMPLETED = "completed"
    ERROR = "error"


class SessionManager:
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.id_length = 5

    def generate_session_id(self) -> str:
        """Generate a random alphanumeric session ID"""
        chars = string.ascii_uppercase + string.digits
        session_id = "".join(random.choice(chars) for _ in range(self.id_length))

        # Ensure uniqueness
        while session_id in self.active_sessions:
            session_id = "".join(random.choice(chars) for _ in range(self.id_length))

        return session_id

    async def create_session(
        self,
        message: discord.Message,
        initial_data: Optional[Dict[str, Any]] = None,
        expire_after_minutes: Optional[int] = None,
    ) -> str:
        """Create a new session and return its ID"""
        session_id = self.generate_session_id()

        # Create initial session message
        session_msg = await message.channel.send(
            f"🔄 **Session {session_id} starting...**"
        )

        # Initialize session data
        self.active_sessions[session_id] = {
            "id": session_id,
            "message": message,
            "session_msg": session_msg,
            "author": message.author,
            "channel": message.channel,
            "status": SessionStatus.STARTING,
            "result": None,
            "data": initial_data or {},
            "created_at": discord.utils.utcnow(),
            "updated_at": discord.utils.utcnow(),
        }

        # Schedule expiration if requested
        if expire_after_minutes:
            self.active_sessions[session_id]["expires_at"] = (
                discord.utils.utcnow() + timedelta(minutes=expire_after_minutes)
            )

            # Schedule the expiration task
            self.bot.loop.create_task(
                self._expire_session(session_id, expire_after_minutes)
            )

        return session_id

    # Add this method to handle session expiration
    async def _expire_session(self, session_id: str, minutes: int):
        """Background task to expire a session after a set time"""
        await asyncio.sleep(minutes * 60)  # Convert to seconds

        # Check if session still exists and hasn't been completed yet
        if (
            session_id in self.active_sessions
            and self.active_sessions[session_id]["status"] != SessionStatus.COMPLETED
        ):
            await self.update_session_status(
                session_id,
                SessionStatus.COMPLETED,
                f"Session expired after {minutes} minutes",
            )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by ID"""
        return self.active_sessions.get(session_id)

    def get_sessions_by_status(self, status: SessionStatus) -> List[Dict[str, Any]]:
        """Get all sessions with a specific status"""
        return [
            session
            for session in self.active_sessions.values()
            if session["status"] == status
        ]

    async def update_session_status(
        self, session_id: str, status: SessionStatus, message: Optional[str] = None
    ) -> bool:
        print(
            f"======================Updating session status for {session_id} to {status}======================="
        )
        """Update a session's status and optionally its message"""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]
        session["status"] = status
        session["updated_at"] = discord.utils.utcnow()

        if message:
            status_emoji = {
                SessionStatus.STARTING: "🔄",
                SessionStatus.PROCESSING: "🔄",
                SessionStatus.WAITING_FOR_INPUT: "⏳",
                SessionStatus.REQUESTING_INPUT: "❓",
                SessionStatus.INPUT_RECEIVED: "✓",
                SessionStatus.CONTINUING: "🔄",
                SessionStatus.COMPLETED: "✅",
                SessionStatus.ERROR: "❌",
            }

            emoji = status_emoji.get(status, "🔄")
            await session["session_msg"].edit(
                content=f"{emoji} **Session {session_id}**: {message}"
            )

        return True

    async def update_session_data(
        self, session_id: str, data_updates: Dict[str, Any]
    ) -> bool:
        """Update a session's data dictionary"""
        if session_id not in self.active_sessions:
            return False

        self.active_sessions[session_id]["data"].update(data_updates)
        self.active_sessions[session_id]["updated_at"] = discord.utils.utcnow()
        return True

    async def request_user_input(
        self,
        session_id: str,
        prompt_text: str,
        timeout: int = 60,
        input_type: str = "yes_no",
    ) -> bool:
        """Request input from a user for a specific session"""
        if session_id not in self.active_sessions:
            raise ValueError("Session not found")

        session = self.active_sessions[session_id]

        # Update status
        await self.update_session_status(
            session_id, SessionStatus.REQUESTING_INPUT, "User input requested..."
        )

        result = None

        if input_type == "yes_no":
            # Create the view for Yes/No input
            view = YesNoView(timeout=timeout, original_author=session["author"])
            prompt_msg = await session["channel"].send(
                content=f"⚠️ **Session {session_id}**: {session['author'].mention}, {prompt_text}",
                view=view,
            )

            # Wait for the user to respond
            await view.wait()

            # Process the result
            if view.value is None:
                result = False
                await prompt_msg.edit(content=f"⏱️ Request timed out", view=None)
            else:
                result = view.value
                resp_text = (
                    f"✅ **Session {session_id} Accepted**: {prompt_text}"
                    if view.value
                    else f"❌ **Session {session_id} Declined**: {prompt_text}"
                )
                await prompt_msg.edit(content=f"{resp_text}", view=None)

        # Update session and return result
        await self.update_session_status(session_id, SessionStatus.INPUT_RECEIVED)
        await self.update_session_data(session_id, {"last_input": result})

        return result

    async def complete_session(
        self, session_id: str, final_message: Optional[str] = None
    ) -> bool:
        """Mark a session as completed"""
        if not await self.update_session_status(
            session_id, SessionStatus.COMPLETED, final_message or "Session completed"
        ):
            return False

        # You can choose to keep completed sessions in memory for reference
        # or remove them to free up memory
        # del self.active_sessions[session_id]

        return True

    async def process_session(
        self,
        session_id: str,
        processor_func: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Process a session using the provided async function"""
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}

        session = self.active_sessions[session_id]

        # Update status to processing
        await self.update_session_status(
            session_id, SessionStatus.PROCESSING, "Processing..."
        )

        # Use typing indicator during processing
        async with session["channel"].typing():
            try:
                # Call the provided processing function
                result = await processor_func(session)

                # Update session data with result
                await self.update_session_data(session_id, {"process_result": result})

                return result
            except Exception as e:
                await self.update_session_status(
                    session_id, SessionStatus.ERROR, f"Error during processing: {str(e)}"
                )
                return {"error": str(e)}
