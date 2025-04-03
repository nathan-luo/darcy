"""Function Chat Application

This program demonstrates the use of the ToolChatEngine for chat with function calling capabilities.
It registers some sample tools and allows conversational interaction with those tools.
Each run starts a new, temporary chat session.
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
    enable_tracing: bool = False


class FunctionChatBootstrap(ApplicationBootstrap[FunctionChatConfig]):
    """Bootstrap for the Function Chat application."""

    def __init__(self, config: FunctionChatConfig):
        """Initialize the bootstrap.

        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.engine: Optional[ToolChatEngine] = None
        # Generate a unique session ID for this run
        self.current_session_id = str(uuid.uuid4())
        logger.info(f"Starting new chat session: {self.current_session_id}")

    async def initialize_engine(self):
        """Initialize the ToolChatEngine.

        Returns:
            The initialized ToolChatEngine
        """
        # Create the engine with the MessageBus from the bootstrap and the generated session ID
        self.engine = ToolChatEngine(
            session_id=self.current_session_id,
            api_key=self.config.openai_api_key,
            model=self.config.model,
            system_prompt=self.config.system_prompt,  # Use config prompt directly
            message_bus=self.message_bus,
        )

        # Register the tools
        await self.engine.register_tool(get_weather)
        await self.engine.register_tool(send_email)
        await self.engine.register_tool(calculate)

        return self.engine

    async def shutdown(self):
        """Shutdown the bootstrap.

        This method should be overridden to include any additional shutdown logic.
        """
        # Unregister handlers for the engine's session ID
        if self.engine:
            logger.info(
                f"Unregistering handlers for engine session: {self.engine.session_id}"
            )
            self.message_bus.unregister_session_handlers(self.engine.session_id)

        # Shutdown the generic bootstrap (stops message bus, cleans up primary session)
        await super().shutdown()


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
    args = parser.parse_args()

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
    )

    # Create and initialize the bootstrap
    bootstrap = FunctionChatBootstrap(config)
    await bootstrap.bootstrap()

    # Initialize the engine through the bootstrap
    engine = await bootstrap.initialize_engine()

    print("\nWelcome to Function Chat!")
    print(f"Session ID (this run only): {bootstrap.current_session_id}")
    print("Type 'exit', 'quit', or Ctrl+C to end the conversation")
    print("Type '/clear' to clear the conversation history")
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

            # Process the message
            try:
                print("\nAssistant: ", end="", flush=True)
                response = await engine.process_message(user_input)
                print(response)
            except Exception as e:
                print(f"Error: {str(e)}")
                # Reraise the exception to see the full traceback during debugging
                raise

    except KeyboardInterrupt:
        print("\nExiting...")

    finally:
        # Shutdown the bootstrap
        await bootstrap.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
