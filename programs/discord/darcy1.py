import discord
import asyncio
import random
import string
from discord.ext import commands
from enum import Enum
from typing import Dict, Any, Optional, Callable, Awaitable, List


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
        self, message: discord.Message, initial_data: Optional[Dict[str, Any]] = None
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

        return session_id

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
    ) -> Dict[str, Any]:
        """Request input from a user for a specific session"""
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}

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
                result = {"response": "timeout"}
                await prompt_msg.edit(content=f"⏱️ Request timed out", view=None)
            else:
                result = {"response": "yes" if view.value else "no"}
                resp_text = "✅ Confirmed" if view.value else "❌ Declined"
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


class YesNoView(discord.ui.View):
    def __init__(self, timeout, original_author):
        super().__init__(timeout=timeout)
        self.value = None
        self.original_author = original_author

    async def interaction_check(self, interaction):
        return interaction.user == self.original_author

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction, button):
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(self, interaction, button):
        self.value = False
        await interaction.response.defer()
        self.stop()


# Example usage of the framework
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
session_manager = SessionManager(bot)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message):
        # Create a new session when the bot is mentioned
        session_id = await session_manager.create_session(message)
        print(f"Session created: {session_id}")
        print(message)
        print(message.content)

        # Example showing how to use the process_session function
        async def my_process_function(session):
            # Simulate some work
            await asyncio.sleep(2)
            return {"success": True, "processed_data": "some result"}

        await session_manager.process_session(session_id, my_process_function)

        # Update to waiting for input
        await session_manager.update_session_status(
            session_id,
            SessionStatus.WAITING_FOR_INPUT,
            "Waiting for external command to request input...",
        )

        await session_manager.request_user_input(
            session_id, "Do you want to proceed?", timeout=30
        )

        await session_manager.complete_session(session_id, "Session completed")

    await bot.process_commands(message)


@bot.command(name="input")
async def request_input_command(ctx, session_id):
    """Test command to request input for a specific session"""
    if session_manager.get_session(session_id):
        await ctx.send(f"Requesting input for session {session_id}")

        result = await session_manager.request_user_input(
            session_id, "Do you want to proceed?", timeout=30
        )

        await ctx.send(f"Input result: {result}")

        # Process the result
        if result.get("response") == "yes":
            # Example showing processing after receiving input
            async def continue_processing(session):
                await asyncio.sleep(2)
                return {"completion": "success"}

            await session_manager.process_session(session_id, continue_processing)
            await session_manager.complete_session(
                session_id, "Process completed successfully!"
            )
        else:
            await session_manager.complete_session(session_id, "Process canceled by user")
    else:
        await ctx.send(f"Session {session_id} not found")


import os
import dotenv

dotenv.load_dotenv()
bot.run(os.getenv("DARCY_KEY"))
