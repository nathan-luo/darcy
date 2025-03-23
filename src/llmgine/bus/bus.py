"""Core message bus implementation for handling commands and events.

The message bus is the central communication mechanism in the application,
providing a way for components to communicate without direct dependencies.
"""

import asyncio
import logging
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast

from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import (
    CommandEvent,
    CommandErrorEvent,
    CommandResultEvent,
    Event,
)
from llmgine.observability.bus import ObservabilityBus
from llmgine.observability.events import LogLevel

logger = logging.getLogger(__name__)

TCommand = TypeVar("TCommand", bound=Command)
TEvent = TypeVar("TEvent", bound=Event)
CommandHandler = Callable[[TCommand], CommandResult]
AsyncCommandHandler = Callable[[TCommand], "asyncio.Future[CommandResult]"]
EventHandler = Callable[[TEvent], None]
AsyncEventHandler = Callable[[TEvent], "asyncio.Future[None]"]


class MessageBus:
    """Async message bus for command and event handling.

    This implements the Command Bus and Event Bus patterns, allowing
    for decoupled communication between components.
    """

    def __init__(self, obs_bus: Optional[ObservabilityBus] = None):
        """Initialize the message bus.

        Args:
            obs_bus: The observability bus for logging and metrics
        """
        self._command_handlers: Dict[Type[Command], AsyncCommandHandler] = {}
        self._event_handlers: Dict[Type[Event], List[AsyncEventHandler]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None

        # Connect to the observability bus
        self._obs_bus = obs_bus or ObservabilityBus()

        # Initialize the tracer for command execution
        from llmgine.bus.observability import MessageBusTracer

        self._tracer = MessageBusTracer()

        # Register with observability
        self._register_with_observability()

    def _register_with_observability(self) -> None:
        """Register the message bus with the observability system."""
        # Add a message bus handler to the observability bus
        from llmgine.bus.observability import MessageBusHandler

        # Don't add another handler if we're re-initializing
        for handler in self._obs_bus._handlers:
            if isinstance(handler, MessageBusHandler):
                return

        # Add the handler to observe message bus events
        handler = MessageBusHandler()
        self._obs_bus.add_handler(handler)

        # Log initialization
        self._obs_bus.log(
            LogLevel.INFO, "MessageBus initialized", {"component": "MessageBus"}
        )

    async def start(self) -> None:
        """Start the message bus event processing loop."""
        if self._processing_task is None:
            self._processing_task = asyncio.create_task(self._process_events())
            self._obs_bus.log(
                LogLevel.INFO, "MessageBus started", {"component": "MessageBus"}
            )

    async def stop(self) -> None:
        """Stop the message bus event processing loop."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            self._obs_bus.log(
                LogLevel.INFO, "MessageBus stopped", {"component": "MessageBus"}
            )

    def register_command_handler(
        self, command_type: Type[TCommand], handler: CommandHandler
    ) -> None:
        """Register a command handler for a specific command type.

        Args:
            command_type: The type of command to handle
            handler: The function that handles the command
        """
        async_handler = self._wrap_sync_command_handler(handler)
        if command_type in self._command_handlers:
            raise ValueError(
                f"Command handler for {command_type.__name__} already registered"
            )

        self._command_handlers[command_type] = async_handler
        self._obs_bus.log(
            LogLevel.DEBUG,
            f"Registered command handler for {command_type.__name__}",
            {"component": "MessageBus", "handler_type": "sync"},
        )

    def register_async_command_handler(
        self, command_type: Type[TCommand], handler: AsyncCommandHandler
    ) -> None:
        """Register an async command handler for a specific command type.

        Args:
            command_type: The type of command to handle
            handler: The async function that handles the command
        """
        if command_type in self._command_handlers:
            raise ValueError(
                f"Command handler for {command_type.__name__} already registered"
            )

        self._command_handlers[command_type] = handler
        self._obs_bus.log(
            LogLevel.DEBUG,
            f"Registered async command handler for {command_type.__name__}",
            {"component": "MessageBus", "handler_type": "async"},
        )

    def register_event_handler(
        self, event_type: Type[TEvent], handler: EventHandler
    ) -> None:
        """Register an event handler for a specific event type.

        Args:
            event_type: The type of event to handle
            handler: The function that handles the event
        """
        async_handler = self._wrap_sync_event_handler(handler)
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(async_handler)
        self._obs_bus.log(
            LogLevel.DEBUG,
            f"Registered event handler for {event_type.__name__}",
            {"component": "MessageBus", "handler_type": "sync"},
        )

    def register_async_event_handler(
        self, event_type: Type[TEvent], handler: AsyncEventHandler
    ) -> None:
        """Register an async event handler for a specific event type.

        Args:
            event_type: The type of event to handle
            handler: The async function that handles the event
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        self._obs_bus.log(
            LogLevel.DEBUG,
            f"Registered async event handler for {event_type.__name__}",
            {"component": "MessageBus", "handler_type": "async"},
        )

    async def execute(self, command: Command) -> CommandResult:
        """Execute a command and return the result.

        Args:
            command: The command to execute

        Returns:
            The result of the command execution

        Raises:
            ValueError: If no handler is registered for the command type
        """
        command_type = type(command)
        if command_type not in self._command_handlers:
            error_msg = f"No handler registered for command type {command_type.__name__}"
            self._obs_bus.log(LogLevel.ERROR, error_msg, {"component": "MessageBus"})
            raise ValueError(error_msg)

        handler = self._command_handlers[command_type]

        # Emit command started event
        start_event = CommandEvent(
            command_type=command_type.__name__,
            command_id=command.id,
            command_metadata=command.metadata,
        )
        await self.publish(start_event)

        # Start tracing the command
        self._tracer.start_command_trace(command)

        # Track execution time
        start_time = time.time()

        try:
            # Execute the command
            result = await handler(command)
            execution_time_ms = (time.time() - start_time) * 1000

            # End the trace
            self._tracer.end_command_trace(command.id, result.success, result.error)

            # Emit command result event
            result_event = CommandResultEvent(
                command_type=command_type.__name__,
                command_id=command.id,
                success=result.success,
                result=result.result,
                error=result.error,
                execution_time_ms=execution_time_ms,
            )
            await self.publish(result_event)

            return result

        except Exception as e:
            # Get stack trace
            stack_trace = "".join(traceback.format_exception(type(e), e, e.__traceback__))

            # Track error execution time
            execution_time_ms = (time.time() - start_time) * 1000

            # End the trace with error
            self._tracer.end_command_trace(command.id, False, str(e))

            # Log the error
            self._obs_bus.log(
                LogLevel.ERROR,
                f"Error executing command {command_type.__name__}: {str(e)}",
                {"component": "MessageBus", "command_id": command.id},
            )

            # Emit command error event
            error_event = CommandErrorEvent(
                command_type=command_type.__name__,
                command_id=command.id,
                error=str(e),
                stack_trace=stack_trace,
            )
            await self.publish(error_event)

            return CommandResult(
                command_id=command.id,
                success=False,
                error=str(e),
                metadata={"stack_trace": stack_trace},
            )

    async def publish(self, event: Event) -> None:
        """Publish an event to the message bus.

        The event will be added to the queue and processed asynchronously.

        Args:
            event: The event to publish
        """
        await self._event_queue.put(event)

        event_type = type(event).__name__
        event_info = {}

        # Add more context based on event type
        if hasattr(event, "command_type"):
            event_info["command_type"] = event.command_type
        if hasattr(event, "command_id"):
            event_info["command_id"] = event.command_id
        if hasattr(event, "success"):
            event_info["success"] = event.success
        if hasattr(event, "error"):
            event_info["error"] = event.error
        if hasattr(event, "tool_name"):
            event_info["tool_name"] = event.tool_name

        # Include all context in the log
        log_context = {
            "component": "MessageBus",
            "event_id": str(event.id),
            "event_class": event_type,
            **event_info,
        }
        self._obs_bus.log(
            LogLevel.DEBUG, f"Published event {type(event).__name__}", log_context
        )

    async def _process_events(self) -> None:
        """Process events from the event queue."""
        while True:
            event = await self._event_queue.get()
            try:
                await self._handle_event(event)
            except Exception as e:
                self._obs_bus.log(
                    LogLevel.ERROR,
                    f"Error handling event {type(event).__name__}: {e}",
                    {"component": "MessageBus", "event_id": str(event.id)},
                )
            finally:
                self._event_queue.task_done()

    async def _handle_event(self, event: Event) -> None:
        """Handle an event by dispatching it to registered handlers.

        Args:
            event: The event to handle
        """
        event_type = type(event)
        handlers = []

        # Find handlers for this specific event type
        if event_type in self._event_handlers:
            handlers.extend(self._event_handlers[event_type])

        # Find handlers for parent event types (if event inherits from another registered type)
        for registered_type, type_handlers in self._event_handlers.items():
            if event_type != registered_type and isinstance(event, registered_type):
                handlers.extend(type_handlers)

        # Start trace for event handling
        if handlers:
            span = self._obs_bus.start_trace(
                f"event_handling:{event_type.__name__}",
                {"event_id": str(event.id), "handler_count": len(handlers)},
            )

            # Execute handlers
            tasks = [handler(event) for handler in handlers]
            if tasks:
                await asyncio.gather(*tasks)

            # End trace
            self._obs_bus.end_trace(span, "success")
        else:
            # Log if no handlers found
            # Enhanced logging for the case with no handlers
            event_info = {"event_type": event_type.__name__, "event_id": str(event.id)}

            # Extract additional context based on event type
            if hasattr(event, "command_type"):
                event_info["command_type"] = event.command_type
            if hasattr(event, "command_id"):
                event_info["command_id"] = event.command_id
            if hasattr(event, "success"):
                event_info["success"] = event.success
            if hasattr(event, "error"):
                event_info["error"] = event.error
            if hasattr(event, "tool_name"):
                event_info["tool_name"] = event.tool_name

            # Log with detailed information
            self._obs_bus.log(
                LogLevel.DEBUG,
                f"No handlers registered for event {event_type.__name__}",
                {"component": "MessageBus", **event_info},
            )

    def _wrap_sync_command_handler(self, handler: CommandHandler) -> AsyncCommandHandler:
        """Wrap a synchronous command handler as an async handler.

        Args:
            handler: The synchronous command handler to wrap

        Returns:
            An asynchronous version of the handler
        """
        if asyncio.iscoroutinefunction(handler):
            return cast(AsyncCommandHandler, handler)

        async def async_handler(command: Command) -> CommandResult:
            return handler(command)

        return async_handler

    def _wrap_sync_event_handler(self, handler: EventHandler) -> AsyncEventHandler:
        """Wrap a synchronous event handler as an async handler.

        Args:
            handler: The synchronous event handler to wrap

        Returns:
            An asynchronous version of the handler
        """
        if asyncio.iscoroutinefunction(handler):
            return cast(AsyncEventHandler, handler)

        async def async_handler(event: Event) -> None:
            handler(event)

        return async_handler
