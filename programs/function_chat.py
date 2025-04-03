"""Function Chat Application

This program demonstrates the use of the ToolChatEngine for chat with function calling capabilities.
It registers some sample tools and allows conversational interaction with those tools.
"""

import asyncio
import os
import json
import uuid
import argparse
import sys
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engines.tool_chat_engine import ToolChatEngine
from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
from llmgine.observability.events import LogLevel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Chat session details."""

    id: str
    name: str
    created_at: str
    system_prompt: str


class SessionManager:
    """Manages chat sessions."""

    def __init__(self, sessions_dir: str = "sessions"):
        """Initialize the session manager.

        Args:
            sessions_dir: Directory to store session files
        """
        self.sessions_dir = sessions_dir
        self.sessions: Dict[str, Session] = {}

        # Create sessions directory if it doesn't exist
        os.makedirs(self.sessions_dir, exist_ok=True)

        # Load existing sessions
        self._load_sessions()

    def _load_sessions(self):
        """Load existing sessions from the sessions directory."""
        for filename in os.listdir(self.sessions_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(self.sessions_dir, filename), "r") as f:
                        session_data = json.load(f)
                        session = Session(
                            id=session_data["id"],
                            name=session_data["name"],
                            created_at=session_data["created_at"],
                            system_prompt=session_data["system_prompt"],
                        )
                        self.sessions[session.id] = session
                except Exception as e:
                    logger.error(f"Error loading session from {filename}: {str(e)}")

    def create_session(self, name: str, system_prompt: str) -> Session:
        """Create a new session.

        Args:
            name: Name of the session
            system_prompt: System prompt for the session

        Returns:
            The newly created session
        """
        from datetime import datetime

        session_id = str(uuid.uuid4())
        session = Session(
            id=session_id,
            name=name,
            created_at=datetime.now().isoformat(),
            system_prompt=system_prompt,
        )

        self.sessions[session_id] = session
        self._save_session(session)

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID.

        Args:
            session_id: The session ID

        Returns:
            The session if found, None otherwise
        """
        return self.sessions.get(session_id)

    def list_sessions(self) -> List[Session]:
        """List all sessions.

        Returns:
            List of all sessions
        """
        return list(self.sessions.values())

    def update_session(
        self,
        session_id: str,
        name: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Optional[Session]:
        """Update a session.

        Args:
            session_id: The session ID
            name: New name for the session (optional)
            system_prompt: New system prompt for the session (optional)

        Returns:
            The updated session if found, None otherwise
        """
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        if name is not None:
            session.name = name

        if system_prompt is not None:
            session.system_prompt = system_prompt

        self._save_session(session)

        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The session ID

        Returns:
            True if the session was deleted, False otherwise
        """
        if session_id not in self.sessions:
            return False

        # Remove from memory
        session = self.sessions.pop(session_id)

        # Delete the file
        filename = os.path.join(self.sessions_dir, f"{session_id}.json")
        if os.path.exists(filename):
            os.remove(filename)

        return True

    def _save_session(self, session: Session):
        """Save a session to disk.

        Args:
            session: The session to save
        """
        filename = os.path.join(self.sessions_dir, f"{session.id}.json")

        try:
            with open(filename, "w") as f:
                json.dump(
                    {
                        "id": session.id,
                        "name": session.name,
                        "created_at": session.created_at,
                        "system_prompt": session.system_prompt,
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Error saving session to {filename}: {str(e)}")


@dataclass
class FunctionChatConfig(ApplicationConfig):
    """Configuration for the Function Chat application."""

    # Application-specific configuration
    name: str = "Function Chat"
    description: str = "A simple chat application with function calling capabilities"

    # OpenAI configuration
    openai_api_key: Optional[str] = None
    model: str = "gpt-4o-mini"

    # System prompt
    system_prompt: str = "You are a helpful assistant with access to tools for weather information, sending emails, and calculating expressions."

    # Session ID (if resuming a session)
    session_id: Optional[str] = None

    # Session name (if creating a new session)
    session_name: str = "Default Session"


class FunctionChatBootstrap(ApplicationBootstrap[FunctionChatConfig]):
    """Bootstrap for the Function Chat application."""

    def __init__(self, config: FunctionChatConfig):
        """Initialize the bootstrap.

        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.session_manager = SessionManager()
        self.engine = None

        # Either get the existing session or create a new one
        if config.session_id:
            self.session = self.session_manager.get_session(config.session_id)
            if not self.session:
                logger.warning(
                    f"Session {config.session_id} not found, creating a new session"
                )
                self.session = self.session_manager.create_session(
                    name=config.session_name, system_prompt=config.system_prompt
                )
        else:
            self.session = self.session_manager.create_session(
                name=config.session_name, system_prompt=config.system_prompt
            )
            logger.info(f"Created new session: {self.session.id} - {self.session.name}")

    async def initialize_engine(self):
        """Initialize the ToolChatEngine.

        Returns:
            The initialized ToolChatEngine
        """
        # Create the engine with the MessageBus from the bootstrap
        self.engine = ToolChatEngine(
            session_id=self.session.id,
            api_key=self.config.openai_api_key,
            model=self.config.model,
            system_prompt=self.session.system_prompt,
            message_bus=self.message_bus,
        )

        # Register the tools
        await self.engine.register_tool(get_weather)
        await self.engine.register_tool(send_email)
        await self.engine.register_tool(calculate)

        return self.engine

    def update_session_prompt(self, system_prompt: str):
        """Update the system prompt for the current session.

        Args:
            system_prompt: The new system prompt
        """
        self.session_manager.update_session(
            session_id=self.session.id, system_prompt=system_prompt
        )
        self.session.system_prompt = system_prompt


# Sample tools for demonstration
async def get_weather(location: str, unit: str = "celsius") -> Dict[str, Any]:
    """Get the current weather in a given location.

    Args:
        location: The city and state, e.g. San Francisco, CA or country e.g. Paris, France
        unit: The unit of temperature, one of (celsius, fahrenheit)

    Returns:
        Dictionary containing weather information
    """
    # This is a mock implementation for demonstration
    weather_data = {
        "San Francisco, CA": {"temperature": 18, "condition": "Foggy", "humidity": 80},
        "New York, NY": {"temperature": 22, "condition": "Partly Cloudy", "humidity": 65},
        "Paris, France": {"temperature": 20, "condition": "Sunny", "humidity": 60},
        "Tokyo, Japan": {"temperature": 25, "condition": "Rainy", "humidity": 85},
    }

    if location in weather_data:
        result = weather_data[location].copy()
        if unit == "fahrenheit":
            result["temperature"] = round(result["temperature"] * 9 / 5 + 32)
        return result
    else:
        return {"error": f"No weather data available for {location}"}


async def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Send an email to a recipient.

    Args:
        to: The email address of the recipient
        subject: The subject of the email
        body: The body content of the email

    Returns:
        Dictionary with status information
    """
    # This is a mock implementation for demonstration
    print(f"\n[MOCK EMAIL SENT]\nTo: {to}\nSubject: {subject}\nBody: {body}\n")
    return {"status": "sent", "to": to, "message_id": str(uuid.uuid4())}


async def calculate(expression: str) -> Dict[str, Any]:
    """Evaluate a mathematical expression.

    Args:
        expression: A mathematical expression as a string, e.g. "2 + 2 * 3"

    Returns:
        Dictionary with the result
    """
    try:
        # Use eval with restricted globals for safety
        result = eval(expression, {"__builtins__": {}}, {})
        return {"result": result}
    except Exception as e:
        return {"error": f"Failed to evaluate expression: {str(e)}"}


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Function Chat Application")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model to use")
    parser.add_argument(
        "--api-key", help="OpenAI API key (or use OPENAI_API_KEY env var)"
    )
    parser.add_argument(
        "--system-prompt",
        default="You are a helpful assistant with access to tools for weather information, sending emails, and calculating expressions.",
        help="System prompt to use for the conversation",
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Log level",
    )
    parser.add_argument("--log-dir", default="logs", help="Directory for log files")
    parser.add_argument(
        "--no-console", action="store_true", help="Disable console output for events"
    )
    parser.add_argument("--session", help="Session ID to resume a previous conversation")
    parser.add_argument(
        "--session-name", default="Default Session", help="Name for a new session"
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List all available sessions and exit",
    )
    args = parser.parse_args()

    # Create a session manager
    session_manager = SessionManager()

    # If we're just listing sessions, do that and exit
    if args.list_sessions:
        sessions = session_manager.list_sessions()
        if not sessions:
            print("No sessions found.")
        else:
            print("Available sessions:")
            for session in sessions:
                print(f"  ID: {session.id}")
                print(f"  Name: {session.name}")
                print(f"  Created: {session.created_at}")
                print(
                    f"  System Prompt: {session.system_prompt[:50]}..."
                    if len(session.system_prompt) > 50
                    else session.system_prompt
                )
                print()
        return

    # Create the application configuration
    config = FunctionChatConfig(
        name="Function Chat",
        description="A simple chat application with function calling capabilities",
        openai_api_key=args.api_key,
        model=args.model,
        system_prompt=args.system_prompt,
        log_level=getattr(LogLevel, args.log_level.upper()),
        enable_console_handler=not args.no_console,
        file_handler_log_dir=args.log_dir,
        session_id=args.session,
        session_name=args.session_name,
    )

    # Create and initialize the bootstrap
    bootstrap = FunctionChatBootstrap(config)
    await bootstrap.bootstrap()

    # Initialize the engine through the bootstrap
    engine = await bootstrap.initialize_engine()

    # Get the current session
    current_session = bootstrap.session

    print("\nWelcome to Function Chat!")
    print(f"Session: {current_session.name} (ID: {current_session.id})")
    print("Type 'exit', 'quit', or Ctrl+C to end the conversation")
    print("Type '/clear' to clear the conversation history")
    print("Type '/system <prompt>' to change the system prompt")
    print("Type '/sessions' to list all available sessions")
    print("\nThis chat has tools for weather, email, and calculation.")
    print("Try asking about the weather in San Francisco or calculating 24*7.")

    try:
        # Main chat loop
        while True:
            # Get user input
            user_input = input("\nYou: ")

            # Check for special commands
            if user_input.lower() in ["exit", "quit"]:
                break
            elif user_input.lower() == "/clear":
                await engine.clear_context()
                print("Conversation history cleared.")
                continue
            elif user_input.lower().startswith("/system "):
                new_system_prompt = user_input[8:].strip()
                # Update session system prompt in both engine and session storage
                engine.set_system_prompt(new_system_prompt)
                bootstrap.update_session_prompt(new_system_prompt)
                print(f"System prompt updated: {new_system_prompt}")
                continue
            elif user_input.lower() == "/sessions":
                sessions = session_manager.list_sessions()
                print("\nAvailable sessions:")
                for session in sessions:
                    if session.id == current_session.id:
                        print(f"* {session.name} (ID: {session.id})")
                    else:
                        print(f"  {session.name} (ID: {session.id})")
                print("\nTo use a session next time, run with: --session <session-id>")
                continue

            # Process the message
            try:
                print("\nAssistant: ", end="", flush=True)
                response = await engine.process_message(user_input)
                print(response)
            except Exception as e:
                print(f"Error: {str(e)}")
                raise e

    except KeyboardInterrupt:
        print("\nExiting...")

    finally:
        # Shutdown the bootstrap
        await bootstrap.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
