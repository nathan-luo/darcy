"""Core message bus implementation for handling commands and events.

The message bus is the central communication mechanism in the application,
providing a way for components to communicate without direct dependencies.
"""

import asyncio
from datetime import datetime
import logging
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast, Union
from dataclasses import asdict
from enum import Enum
import contextvars

from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import (
    Event,
)
from llmgine.observability.events import (
    ObservabilityBaseEvent as ObservabilityBaseEvent,
    Metric,
    MetricEvent,
    SpanContext,
    TraceEvent,
    uuid,
    EventLogWrapper,
)
from llmgine.bus.session import BusSession


# Create a logger adapter that ensures session_id is always present
class SessionLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that ensures session_id is always present in log records."""

    def process(self, msg, kwargs):
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        if "session_id" not in kwargs["extra"]:
            kwargs["extra"]["session_id"] = "global"
        return msg, kwargs


# Get the base logger and wrap it with the adapter
base_logger = logging.getLogger(__name__)
logger = SessionLoggerAdapter(base_logger, {})

# Context variable to hold the current span context
current_span_context: contextvars.ContextVar[Optional[SpanContext]] = (
    contextvars.ContextVar("current_span_context", default=None)
)
# Context variable to hold the current session ID
current_session_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_session_id", default=None
)

TCommand = TypeVar("TCommand", bound=Command)
TEvent = TypeVar("TEvent", bound=Event | ObservabilityBaseEvent)
CommandHandler = Callable[[TCommand], CommandResult]
AsyncCommandHandler = Callable[[TCommand], "asyncio.Future[CommandResult]"]
EventHandler = Callable[[TEvent], None]
AsyncEventHandler = Callable[[TEvent], "asyncio.Future[None]"]


class MessageBus:
    """Async message bus for command and event handling (Singleton).

    This implements the Command Bus and Event Bus patterns, allowing
    for decoupled communication between components.
    """

    # --- Singleton Pattern ---
    _instance: Optional["MessageBus"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "MessageBus":
        """Ensure only one instance is created."""
        if cls._instance is None:
            cls._instance = super(MessageBus, cls).__new__(cls)
            # Mark as not initialized yet, __init__ will handle it
            cls._instance._initialized = False
        return cls._instance

    # --- End Singleton Pattern ---

    def __init__(self):
        """Initialize the message bus (only once)."""
        # --- Singleton Initialization Guard ---
        if hasattr(self, "_initialized") and self._initialized:
            return
        # --- End Guard ---

        # Restructured to organize by session_id -> command/event type -> handler
        self._command_handlers: Dict[str, Dict[Type[Command], AsyncCommandHandler]] = {}
        self._event_handlers: Dict[
            str, Dict[Type[Event | ObservabilityBaseEvent], List[AsyncEventHandler]]
        ] = {}
        self._event_queue: Optional[asyncio.Queue] = (
            None  # Initialize queue later in start()
        )
        self._processing_task: Optional[asyncio.Task] = None

        logger.info("MessageBus initialized (Observability via registered handlers)")

        # --- Mark as initialized ---
        self._initialized = True

    def create_session(self) -> BusSession:
        """Create a new session for grouping related commands and events.

        Usage:
            with message_bus.create_session() as session:
                session.register_event_handler(...)
                session.register_command_handler(...)
                # ... use session ...
                # On exit, all handlers for this session will be unregistered

        Returns:
            A new BusSession object that can be used as a context manager
        """
        # Need to import BusSession locally to avoid circular dependency
        # during initial module load potentially triggered by singleton creation
        # before session module might be fully processed.
        from llmgine.bus.session import BusSession

        return BusSession()

    async def start(self) -> None:
        """Start the message bus event processing loop."""
        if self._processing_task is None:
            # Create the queue here to ensure it uses the current event loop
            if self._event_queue is None:
                self._event_queue = asyncio.Queue()
                logger.info("Event queue created.", extra={"component": "MessageBus"})

            if self._event_queue is not None:  # Ensure queue was created
                self._processing_task = asyncio.create_task(self._process_events())
                logger.info("MessageBus started", extra={"component": "MessageBus"})
            else:
                logger.error(
                    "Failed to create event queue, MessageBus cannot start processing task.",
                    extra={"component": "MessageBus"},
                )
        else:
            logger.warning(
                "MessageBus processing task already running or start called multiple times.",
                extra={"component": "MessageBus"},
            )

    async def stop(self) -> None:
        """Stop the message bus event processing loop."""
        if self._processing_task:
            logger.info(
                "Attempting to cancel message bus processing task...",
                extra={"component": "MessageBus"},
            )
            self._processing_task.cancel()
            try:
                # Wait for the task to finish, but with a timeout
                await asyncio.wait_for(self._processing_task, timeout=2.0)
                logger.info(
                    "Message bus processing task cancelled successfully.",
                    extra={"component": "MessageBus"},
                )
            except asyncio.CancelledError:
                logger.info(
                    "Message bus processing task was cancelled as expected.",
                    extra={"component": "MessageBus"},
                )
            except asyncio.TimeoutError:
                logger.error(
                    "Message bus processing task did not finish within timeout after cancellation.",
                    extra={"component": "MessageBus"},
                )
            except Exception as e:
                logger.exception(
                    f"Error during message bus processing task cleanup: {e}",
                    extra={"component": "MessageBus"},
                )
            finally:
                self._processing_task = None
                logger.info(
                    "MessageBus stop sequence complete.",
                    extra={"component": "MessageBus"},
                )
        else:
            logger.info(
                "MessageBus already stopped or never started.",
                extra={"component": "MessageBus"},
            )

    def register_command_handler(
        self,
        session_id: str,
        command_type: Type[TCommand],
        handler: CommandHandler,
    ) -> None:
        """Register a command handler for a specific command type and session.

        Args:
            session_id: The session ID to use for the command
            command_type: The type of command to handle
            handler: The function that handles the command
        """
        session_id = session_id or "global"

        # Ensure the session exists in the handlers dictionary
        if session_id not in self._command_handlers:
            self._command_handlers[session_id] = {}

        # Convert sync handler to async if needed
        async_handler = self._wrap_handler_as_async(handler)

        # Make sure there isn't already a handler for this command type in this session
        if command_type in self._command_handlers[session_id]:
            raise ValueError(
                f"Command handler for {command_type.__name__} already registered in session {session_id}"
            )

        self._command_handlers[session_id][command_type] = async_handler
        logger.debug(
            f"Registered command handler for {command_type.__name__} in session {session_id}",
            extra={"component": "MessageBus", "session_id": session_id},
        )

    def register_event_handler(
        self, session_id: str, event_type: Type[TEvent], handler: EventHandler
    ) -> None:
        """Register an event handler for a specific event type and session.

        Args:
            session_id: The session ID to use for the events
            event_type: The type of event to handle
            handler: The function that handles the event
        """
        session_id = session_id or "global"

        # Ensure the session exists in the handlers dictionary
        if session_id not in self._event_handlers:
            self._event_handlers[session_id] = {}

        # Ensure the event type exists for this session
        if event_type not in self._event_handlers[session_id]:
            self._event_handlers[session_id][event_type] = []

        # Convert sync handler to async if needed
        async_handler = self._wrap_handler_as_async(handler)

        # Add the handler to the list for this event type
        self._event_handlers[session_id][event_type].append(async_handler)

        logger.debug(
            f"Registered event handler for {event_type.__name__} in session {session_id}",
            extra={"component": "MessageBus", "session_id": session_id},
        )

    def unregister_session_handlers(self, session_id: str) -> None:
        """Unregister all command and event handlers for a specific session.

        Args:
            session_id: The session ID whose handlers should be unregistered
        """
        if session_id in self._command_handlers:
            # Count the number of command handlers being removed
            num_cmd_handlers = len(self._command_handlers[session_id])
            # Remove all command handlers for this session
            del self._command_handlers[session_id]
            logger.debug(
                f"Unregistered {num_cmd_handlers} command handlers for session {session_id}",
                extra={"component": "MessageBus", "session_id": session_id},
            )

        if session_id in self._event_handlers:
            # Count the number of event handlers being removed
            num_event_handlers = sum(
                len(handlers) for handlers in self._event_handlers[session_id].values()
            )
            # Remove all event handlers for this session
            del self._event_handlers[session_id]
            logger.debug(
                f"Unregistered {num_event_handlers} event handlers for session {session_id}",
                extra={"component": "MessageBus", "session_id": session_id},
            )

    # --- Explicit Observability Methods ---

    async def start_span(
        self,
        name: str,
        parent_context: Optional[SpanContext] = None,
        attributes: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,  # Allow overriding the source
    ) -> SpanContext:
        """Starts a new trace span and publishes the start event."""
        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        else:
            # Try getting from context var if not explicitly passed
            ctx_parent = current_span_context.get()
            if ctx_parent:
                trace_id = ctx_parent.trace_id
                parent_span_id = ctx_parent.span_id
            else:
                trace_id = str(uuid.uuid4())
                parent_span_id = None

        span_id = str(uuid.uuid4())
        span_context = SpanContext(
            trace_id=trace_id, span_id=span_id, parent_span_id=parent_span_id
        )

        start_event = TraceEvent(
            name=name,
            span_context=span_context,
            start_time=datetime.now().isoformat(),
            attributes=attributes or {},
            source=source or "MessageBus.start_span",  # Default source
        )
        await self.publish(start_event)
        return span_context

    async def end_span(
        self,
        span_context: SpanContext,
        name: str,  # Name needed again to ensure consistency
        status: str = "OK",
        attributes: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
        source: Optional[str] = None,  # Allow overriding the source
    ) -> None:
        """Ends a trace span, calculates duration, and publishes the end event."""
        # We need the start event to calculate duration reliably,
        # but storing it is complex. Let's approximate or accept inaccuracy.
        # A better way would involve passing start_time or retrieving the start event.
        # For now, we'll mark duration as None or calculate if possible (requires storing start times)
        # This implementation won't calculate duration accurately without start time.

        final_attributes = attributes or {}
        if error:
            status = "EXCEPTION"
            final_attributes.update({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "stack_trace": "".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                ),
            })

        end_event = TraceEvent(
            name=name,
            span_context=span_context,
            end_time=datetime.now().isoformat(),
            duration_ms=None,  # Duration calculation requires start time
            status=status,
            attributes=final_attributes,
            source=source or "MessageBus.end_span",  # Default source
        )
        await self.publish(end_event)

    async def emit_metric(
        self,
        name: str,
        value: Union[int, float],
        unit: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        source: Optional[str] = None,  # Allow overriding the source
    ) -> None:
        """Creates and publishes a single metric event."""
        metric = Metric(name=name, value=value, unit=unit, tags=tags or {})
        metric_event = MetricEvent(
            metrics=[metric],
            source=source or "MessageBus.emit_metric",  # Default source
        )
        await self.publish(metric_event)

    # --- End Explicit Observability Methods ---

    async def execute(self, command: Command) -> CommandResult:
        """Execute a command and return its result."""
        command_type = type(command)

        # --- Session ID Handling ---
        session_token: Optional[contextvars.Token] = None
        # Prioritize command's own session_id, then context var, then generate new
        command_session_id = command.session_id
        if not command_session_id:
            command_session_id = current_session_id.get()

        if command_session_id is None:
            # If no session ID exists in command or context, start a new one
            command_session_id = str(uuid.uuid4())
            logger.info(
                f"Starting new session {command_session_id} for command {command_type.__name__}",
                extra={
                    "session_id": command_session_id,
                    "command_type": command_type.__name__,
                    "command_id": command.id,
                },
            )
        # Ensure the command object has the session ID
        command.session_id = command_session_id
        # Set the context var for handlers/events triggered by this command
        session_token = current_session_id.set(command_session_id)
        # --- End Session ID Handling ---

        # Find handler - first check specific session, then fall back to global
        handler = None
        if command_session_id in self._command_handlers:
            handler = self._command_handlers[command_session_id].get(command_type)

        # If no session-specific handler, try global
        if handler is None and "global" in self._command_handlers:
            handler = self._command_handlers["global"].get(command_type)

        if handler is None:
            logger.error(
                f"No handler registered for command type {command_type.__name__}",
                extra={
                    "component": "MessageBus",
                    "command_id": command.id,
                    "session_id": command_session_id,
                },
            )
            raise ValueError(f"No handler registered for command {command_type.__name__}")

        # --- Tracing Setup ---
        span_name = f"Execute Command: {command_type.__name__}"
        parent_context = current_span_context.get()  # Get context from parent caller
        span_context: Optional[SpanContext] = None  # Initialize
        trace_token: Optional[contextvars.Token] = (
            None  # Renamed from 'token' to avoid clash
        )
        start_time = time.time()  # For duration calculation

        try:
            # --- Start Span and Set Context ---
            span_attributes = {
                "command_id": command.id,
                "command_type": command_type.__name__,
                "command_metadata": getattr(command, "metadata", {}),
                "session_id": command.session_id,  # Add session_id to trace
            }
            span_context = await self.start_span(
                name=span_name,
                parent_context=parent_context,  # Pass parent context here
                attributes=span_attributes,
                source="MessageBus.execute",
            )
            trace_token = current_span_context.set(
                span_context
            )  # Set context for handler
            # --- End Span Start ---

            logger.info(
                f"Executing command {command_type.__name__}",
                extra={
                    "component": "MessageBus",
                    "command_id": command.id,
                    "session_id": command.session_id,  # Log session ID
                    "trace_id": span_context.trace_id if span_context else "N/A",
                    "span_id": span_context.span_id if span_context else "N/A",
                },
            )

            result = await handler(command)

            # --- End Span (Success) ---
            duration_ms = (time.time() - start_time) * 1000
            end_span_attributes = {
                "result_success": result.success,
                "result_metadata": result.metadata,
                "execution_time_ms": duration_ms,
            }
            if result.error:
                end_span_attributes["error"] = result.error
            await self.end_span(
                span_context=span_context,
                name=span_name,
                status="OK" if result.success else "ERROR",
                attributes=end_span_attributes,
                source="MessageBus.execute",
            )
            # --- End Span End ---

            logger.info(
                f"Command {command_type.__name__} executed successfully",
                extra={
                    "component": "MessageBus",
                    "command_id": command.id,
                    "session_id": command.session_id,  # Log session ID
                    "trace_id": span_context.trace_id if span_context else "N/A",
                    "span_id": span_context.span_id if span_context else "N/A",
                    "duration_ms": duration_ms,
                },
            )
            return result

        except Exception as e:
            # --- End Span (Exception) ---
            duration_ms = (time.time() - start_time) * 1000
            error_attributes = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "stack_trace": "".join(
                    traceback.format_exception(type(e), e, e.__traceback__)
                ),
                "execution_time_ms": duration_ms,
            }
            if span_context:  # Only end span if it was successfully started
                await self.end_span(
                    span_context=span_context,
                    name=span_name,
                    status="EXCEPTION",
                    attributes=error_attributes,
                    error=e,
                    source="MessageBus.execute",
                )
            # --- End Span End ---

            logger.exception(
                f"Error executing command {command_type.__name__}: {e}",
                extra={
                    "component": "MessageBus",
                    "command_id": command.id,
                    "session_id": command.session_id,  # Log session ID
                    "trace_id": span_context.trace_id if span_context else "N/A",
                    "span_id": span_context.span_id if span_context else "N/A",
                },
            )
            # Create a failed CommandResult
            failed_result = CommandResult(
                success=False,
                original_command=command,
                error=f"{type(e).__name__}: {str(e)}",
                metadata={
                    "exception_details": error_attributes.get("stack_trace", "N/A")
                },
            )
            # Optionally publish an error event here if needed
            # await self.publish(CommandExecutionFailedEvent(...))
            return failed_result  # Return failure result instead of raising

        finally:
            # Reset context variables even if errors occurred
            if trace_token is not None:
                current_span_context.reset(trace_token)
            if session_token is not None:
                current_session_id.reset(session_token)

    async def publish(self, event: Event | ObservabilityBaseEvent) -> None:
        """Publish an event onto the event queue."""

        # --- Session ID Handling ---
        # If the event doesn't have a session ID, try to inherit from context
        if hasattr(event, "session_id") and event.session_id is None:
            context_session_id = current_session_id.get()
            if context_session_id:
                event.session_id = context_session_id
                logger.debug(
                    f"Event {type(event).__name__} inherited session ID {event.session_id} from context",
                    extra={
                        "component": "MessageBus",
                        "event_id": getattr(event, "id", "N/A"),
                        "session_id": event.session_id,
                    },
                )
        # --- End Session ID Handling ---

        # --- Logging/Tracing Context ---
        current_span = current_span_context.get()  # For trace context propagation
        event_session_id = getattr(event, "session_id", None)  # Get session_id if exists

        # Add trace and session context to event metadata if not already present
        if hasattr(event, "metadata") and isinstance(event.metadata, dict):
            if current_span and "trace_id" not in event.metadata:
                event.metadata["trace_id"] = current_span.trace_id
                event.metadata["span_id"] = current_span.span_id
                if current_span.parent_span_id:
                    event.metadata["parent_span_id"] = current_span.parent_span_id
            if event_session_id and "session_id" not in event.metadata:
                event.metadata["session_id"] = event_session_id
        # --- End Context Handling ---

        # Log the publication attempt
        logger.debug(
            f"Publishing event {type(event).__name__}",
            extra={
                "component": "MessageBus",
                "event_id": getattr(event, "id", "N/A"),
                "session_id": event_session_id
                or "global",  # Log session ID with fallback
                "trace_id": current_span.trace_id if current_span else "N/A",
                "span_id": current_span.span_id if current_span else "N/A",
            },
        )

        try:
            # Handle EventLogWrapper specially - just queue it directly
            if isinstance(event, EventLogWrapper):
                await self._event_queue.put(event)
                return

            # For other event types, create the wrapper with proper session ID
            original_event_type_name = type(event).__name__
            try:
                original_event_data = self._event_to_dict(event)
            except Exception as e:
                logger.error(
                    f"Failed to serialize event {original_event_type_name} for wrapper: {e}",
                    extra={
                        "event_id": getattr(event, "id", "N/A"),
                        "session_id": event_session_id or "global",
                    },
                    exc_info=True,
                )
                original_event_data = {
                    "error": "Serialization failed",
                    "event_repr": repr(event),
                }

            # Create the wrapper event, explicitly listing all parameters
            kwargs = {
                "source": "MessageBus.publish",
                "original_event_type": original_event_type_name,
                "original_event_data": original_event_data,
            }

            # Only add session_id if the EventLogWrapper class supports it
            if hasattr(EventLogWrapper, "session_id"):
                kwargs["session_id"] = event_session_id

            wrapper_event = EventLogWrapper(**kwargs)

            # Add the wrapper event to the queue
            await self._event_queue.put(wrapper_event)

        except Exception as e:
            logger.error(
                f"Error preparing event for queue: {e}",
                extra={
                    "event_type": type(event).__name__,
                    "session_id": event_session_id or "global",
                },
                exc_info=True,
            )

    async def _process_events(self) -> None:
        """Process events from the queue indefinitely."""
        logger.info("Event processing loop starting.", extra={"component": "MessageBus"})
        while True:
            try:
                # Wait for an event indefinitely
                event = await self._event_queue.get()
                logger.debug(
                    f"Dequeued event {type(event).__name__}",
                    extra={
                        "component": "MessageBus",
                        "event_id": getattr(event, "id", "N/A"),
                    },
                )
                try:
                    await self._handle_event(event)
                except asyncio.CancelledError:
                    logger.warning(
                        "Event handling cancelled.",
                        extra={
                            "component": "MessageBus",
                            "event_id": getattr(event, "id", "N/A"),
                        },
                    )
                    # Re-raise the cancellation to stop the loop if needed
                    raise
                except Exception:
                    logger.exception(
                        f"Unhandled error processing event {type(event).__name__}",
                        extra={
                            "component": "MessageBus",
                            "event_id": getattr(event, "id", "N/A"),
                        },
                    )
                finally:
                    # Crucially, mark the task as done even if handling failed or was cancelled
                    self._event_queue.task_done()
                    logger.debug(
                        f"Event queue task_done called for {type(event).__name__}",
                        extra={
                            "component": "MessageBus",
                            "event_id": getattr(event, "id", "N/A"),
                        },
                    )

            except asyncio.CancelledError:
                logger.info(
                    "Event processing loop cancelled.", extra={"component": "MessageBus"}
                )
                break  # Exit the loop if the task is cancelled
            except Exception as e:
                # Catch potential errors in queue.get() itself, though unlikely
                logger.exception(
                    f"Error in event processing loop: {e}",
                    extra={"component": "MessageBus"},
                )
                # Avoid busy-looping on persistent errors; add a small delay
                await asyncio.sleep(0.1)

        logger.info("Event processing loop finished.", extra={"component": "MessageBus"})

    async def _handle_event(self, event: Event | ObservabilityBaseEvent) -> None:
        """Handle a single event by calling all registered handlers."""
        event_type = type(event)
        handlers_to_run: List[AsyncEventHandler] = []

        # --- Determine which handlers should process the event ---
        # Get the event's session ID if it has one
        event_session_id = getattr(event, "session_id", None)

        # First add handlers from the event's specific session if applicable
        if event_session_id and event_session_id in self._event_handlers:
            for registered_type, handlers in self._event_handlers[
                event_session_id
            ].items():
                if issubclass(event_type, registered_type):
                    handlers_to_run.extend(handlers)

        # Then add global handlers that should process all events of this type
        if "global" in self._event_handlers:
            for registered_type, handlers in self._event_handlers["global"].items():
                if issubclass(event_type, registered_type):
                    # Avoid adding handlers twice
                    handlers_to_run.extend([
                        h for h in handlers if h not in handlers_to_run
                    ])

        # --- Session ID Handling ---
        session_token: Optional[contextvars.Token] = None
        if event_session_id:
            # If the event has a session ID, set it in the context for its handlers
            session_token = current_session_id.set(event_session_id)
        # --- End Session ID Handling ---

        # --- Skip Tracing for Observability Events ---
        # Avoid recursive tracing loops: don't trace the handling of observability events themselves.
        is_observability_event = isinstance(
            event, (ObservabilityBaseEvent, EventLogWrapper)
        )

        # --- Tracing Setup (only if not an observability event) ---
        trace_token: Optional[contextvars.Token] = None
        parent_context = current_span_context.get()  # Check if we're already in a span
        span_context: Optional[SpanContext] = None  # Initialize
        span_name = f"Handle Event: {event_type.__name__}"
        # --- End Tracing Setup ---

        try:
            if not is_observability_event:
                # --- Start Span if not already in one (or create child span) ---
                # Decide if event handling itself should be a span. Often useful.
                span_attributes = {
                    "event_id": getattr(event, "id", "N/A"),
                    "event_type": event_type.__name__,
                    "event_metadata": getattr(event, "metadata", {}),
                    "num_handlers": len(handlers_to_run),
                    "session_id": event_session_id,  # Add session_id to trace
                }
                # Use start_span which handles parent context correctly
                span_context = await self.start_span(
                    name=span_name,
                    parent_context=parent_context,  # Will become child if parent exists
                    attributes=span_attributes,
                    source="MessageBus._handle_event",
                )
                trace_token = current_span_context.set(
                    span_context
                )  # Set context for handlers
                # --- End Span Start ---

            # --- Execute Handlers ---
            if handlers_to_run:
                # Log dispatch only once, regardless of tracing
                logger.debug(
                    f"Dispatching event {event_type.__name__} to {len(handlers_to_run)} handlers",
                    extra={
                        "component": "MessageBus",
                        "event_id": getattr(event, "id", "N/A"),
                        "session_id": event_session_id,
                        "trace_id": span_context.trace_id if span_context else "N/A",
                        "span_id": span_context.span_id if span_context else "N/A",
                    },
                )

                # Create tasks for each handler to run concurrently
                tasks = [
                    asyncio.create_task(handler(event)) for handler in handlers_to_run
                ]

                # Wait for all tasks to complete, gathering results/exceptions
                # Using return_exceptions=True ensures all tasks run even if some fail
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Log any exceptions from handlers
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        # Ensure the original handler function is identifiable in logs
                        # Use __qualname__ for nested functions/methods, fallback to repr
                        handler_func = handlers_to_run[i]
                        handler_name = getattr(handler_func, "__qualname__", None)
                        if not handler_name and hasattr(
                            handler_func, "func"
                        ):  # Handle wrapped sync funcs
                            handler_name = getattr(
                                handler_func.func, "__qualname__", repr(handler_func.func)
                            )
                        if not handler_name:  # Fallback if still not found
                            handler_name = repr(handler_func)

                        logger.exception(
                            f"Error in event handler '{handler_name}' for {event_type.__name__}: {result}",
                            extra={
                                "component": "MessageBus",
                                "event_id": getattr(event, "id", "N/A"),
                                "session_id": event_session_id,  # Log session ID
                                "trace_id": span_context.trace_id
                                if span_context
                                else "N/A",
                                "span_id": span_context.span_id
                                if span_context
                                else "N/A",
                            },
                        )
                        # Optionally: Publish a specific HandlerFailedEvent here
                        # await self.publish(EventHandlerFailedEvent(...))
            else:
                # Log lack of handlers only once
                logger.debug(
                    f"No handlers registered for event type {event_type.__name__} or its parents",
                    extra={
                        "component": "MessageBus",
                        "event_id": getattr(event, "id", "N/A"),
                        "session_id": event_session_id,
                        "trace_id": span_context.trace_id if span_context else "N/A",
                        "span_id": span_context.span_id if span_context else "N/A",
                    },
                )
            # --- End Execute Handlers ---

            if not is_observability_event:
                # --- End Span (Success) ---
                if span_context:  # Ensure span was started
                    await self.end_span(
                        span_context=span_context,
                        name=span_name,
                        status="OK",  # Assume OK unless an exception occurred below
                        source="MessageBus._handle_event",
                    )
                # --- End Span End ---

        except Exception as e:
            if not is_observability_event:
                # --- End Span (Exception) ---
                # This catches errors in the _handle_event logic itself (e.g., starting span)
                if span_context:  # Ensure span was started
                    await self.end_span(
                        span_context=span_context,
                        name=span_name,
                        status="EXCEPTION",
                        error=e,
                        source="MessageBus._handle_event",
                    )
                # --- End Span End ---
            # Log the error regardless of tracing status
            logger.exception(
                f"Unhandled error processing event {type(event).__name__}",
                extra={
                    "component": "MessageBus",
                    "event_id": getattr(event, "id", "N/A"),
                    "session_id": event_session_id,  # Log session ID
                    "trace_id": span_context.trace_id if span_context else "N/A",
                    "span_id": span_context.span_id if span_context else "N/A",
                },
            )
        finally:
            # Reset context variables
            if trace_token is not None:
                current_span_context.reset(trace_token)
            if session_token is not None:
                current_session_id.reset(session_token)

    def _wrap_handler_as_async(self, handler: Callable) -> Callable:
        """Wrap any handler (command or event) to be async if it's not already.

        This simplifies handler registration by automatically converting sync handlers to async.
        """
        if asyncio.iscoroutinefunction(handler):
            return handler

        # Create an async wrapper for the synchronous handler
        async def async_wrapper(*args, **kwargs):
            return handler(*args, **kwargs)

        return async_wrapper

    def _event_to_dict(self, event: Any) -> Dict[str, Any]:
        """Convert an event (dataclass or object) to a dictionary for serialization."""
        # Prefers a custom to_dict if available
        if hasattr(event, "to_dict") and callable(event.to_dict):
            try:
                return event.to_dict()
            except Exception:
                logger.warning(f"Error calling to_dict on {type(event)}", exc_info=True)
                # Fall through to other methods

        # Use dataclasses.asdict if possible
        try:
            return asdict(
                event, dict_factory=lambda x: {k: self._convert_value(v) for k, v in x}
            )
        except TypeError:
            pass  # Not a dataclass

        # Handle basic objects with __dict__, excluding private/protected attrs
        if hasattr(event, "__dict__"):
            return {
                k: self._convert_value(v)
                for k, v in event.__dict__.items()
                if not k.startswith("_")
            }

        # Fallback for unknown types
        logger.warning(
            f"Could not serialize event of type {type(event)} to dict, using repr()."
        )
        return {"event_repr": repr(event)}

    def _convert_value(self, value: Any) -> Any:
        """Helper for _event_to_dict to handle nested structures and special types."""
        if isinstance(value, Enum):
            return value.value
        elif isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, dict):
            # Ensure keys are strings for JSON compatibility
            return {str(k): self._convert_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple, set)):  # Handle sets too
            return [self._convert_value(item) for item in value]
        elif hasattr(value, "to_dict") and callable(value.to_dict):
            # Use custom to_dict for nested objects if available
            try:
                return value.to_dict()
            except Exception:
                logger.warning(
                    f"Error calling nested to_dict on {type(value)}", exc_info=True
                )
                # Fall through to other methods
        elif hasattr(value, "__dict__") or hasattr(value, "__dataclass_fields__"):
            # Recursively convert nested objects/dataclasses
            return self._event_to_dict(value)
        else:
            # Attempt to convert other types to string
            try:
                return str(value)
            except Exception:
                logger.warning(
                    f"Could not convert type {type(value)} to string, using repr()"
                )
                return repr(value)
