"""Console handler for observability events.

This module provides handlers for logging events to the console.
"""

import logging
from typing import Any, Dict, Optional, Type

from llmgine.observability.events import LogEvent, LogLevel
from llmgine.observability.handlers.base import ObservabilityHandler

logger = logging.getLogger(__name__)


class ConsoleLogHandler(ObservabilityHandler[LogEvent]):
    """Handler for logging events to console."""
    
    def __init__(self, min_level: LogLevel = LogLevel.INFO):
        """Initialize the console log handler.
        
        Args:
            min_level: Minimum log level to display
        """
        super().__init__()
        self.min_level = min_level
        
    def _get_event_type(self) -> Type[LogEvent]:
        """Get the event type this handler processes.
        
        Returns:
            The LogEvent class
        """
        return LogEvent
    
    async def handle(self, event: LogEvent) -> None:
        """Handle the log event by writing to console.
        
        Args:
            event: The log event to handle
        """
        if not self.enabled:
            return
            
        # Check if we should log this level
        if self._should_log_level(event.level):
            # Map to Python log levels
            level_map = {
                LogLevel.DEBUG: logging.DEBUG,
                LogLevel.INFO: logging.INFO,
                LogLevel.WARNING: logging.WARNING,
                LogLevel.ERROR: logging.ERROR,
                LogLevel.CRITICAL: logging.CRITICAL,
            }
            
            # Get the python logging level
            python_level = level_map.get(event.level, logging.INFO)
            
            # Format the message with context
            message = self._format_message(event)
            
            # Log to the Python logger
            logger.log(python_level, message)
    
    def _should_log_level(self, level: LogLevel) -> bool:
        """Check if a log level should be displayed.
        
        Args:
            level: The log level to check
            
        Returns:
            True if the level should be logged
        """
        # Compare enum values based on severity
        level_values = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4
        }
        
        # Get the numerical values
        event_value = level_values.get(level, 0)
        min_value = level_values.get(self.min_level, 0)
        
        # Should log if event level is >= minimum level
        return event_value >= min_value
    
    def _format_message(self, event: LogEvent) -> str:
        """Format a log message with context.
        
        Args:
            event: The log event
            
        Returns:
            Formatted message
        """
        message = event.message
        
        # Add source information if available
        if event.source:
            message = f"[{event.source}] {message}"
            
        # Add context as key=value pairs
        if event.context:
            context_str = " ".join(f"{k}={v}" for k, v in event.context.items())
            message = f"{message} {context_str}"
            
        return message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert handler to a dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        base_dict = super().to_dict()
        base_dict["min_level"] = self.min_level.value
        return base_dict