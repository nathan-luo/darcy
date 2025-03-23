"""Main application for the LLMgine chatbot."""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional

from llmgine.bus import MessageBus
from llmgine.llm.context import InMemoryContextManager
from llmgine.llm.engine import LLMEngine
from llmgine.llm.engine.messages import ClearHistoryCommand, SystemPromptCommand
from llmgine.llm.providers import DefaultLLMManager, DummyProvider
from llmgine.messages.commands import Command
from llmgine.messages.events import Event
from llmgine.llm.tools import ToolManager
from llmgine.ui.cli.interface import CLIInterface
from llmgine.ui.cli.tools import calculator, get_current_time, get_weather

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("llmgine.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ApplicationStartedEvent(Event):
    """Event emitted when the application starts."""

    def __init__(self, tool_count: int):
        super().__init__()
        self.tool_count = tool_count


class ApplicationExitedEvent(Event):
    """Event emitted when the application exits."""
    pass


class ChatbotApp:
    """Main chatbot application class."""

    def __init__(self, system_prompt: Optional[str] = None):
        """Initialize the chatbot application.
        
        Args:
            system_prompt: Optional system prompt to set for the LLM
        """
        # Create message bus
        self.message_bus = MessageBus()

        # Create tool manager and register tools
        self.tool_manager = ToolManager()
        self._register_tools()

        # Create LLM components
        self.llm_manager = DefaultLLMManager()
        self.llm_manager.register_provider("dummy", DummyProvider())
        self.context_manager = InMemoryContextManager()
        
        # Create LLM engine
        self.llm_engine = LLMEngine(
            message_bus=self.message_bus,
            llm_manager=self.llm_manager,
            context_manager=self.context_manager,
            tool_manager=self.tool_manager
        )

        # Set system prompt if provided
        if system_prompt:
            # Create system prompt command
            command = SystemPromptCommand(system_prompt)
            asyncio.create_task(self.message_bus.execute(command))

        # Create CLI interface
        self.cli = CLIInterface(self.message_bus)

        # Create event logger - import locally to avoid circular imports
        from llmgine.observability.logging.event_logger import EventLogger
        logs_dir = os.path.join(os.getcwd(), "logs")
        self.event_logger = EventLogger(self.message_bus, logs_dir)

    def _register_tools(self) -> None:
        """Register available tools with the tool manager."""
        self.tool_manager.register_tool(calculator)
        self.tool_manager.register_tool(get_current_time)
        self.tool_manager.register_tool(get_weather)

        logger.info(f"Registered {len(self.tool_manager.tools)} tools")

    async def run(self) -> None:
        """Run the chatbot application."""
        try:
            # Start the message bus
            await self.message_bus.start()

            # Emit application started event
            await self.message_bus.publish(
                ApplicationStartedEvent(len(self.tool_manager.tools))
            )

            # Run the CLI interface
            await self.cli.run()

        except Exception as e:
            logger.exception(f"Error running chatbot: {e}")
        finally:
            # Emit application exited event
            await self.message_bus.publish(ApplicationExitedEvent())

            # Stop the message bus
            await self.message_bus.stop()


async def main() -> None:
    """Main entry point for the chatbot application."""
    # Create system prompt
    system_prompt = """
    You are a helpful assistant with access to tools.
    When appropriate, use the available tools to provide better answers.
    """

    # Create and run the chatbot
    app = ChatbotApp(system_prompt)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
