"""Bootstrap utilities for application initialization.

Provides a way to bootstrap the application components including
the observability bus and the message bus.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from llmgine.bus import MessageBus
from llmgine.messages.commands import Command
from llmgine.messages.events import Event
from llmgine.observability.bus import ObservabilityBus
from llmgine.observability.events import LogLevel

logger = logging.getLogger(__name__)

# Type definitions
TConfig = TypeVar("TConfig")


@dataclass
class ApplicationConfig:
    """Base configuration for applications."""
    
    # General application config
    system_prompt: Optional[str] = None
    
    # Logging configuration
    log_level: LogLevel = LogLevel.INFO
    log_dir: str = "logs"
    
    # Advanced logging options
    console_logging: bool = True
    file_logging: bool = True
    json_logging: bool = True
    
    # Metrics configuration
    metrics_enabled: bool = True
    metrics_interval: int = 60  # seconds
    
    # Tracing configuration
    tracing_enabled: bool = True
    
    # Custom handlers
    custom_log_handlers: List[Any] = field(default_factory=list)
    custom_metric_handlers: List[Any] = field(default_factory=list)
    custom_trace_handlers: List[Any] = field(default_factory=list)


class ApplicationBootstrap(Generic[TConfig]):
    """Bootstrap for application initialization.
    
    Handles setting up the observability and message buses and 
    connecting all components.
    """

    def __init__(self, config: TConfig = None):
        """Initialize the bootstrap.
        
        Args:
            config: Application configuration
        """
        self.config = config or ApplicationConfig()
        
        # Initialize the observability bus first
        self.obs_bus = ObservabilityBus(
            log_dir=getattr(self.config, "log_dir", "logs")
        )
        
        # Initialize the message bus with reference to the observability bus
        self.message_bus = MessageBus(obs_bus=self.obs_bus)
        
    async def bootstrap(self) -> None:
        """Bootstrap the application.
        
        Starts the observability bus and message bus, and registers handlers.
        """
        # Start observability bus first
        await self.obs_bus.start()
        self.obs_bus.log(
            LogLevel.INFO, 
            "Application bootstrap started",
            {"component": "ApplicationBootstrap"}
        )
        
        # Configure advanced observability options
        self._configure_observability()
        
        # Start message bus
        await self.message_bus.start()
        
        # Register command and event handlers
        self._register_command_handlers()
        self._register_event_handlers()
        
        self.obs_bus.log(
            LogLevel.INFO, 
            "Application bootstrap completed",
            {"component": "ApplicationBootstrap"}
        )

    async def shutdown(self) -> None:
        """Shutdown the application components."""
        # Stop message bus first
        await self.message_bus.stop()
        
        # Then stop observability bus
        await self.obs_bus.stop()
        
        self.obs_bus.log(
            LogLevel.INFO, 
            "Application shutdown complete",
            {"component": "ApplicationBootstrap"}
        )

    def _configure_observability(self) -> None:
        """Configure observability based on configuration."""
        # Configure custom handlers if provided
        if hasattr(self.config, "custom_log_handlers"):
            for handler in getattr(self.config, "custom_log_handlers", []):
                self.obs_bus.register_event_handler(
                    handler.event_type, handler.handler
                )
        
        if hasattr(self.config, "custom_metric_handlers"):
            for handler in getattr(self.config, "custom_metric_handlers", []):
                self.obs_bus.register_event_handler(
                    handler.event_type, handler.handler
                )
                
        if hasattr(self.config, "custom_trace_handlers"):
            for handler in getattr(self.config, "custom_trace_handlers", []):
                self.obs_bus.register_event_handler(
                    handler.event_type, handler.handler
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
        
    def register_command_handler(self, command_type: Type[Command], 
                              handler: Callable) -> None:
        """Register a command handler with the message bus.
        
        Args:
            command_type: The type of command to handle
            handler: The function that handles the command
        """
        if asyncio.iscoroutinefunction(handler):
            self.message_bus.register_async_command_handler(command_type, handler)
        else:
            self.message_bus.register_command_handler(command_type, handler)

    def register_event_handler(self, event_type: Type[Event],
                            handler: Callable) -> None:
        """Register an event handler with the message bus.
        
        Args:
            event_type: The type of event to handle
            handler: The function that handles the event
        """
        if asyncio.iscoroutinefunction(handler):
            self.message_bus.register_async_event_handler(event_type, handler)
        else:
            self.message_bus.register_event_handler(event_type, handler)
            

class CommandBootstrap(ApplicationBootstrap[TConfig]):
    """Legacy bootstrap class for backward compatibility."""
    pass