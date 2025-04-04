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
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from engines.notion_engine import NotionEngine
from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
from llmgine.observability.events import LogLevel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NotionChatConfig(ApplicationConfig):
    """Configuration for the Notion Chat application."""

    # Application-specific configuration
    name: str = "Notion Chat"
    description: str = "A chat application connected to Notion"

    # OpenAI configuration
    openai_api_key: Optional[str] = None
    model: str = "gpt-4o-mini"

    enable_console_handler = False

    # System prompt
    system_prompt: str = """
    You are Darcy, a Discord bot that is essentially a CRUD interface for the Notion database.
    When you call functions, always do them step by step. For example, if you need to get someone's tasks,
    you should first get all users, then only after that, you should get the tasks for each user.
    """
    enable_tracing: bool = False


class NotionChatBootstrap(ApplicationBootstrap[NotionChatConfig]):
    """Bootstrap for the Notion Chat application."""

    def __init__(self, config: NotionChatConfig):
        """Initialize the bootstrap.

        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.engine: Optional[NotionEngine] = None
        # Generate a unique session ID for this run
        self.current_session_id = str(uuid.uuid4())
        logger.info(f"Starting new chat session: {self.current_session_id}")

    async def initialize_engine(self):
        """Initialize the ToolChatEngine.

        Returns:
            The initialized ToolChatEngine
        """
        # Create the engine with the MessageBus from the bootstrap and the generated session ID
        self.engine = NotionEngine(
            session_id=self.current_session_id,
            api_key=self.config.openai_api_key,
            model=self.config.model,
            system_prompt=self.config.system_prompt,  # Use config prompt directly
        )

        # Register the tools
        await self.engine.register_tools(["notion"])
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
    config = NotionChatConfig(
        name="Notion Chat",
        description="A chat application connected to Notion",
        openai_api_key=args.api_key,
        model=args.model,
        system_prompt=args.system_prompt,
        log_level=getattr(LogLevel, args.log_level.upper()),
        enable_console_handler=not args.no_console,
        file_handler_log_dir=args.log_dir,
    )

    # Create and initialize the bootstrap
    bootstrap = NotionChatBootstrap(config)
    await bootstrap.bootstrap()

    # Initialize the engine through the bootstrap
    engine = await bootstrap.initialize_engine()

    print("\nWelcome to Notion Chat!")
    print(f"Session ID (this run only): {bootstrap.current_session_id}")
    print("Type 'exit', 'quit', or Ctrl+C to end the conversation")
    print("Type '/clear' to clear the conversation history")
    print("\nThis chat has tools for Notion.")
    print(f"Here are the available tools: {engine.tool_manager.tools.keys()}")

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
