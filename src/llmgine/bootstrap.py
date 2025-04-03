"""Bootstrap utilities for application initialization.

Provides a way to bootstrap the application components including
the observability bus and the message bus.
"""

import asyncio
import logging
import sys  # Added for logging setup
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from llmgine.bus.bus import MessageBus
from llmgine.bus.session import BusSession
from llmgine.messages.commands import Command
from llmgine.messages.events import Event
from llmgine.observability.events import LogLevel, ObservabilityBaseEvent
from llmgine.observability.handlers import (
    ConsoleEventHandler,
    FileEventHandler,
    ObservabilityEventHandler,
)

logger = logging.getLogger(__name__)

# Type definitions
TConfig = TypeVar("TConfig")


# --- Basic Logging Setup Function ---
def setup_basic_logging(level: LogLevel = LogLevel.INFO):
    """Configure basic Python logging to the console."""
    log_level_map = {
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.INFO: logging.INFO,
        LogLevel.WARNING: logging.WARNING,
        LogLevel.ERROR: logging.ERROR,
        LogLevel.CRITICAL: logging.CRITICAL,
    }
    logging_level = log_level_map.get(level, logging.INFO)

    # Configure logging with session_id support
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s - %(name)s - %(levelname)s - [%(session_id)s] %(message)s",
        # stream=sys.stdout # Optionally direct to stdout instead of stderr
    )

    # Add a default filter that adds session_id if not present
    class SessionFilter(logging.Filter):
        def filter(self, record):
            if not hasattr(record, "session_id"):
                record.session_id = "global"
            return True

    # Add the filter to the root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(SessionFilter())

    logger.info(f"Basic logging configured with level {logging_level}")


@dataclass
class ApplicationConfig:
    """Base configuration for applications."""

    # General application config
    name: str = "application"
    description: str = "application description"

    # --- Standard Logging Config ---
    # Controls standard Python logging setup (not MessageBus handlers)
    log_level: LogLevel = LogLevel.INFO

    # --- Observability Handler Config ---
    enable_console_handler: bool = True
    enable_file_handler: bool = True
    file_handler_log_dir: str = "logs"
    file_handler_log_filename: Optional[str] = None  # Default: timestamped events.jsonl
    # custom_handlers: List[ObservabilityEventHandler] = field(default_factory=list) # For adding other handlers

    # --- Removed old MessageBus specific flags ---
    # log_dir: str = "logs"
    # log_filename: Optional[str] = None
    # enable_console_metrics: bool = True
    # metrics_interval: int = 60
    # enable_console_traces: bool = True


class ApplicationBootstrap(Generic[TConfig]):
    """Bootstrap for application initialization.

    Handles setting up the message bus and registering configured
    observability event handlers.
    """

    def __init__(self, config: TConfig = None):
        """Initialize the bootstrap.

        Args:
            config: Application configuration
        """
        self.config = config or ApplicationConfig()

        # --- Configure Standard Logging ---
        # Get log level from config, default to INFO
        log_level_config = getattr(self.config, "log_level", LogLevel.INFO)
        setup_basic_logging(level=log_level_config)
        # --- End Logging Config ---

        # --- Initialize MessageBus (now takes no args) ---
        self.message_bus = MessageBus()

        # --- Create a primary session for this bootstrap ---
        self.primary_session = self.message_bus.create_session()

        # --- Instantiate and Register Handlers based on Config ---
        self._register_observability_handlers()

    def _register_observability_handlers(self) -> None:
        """Instantiate and register observability handlers based on config."""

        console_handler = None
        file_handler = None

        # Standard Console Handler
        if getattr(self.config, "enable_console_handler", True):
            console_handler = ConsoleEventHandler()
            logger.info("ConsoleEventHandler enabled.")

        # Standard File Handler
        if getattr(self.config, "enable_file_handler", True):
            log_dir = getattr(self.config, "file_handler_log_dir", "logs")
            log_filename = getattr(self.config, "file_handler_log_filename", None)
            file_handler = FileEventHandler(log_dir=log_dir, filename=log_filename)
            logger.info(
                f"FileEventHandler enabled (dir={log_dir}, file={log_filename or 'timestamped'})."
            )

        # Custom Handlers registration would go here

        # Register Console Handler for BaseEvent (to see original obs events)
        if console_handler:
            logger.info("Registering ConsoleEventHandler for BaseEvent.")
            # Use the global session for observability handlers
            self.message_bus.register_event_handler(
                "global", ObservabilityBaseEvent, console_handler.handle
            )

        # Register File Handler for EventLogWrapper (to log wrapped events)
        if file_handler:
            # Import EventLogWrapper here locally to avoid circular dependency if BaseEvent wasn't sufficient
            from llmgine.observability.events import EventLogWrapper

            logger.info("Registering FileEventHandler for EventLogWrapper.")
            # Use the global session for observability handlers
            self.message_bus.register_event_handler(
                "global", EventLogWrapper, file_handler.handle
            )

        if not console_handler and not file_handler:
            logger.warning(
                "No standard observability handlers were configured or registered."
            )

    async def bootstrap(self) -> None:
        """Bootstrap the application.

        Starts the message bus, and registers handlers.
        """
        logger.info(
            "Application bootstrap started", extra={"component": "ApplicationBootstrap"}
        )

        # Start message bus
        await self.message_bus.start()

        # Register command and event handlers
        self._register_command_handlers()
        self._register_event_handlers()

        logger.info(
            "Application bootstrap completed", extra={"component": "ApplicationBootstrap"}
        )

    async def shutdown(self) -> None:
        """Shutdown the application components."""
        # Close the primary session
        self.primary_session.__exit__(None, None, None)

        # Stop message bus
        await self.message_bus.stop()

        logger.info(
            "Application shutdown complete", extra={"component": "ApplicationBootstrap"}
        )

    def _register_command_handlers(self) -> None:
        """Register command handlers with the message bus.

        Override this method to register your engine's command handlers.
        """
        pass

    def _register_event_handlers(self) -> None:
        """Register event handlers with the message bus.

        Override this method to register your engine's event handlers.
        """
        pass

    def register_command_handler(
        self, command_type: Type[Command], handler: Callable
    ) -> None:
        """Register a command handler with the message bus.

        Args:
            command_type: The type of command to handle
            handler: The function that handles the command
        """
        # Use the primary session as the default
        self.primary_session.register_command_handler(command_type, handler)

    def register_event_handler(self, event_type: Type[Event], handler: Callable) -> None:
        """Register an event handler with the message bus.

        Args:
            event_type: The type of event to handle
            handler: The function that handles the event
        """
        # Use the primary session as the default
        self.primary_session.register_event_handler(event_type, handler)

    def create_session(self) -> BusSession:
        """Create a new session for session-specific handlers.

        Returns:
            A new BusSession that can be used as a context manager
        """
        return self.message_bus.create_session()


class CommandBootstrap(ApplicationBootstrap[TConfig]):
    """Legacy bootstrap class for backward compatibility."""

    pass
