"""Observability integration for MessageBus.

This module provides handlers and adapters to integrate the MessageBus with
the ObservabilityBus.
"""

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Type

from llmgine.messages.commands import Command
from llmgine.messages.events import (
    CommandErrorEvent,
    CommandEvent,
    CommandResultEvent,
    Event,
)
from llmgine.observability.events import LogEvent, LogLevel, MetricEvent, TraceEvent
from llmgine.observability.handlers.base import ObservabilityHandler

logger = logging.getLogger(__name__)


@dataclass
class MessageBusHandler(ObservabilityHandler[Event]):
    """Handler to log MessageBus events to the ObservabilityBus.
    
    This handler translates MessageBus events into ObservabilityBus events.
    """
    
    include_command_events: bool = True
    include_result_events: bool = True
    include_error_events: bool = True
    include_app_events: bool = True
    
    def _get_event_type(self) -> Type[Event]:
        """Get the event type this handler processes.
        
        Returns:
            The Event class
        """
        return Event
    
    async def handle(self, event: Event) -> None:
        """Handle a MessageBus event.
        
        Args:
            event: The event to handle
        """
        if not self.enabled:
            return
        
        # Handle each type of event differently
        if isinstance(event, CommandEvent) and self.include_command_events:
            await self._handle_command_event(event)
        elif isinstance(event, CommandResultEvent) and self.include_result_events:
            await self._handle_result_event(event)
        elif isinstance(event, CommandErrorEvent) and self.include_error_events:
            await self._handle_error_event(event)
        elif self.include_app_events:
            await self._handle_generic_event(event)
    
    async def _handle_command_event(self, event: CommandEvent) -> None:
        """Handle a command event.
        
        Args:
            event: The command event
        """
        from llmgine.observability.bus import ObservabilityBus
        
        # Get the ObservabilityBus instance
        obs_bus = ObservabilityBus()
        
        # Log the event
        obs_bus.log(
            LogLevel.INFO,
            f"Command started: {event.command_type}",
            {
                "command_id": event.command_id,
                "component": "MessageBus",
                **event.command_metadata
            }
        )
        
        # Start a trace span for the command
        obs_bus.start_trace(
            name=f"command:{event.command_type}",
            attributes={
                "command_id": event.command_id,
                "command_type": event.command_type,
                **event.command_metadata
            }
        )
    
    async def _handle_result_event(self, event: CommandResultEvent) -> None:
        """Handle a command result event.
        
        Args:
            event: The command result event
        """
        from llmgine.observability.bus import ObservabilityBus
        
        # Get the ObservabilityBus instance
        obs_bus = ObservabilityBus()
        
        # Log the event
        level = LogLevel.INFO if event.success else LogLevel.WARNING
        message = f"Command completed: {event.command_type}"
        if not event.success and event.error:
            message = f"Command failed: {event.command_type} - {event.error}"
            
        obs_bus.log(
            level,
            message,
            {
                "command_id": event.command_id,
                "success": str(event.success),
                "execution_time_ms": str(event.execution_time_ms),
                "component": "MessageBus"
            }
        )
        
        # Record a metric for the execution time
        if event.execution_time_ms is not None:
            obs_bus.metric(
                name="command_execution_time",
                value=event.execution_time_ms,
                unit="ms",
                tags={
                    "command_type": event.command_type,
                    "success": str(event.success)
                }
            )
    
    async def _handle_error_event(self, event: CommandErrorEvent) -> None:
        """Handle a command error event.
        
        Args:
            event: The command error event
        """
        from llmgine.observability.bus import ObservabilityBus
        
        # Get the ObservabilityBus instance
        obs_bus = ObservabilityBus()
        
        # Log the error event
        obs_bus.log(
            LogLevel.ERROR,
            f"Command error: {event.command_type} - {event.error}",
            {
                "command_id": event.command_id,
                "stack_trace": event.stack_trace,
                "component": "MessageBus"
            }
        )
    
    async def _handle_generic_event(self, event: Event) -> None:
        """Handle a generic event.
        
        Args:
            event: The event
        """
        from llmgine.observability.bus import ObservabilityBus
        
        # Get the ObservabilityBus instance
        obs_bus = ObservabilityBus()
        
        # Log the event
        event_type = type(event).__name__
        obs_bus.log(
            LogLevel.DEBUG,
            f"Event published: {event_type}",
            {
                "event_id": str(event.id),
                "event_type": event_type,
                "component": "MessageBus"
            }
        )


class MessageBusTracer:
    """Trace Manager for MessageBus operations.
    
    This class helps with creating and managing traces for MessageBus operations.
    """
    
    def __init__(self):
        """Initialize the tracer."""
        from llmgine.observability.bus import ObservabilityBus
        self.obs_bus = ObservabilityBus()
        self._active_traces: Dict[str, Dict[str, str]] = {}
    
    def start_command_trace(self, command: Command) -> Dict[str, str]:
        """Start a trace for a command.
        
        Args:
            command: The command to trace
            
        Returns:
            Trace context
        """
        command_type = type(command).__name__
        
        # Start a trace span for the command
        span = self.obs_bus.start_trace(
            name=f"command:{command_type}",
            attributes={
                "command_id": command.id,
                "command_type": command_type,
                **command.metadata
            }
        )
        
        # Store the trace
        self._active_traces[command.id] = span
        
        return span
    
    def end_command_trace(self, command_id: str, success: bool, error: Optional[str] = None) -> None:
        """End a trace for a command.
        
        Args:
            command_id: ID of the command
            success: Whether the command was successful
            error: Optional error message
        """
        if command_id in self._active_traces:
            span = self._active_traces[command_id]
            status = "success" if success else "error"
            
            # End the trace
            self.obs_bus.end_trace(span, status=status)
            
            # Remove from active traces
            del self._active_traces[command_id]