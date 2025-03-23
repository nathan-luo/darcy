"""Bootstrap implementation for the CLI chatbot application."""

import asyncio
import logging
import os
from dataclasses import dataclass

from llmgine.bootstrap import ApplicationConfig, MessageBusBootstrap
from llmgine.bus import MessageBus
from llmgine.llm.context import InMemoryContextManager
from llmgine.llm.engine import LLMEngine
from llmgine.llm.engine.messages import (
    ClearHistoryCommand,
    PromptCommand,
    SystemPromptCommand,
    ToolCallEvent,
)
from llmgine.llm.providers import DefaultLLMManager, DummyProvider
from llmgine.llm.tools import ToolManager
from llmgine.observability.logging.event_logger import EventLogger
from llmgine.ui.cli.interface import CLIInterface
from llmgine.ui.cli.tools import calculator, get_current_time, get_weather

logger = logging.getLogger(__name__)


@dataclass
class ChatbotConfig(ApplicationConfig):
    """Configuration for the chatbot application."""
    
    system_prompt: str = """
    You are a helpful assistant with access to tools.
    When appropriate, use the available tools to provide better answers.
    """
    log_file: str = "chatbot.log"
    logs_dir: str = "logs"
    event_logging_enabled: bool = True


class ChatbotBootstrap(MessageBusBootstrap[ChatbotConfig]):
    """Bootstrap for the chatbot application.
    
    Initializes the chatbot components and registers their command handlers.
    """
    
    def __init__(self, config: ChatbotConfig):
        """Initialize the bootstrap.
        
        Args:
            config: Chatbot configuration
        """
        # Create message bus first
        self.message_bus = MessageBus()
        super().__init__(self.message_bus, config)
        
        # Initialize all components
        self.tool_manager = ToolManager()
        self.llm_manager = DefaultLLMManager()
        self.context_manager = InMemoryContextManager()
        self.llm_engine = None  # Will be created during bootstrap
        self.cli = None
        self.event_logger = None

    def _configure_logging(self) -> None:
        """Configure logging for the chatbot."""
        log_level = self.config.log_level
        log_format = self.config.log_format
        log_file = self.config.log_file
        
        # Ensure handlers include both file and stdout
        handlers = [
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
        
        # Configure the root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=handlers
        )
        
        logger.info(f"Logging configured with level {logging.getLevelName(log_level)}")

    async def bootstrap(self) -> None:
        """Bootstrap the chatbot application."""
        # Initialize LLM engine and other components
        self._initialize_components()
        
        # Start message bus and register handlers
        await super().bootstrap()
        
        # Set system prompt if provided
        if self.config.system_prompt:
            command = SystemPromptCommand(self.config.system_prompt)
            await self.message_bus.execute(command)
            
        logger.info("Chatbot bootstrapped successfully")
    
    def _initialize_components(self) -> None:
        """Initialize all components needed for the chatbot."""
        # Register tools
        self._register_tools()
        
        # Register LLM providers
        self.llm_manager.register_provider("dummy", DummyProvider())
        logger.info("Registered dummy LLM provider")
        
        # Initialize LLM engine
        self.llm_engine = LLMEngine(
            message_bus=self.message_bus,
            llm_manager=self.llm_manager,
            context_manager=self.context_manager,
            tool_manager=self.tool_manager
        )
        
        # Initialize CLI interface
        self.cli = CLIInterface(self.message_bus)
        
        # Initialize event logger if enabled
        if self.config.event_logging_enabled:
            logs_dir = os.path.join(os.getcwd(), self.config.logs_dir)
            os.makedirs(logs_dir, exist_ok=True)
            
            self.event_logger = EventLogger(self.message_bus, logs_dir)
            logger.info(f"Event logger initialized with logs directory: {logs_dir}")

    def _register_tools(self) -> None:
        """Register built-in tools."""
        self.tool_manager.register_tool(calculator)
        self.tool_manager.register_tool(get_current_time)
        self.tool_manager.register_tool(get_weather)
        logger.info(f"Registered {len(self.tool_manager.tools)} tools")

    def _register_command_handlers(self) -> None:
        """Register command handlers for the LLM engine."""
        # Register LLM engine command handlers
        self.register_command_handler(
            PromptCommand, self.llm_engine._handle_prompt
        )
        self.register_command_handler(
            SystemPromptCommand, self.llm_engine._handle_system_prompt
        )
        self.register_command_handler(
            ClearHistoryCommand, self.llm_engine._handle_clear_history
        )
        self.register_command_handler(
            ToolCallEvent, self.llm_engine._handle_tool_call_event
        )


class ChatbotApplication:
    """CLI chatbot application."""
    
    def __init__(self, bootstrap: ChatbotBootstrap):
        """Initialize the application with a bootstrap.
        
        Args:
            bootstrap: The bootstrap for the application
        """
        self.bootstrap = bootstrap

    async def start(self) -> None:
        """Start the application."""
        await self.bootstrap.bootstrap()

    async def stop(self) -> None:
        """Stop the application."""
        await self.bootstrap.shutdown()

    async def run(self) -> None:
        """Run the chatbot application."""
        await self.start()
        
        try:
            # Run the CLI interface
            if self.bootstrap.cli:
                await self.bootstrap.cli.run()
            else:
                raise RuntimeError("CLI interface not initialized")
                
        except KeyboardInterrupt:
            logger.info("Chatbot interrupted by user")
        except Exception as e:
            logger.exception(f"Error running chatbot: {e}")
        finally:
            await self.stop()


async def create_and_run_chatbot(config: ChatbotConfig) -> None:
    """Create and run the chatbot application.
    
    Args:
        config: Chatbot configuration
    """
    bootstrap = ChatbotBootstrap(config)
    app = ChatbotApplication(bootstrap)
    await app.run()


def main() -> None:
    """Main entry point for the CLI chatbot application."""
    from asyncio import run
    config = ChatbotConfig()
    run(create_and_run_chatbot(config))