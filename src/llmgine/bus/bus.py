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

    This is a simplified implementation of the Command Bus and Event Bus patterns,
    allowing for decoupled communication between components.
    """

    # --- Singleton Pattern ---
    _instance: Optional["MessageBus"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "MessageBus":
        """Ensure only one instance is created."""
        if cls._instance is None:
            cls._instance = super(MessageBus, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the message bus (only once)."""
        if hasattr(self, "_initialized") and self._initialized:
            return

        # Simplified handler storage - only one session ID concept
        self._command_handlers: Dict[str, Dict[Type[Command], AsyncCommandHandler]] = {}
        self._event_handlers: Dict[
            str, Dict[Type[Event | ObservabilityBaseEvent], List[AsyncEventHandler]]
        ] = {}
        self._event_queue: Optional[asyncio.Queue] = None
        self._processing_task: Optional[asyncio.Task] = None

        # Tracing configuration - enabled by default
        self._tracing_enabled = True

        logger.info("MessageBus initialized with simplified session model")
        self._initialized = True

    @property
    def tracing_enabled(self) -> bool:
        """Return whether tracing is enabled for this message bus."""
        return self._tracing_enabled

    def enable_tracing(self) -> None:
        """Enable tracing for this message bus."""
        if not self._tracing_enabled:
            self._tracing_enabled = True
            logger.info("Tracing enabled for MessageBus")

    def disable_tracing(self) -> None:
        """Disable tracing for this message bus."""
        if self._tracing_enabled:
            self._tracing_enabled = False
            logger.info("Tracing disabled for MessageBus")

    def create_session(self, id: Optional[str] = None):
        """Create a new session for grouping related commands and events."""
        # Import BusSession locally to avoid circular dependency
        from llmgine.bus.session import BusSession

        return BusSession(id=id)

    async def start(self) -> None:
        """Start the message bus event processing loop."""
        if self._processing_task is None:
            if self._event_queue is None:
                self._event_queue = asyncio.Queue()
                logger.info("Event queue created")

            if self._event_queue is not None:
                self._processing_task = asyncio.create_task(self._process_events())
                logger.info("MessageBus started")
            else:
                logger.error("Failed to create event queue, MessageBus cannot start")
        else:
            logger.warning("MessageBus already running")

    async def stop(self) -> None:
        """Stop the message bus event processing loop."""
        if self._processing_task:
            logger.info("Stopping message bus...")
            self._processing_task.cancel()
            try:
                await asyncio.wait_for(self._processing_task, timeout=2.0)
                logger.info("MessageBus stopped successfully")
            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.warning(f"MessageBus stop issue: {type(e).__name__}")
            except Exception as e:
                logger.exception(f"Error during MessageBus shutdown: {e}")
            finally:
                self._processing_task = None
        else:
            logger.info("MessageBus already stopped or never started")

    def register_command_handler(
        self,
        session_id: str,
        command_type: Type[TCommand],
        handler: CommandHandler,
    ) -> None:
        """Register a command handler for a specific command type and session."""
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
            f"Registered command handler for {command_type.__name__} in session {session_id}"
        )

    def register_event_handler(
        self, session_id: str, event_type: Type[TEvent], handler: EventHandler
    ) -> None:
        """Register an event handler for a specific event type and session."""
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
            f"Registered event handler for {event_type.__name__} in session {session_id}"
        )

    def unregister_session_handlers(self, session_id: str) -> None:
        """Unregister all command and event handlers for a specific session."""
        if session_id in self._command_handlers:
            num_cmd_handlers = len(self._command_handlers[session_id])
            del self._command_handlers[session_id]
            logger.debug(
                f"Unregistered {num_cmd_handlers} command handlers for session {session_id}"
            )

        if session_id in self._event_handlers:
            num_event_handlers = sum(
                len(handlers) for handlers in self._event_handlers[session_id].values()
            )
            del self._event_handlers[session_id]
            logger.debug(
                f"Unregistered {num_event_handlers} event handlers for session {session_id}"
            )

    # --- Observability Methods ---

    async def start_span(
        self,
        name: str,
        parent_context: Optional[SpanContext] = None,
        attributes: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> SpanContext:
        """Starts a new trace span and publishes the start event."""
        # If tracing is disabled, return a dummy span context without publishing events
        if not self._tracing_enabled:
            return SpanContext(
                trace_id=str(uuid.uuid4()),
                span_id=str(uuid.uuid4()),
                parent_span_id=parent_context.span_id if parent_context else None,
            )

        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        else:
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
            source=source or "MessageBus.start_span",
        )
        await self.publish(start_event)
        return span_context

    async def end_span(
        self,
        span_context: SpanContext,
        name: str,
        status: str = "OK",
        attributes: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
        source: Optional[str] = None,
    ) -> None:
        """Ends a trace span and publishes the end event."""
        # If tracing is disabled, do nothing
        if not self._tracing_enabled:
            return

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
            source=source or "MessageBus.end_span",
        )
        await self.publish(end_event)

    async def emit_metric(
        self,
        name: str,
        value: Union[int, float],
        unit: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        source: Optional[str] = None,
    ) -> None:
        """Creates and publishes a single metric event."""
        # Metrics are still published even when tracing is disabled
        metric = Metric(name=name, value=value, unit=unit, tags=tags or {})
        metric_event = MetricEvent(
            metrics=[metric],
            source=source or "MessageBus.emit_metric",
        )
        await self.publish(metric_event)

    # --- Command Execution and Event Publishing ---

    async def execute(self, command: Command) -> CommandResult:
        """Execute a command and return its result."""
        command_type = type(command)

        # --- Session ID Handling ---
        session_token = None
        # Use the current session ID from context if available and command doesn't have one
        if not command.session_id:
            command.session_id = current_session_id.get() or str(uuid.uuid4())

        # Set the context variable for the duration of command execution
        # This ensures events published during command execution inherit the session ID
        session_token = current_session_id.set(command.session_id)
        # --- End Session ID Handling ---

        # Find handler - first check specific session, then fall back to global
        handler = None
        if command.session_id in self._command_handlers:
            handler = self._command_handlers[command.session_id].get(command_type)

        # If no session-specific handler, try global
        if handler is None and "global" in self._command_handlers:
            handler = self._command_handlers["global"].get(command_type)

        if handler is None:
            logger.error(
                f"No handler registered for command type {command_type.__name__}"
            )
            raise ValueError(f"No handler registered for command {command_type.__name__}")

        # --- Tracing Setup ---
        span_name = f"Execute Command: {command_type.__name__}"
        parent_context = current_span_context.get()
        span_context = None
        trace_token = None
        start_time = time.time()

        try:
            # Start span (only if tracing is enabled)
            if self._tracing_enabled:
                span_attributes = {
                    "command_id": command.id,
                    "command_type": command_type.__name__,
                    "command_metadata": getattr(command, "metadata", {}),
                    "session_id": command.session_id,
                }
                span_context = await self.start_span(
                    name=span_name,
                    parent_context=parent_context,
                    attributes=span_attributes,
                    source="MessageBus.execute",
                )
                trace_token = current_span_context.set(span_context)

            logger.info(f"Executing command {command_type.__name__}")
            result = await handler(command)

            # End span (success) - only if tracing is enabled
            if self._tracing_enabled and span_context:
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

            logger.info(f"Command {command_type.__name__} executed successfully")
            return result

        except Exception as e:
            # End span (exception) - only if tracing is enabled
            if self._tracing_enabled and span_context:
                duration_ms = (time.time() - start_time) * 1000
                error_attributes = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "stack_trace": "".join(
                        traceback.format_exception(type(e), e, e.__traceback__)
                    ),
                    "execution_time_ms": duration_ms,
                }

                await self.end_span(
                    span_context=span_context,
                    name=span_name,
                    status="EXCEPTION",
                    attributes=error_attributes,
                    error=e,
                    source="MessageBus.execute",
                )

            logger.exception(f"Error executing command {command_type.__name__}: {e}")

            # Create a failed CommandResult
            failed_result = CommandResult(
                success=False,
                original_command=command,
                error=f"{type(e).__name__}: {str(e)}",
                metadata={
                    "exception_details": error_attributes.get("stack_trace", "N/A")
                    if "error_attributes" in locals()
                    else traceback.format_exc()
                },
            )
            return failed_result

        finally:
            if trace_token is not None:
                current_span_context.reset(trace_token)
            if session_token is not None:
                current_session_id.reset(session_token)

    async def publish(self, event: Event | ObservabilityBaseEvent) -> None:
        """Publish an event onto the event queue and potentially a logging wrapper."""

        # --- Simple Session ID Handling ---
        # Only inherit session ID if the event has a session_id attribute and it's None
        if hasattr(event, "session_id") and event.session_id is None:
            session_id = current_session_id.get()
            if session_id:
                event.session_id = session_id
        # --- End Session ID Handling ---

        # Get current span and session ID for logging/metadata
        current_span = current_span_context.get()
        event_session_id = getattr(event, "session_id", None)

        # Add metadata if available (use setdefault to avoid overwriting existing)
        if hasattr(event, "metadata") and isinstance(event.metadata, dict):
            if current_span:
                event.metadata.setdefault("trace_id", current_span.trace_id)
                event.metadata.setdefault("span_id", current_span.span_id)
            if event_session_id:
                event.metadata.setdefault("session_id", event_session_id)

        logger.info(f"Publishing event {type(event).__name__}")

        try:
            # Determine if the event is observational or a log wrapper itself
            is_log_or_observability = isinstance(
                event, (EventLogWrapper, ObservabilityBaseEvent)
            )

            if is_log_or_observability:
                # If it's already a log/observability event, just queue it directly.
                await self._event_queue.put(event)
                logger.debug(
                    f"Queued observability/log event directly: {type(event).__name__}"
                )
            else:
                # For regular application events:
                # 1. Create and publish the EventLogWrapper for logging purposes.
                original_event_type_name = type(event).__name__
                try:
                    original_event_data = self._event_to_dict(event)
                except Exception as e:
                    logger.error(
                        f"Failed to serialize event {original_event_type_name}: {e}"
                    )
                    original_event_data = {
                        "error": "Serialization failed",
                        "event_repr": repr(event),
                    }

                wrapper_kwargs = {
                    "source": "MessageBus.publish",
                    "original_event_type": original_event_type_name,
                    "original_event_data": original_event_data,
                    # Add session_id if the EventLogWrapper class supports it and it exists
                    **(
                        {"session_id": event_session_id}
                        if hasattr(EventLogWrapper, "session_id") and event_session_id
                        else {}
                    ),
                }
                wrapper_event = EventLogWrapper(**wrapper_kwargs)

                # Recursively call publish for the wrapper event.
                # This will hit the `is_log_or_observability` branch in the next call,
                # queueing the wrapper without further recursion.
                await self.publish(wrapper_event)
                logger.debug(f"Published EventLogWrapper for {original_event_type_name}")

                # 2. Queue the original event for its specific handlers.
                await self._event_queue.put(event)
                logger.debug(f"Queued original event: {original_event_type_name}")

        except Exception as e:
            logger.error(f"Error during event publishing: {e}", exc_info=True)

    async def _process_events(self) -> None:
        """Process events from the queue indefinitely."""
        logger.info("Event processing loop starting")

        while True:
            try:
                # Wait for an event
                event = await self._event_queue.get()
                logger.debug(f"Dequeued event {type(event).__name__}")

                try:
                    await self._handle_event(event)
                except asyncio.CancelledError:
                    logger.warning("Event handling cancelled")
                    raise
                except Exception:
                    logger.exception(f"Error processing event {type(event).__name__}")
                finally:
                    self._event_queue.task_done()

            except asyncio.CancelledError:
                logger.info("Event processing loop cancelled")
                break
            except Exception as e:
                logger.exception(f"Error in event processing loop: {e}")
                await asyncio.sleep(0.1)  # Avoid busy-looping

        logger.info("Event processing loop finished")

    async def _handle_event(self, event: Event | ObservabilityBaseEvent) -> None:
        """Handle a single event by calling all registered handlers."""
        event_type = type(event)
        handlers_to_run = []
        event_session_id = getattr(event, "session_id", None)

        # Set the session context for the duration of event handling
        session_token = None
        if event_session_id:
            session_token = current_session_id.set(event_session_id)

        # Determine handlers to run, prioritizing session-specific ones
        if event_session_id and event_session_id in self._event_handlers:
            for registered_type, handlers in self._event_handlers[
                event_session_id
            ].items():
                if issubclass(event_type, registered_type):
                    handlers_to_run.extend(handlers)

        # Add global handlers
        if "global" in self._event_handlers:
            for registered_type, handlers in self._event_handlers["global"].items():
                if issubclass(event_type, registered_type):
                    # Avoid duplicates
                    handlers_to_run.extend([
                        h for h in handlers if h not in handlers_to_run
                    ])

        # Skip tracing for observability events to avoid loops
        is_observability_event = isinstance(
            event, ObservabilityBaseEvent
        )  # Removed EventLogWrapper from this check
        span_context = None
        trace_token = None

        try:
            # Create span for event handling - only if tracing is enabled and not an observability event
            if self._tracing_enabled and not is_observability_event:
                span_attributes = {
                    "event_id": getattr(event, "id", "N/A"),
                    "event_type": event_type.__name__,
                    "event_metadata": getattr(event, "metadata", {}),
                    "num_handlers": len(handlers_to_run),
                    "session_id": event_session_id,
                }
                span_context = await self.start_span(
                    name=f"Handle Event: {event_type.__name__}",
                    parent_context=current_span_context.get(),
                    attributes=span_attributes,
                    source="MessageBus._handle_event",
                )
                trace_token = current_span_context.set(span_context)

            # Execute handlers
            if handlers_to_run:
                logger.debug(
                    f"Dispatching event {event_type.__name__} to {len(handlers_to_run)} handlers"
                )

                # Run all handlers concurrently
                tasks = [
                    asyncio.create_task(handler(event)) for handler in handlers_to_run
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Log errors
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        handler_name = getattr(
                            handlers_to_run[i], "__qualname__", repr(handlers_to_run[i])
                        )
                        logger.exception(
                            f"Error in handler '{handler_name}' for {event_type.__name__}: {result}"
                        )
            else:
                logger.debug(f"No handlers for event type {event_type.__name__}")

            # End span if created - only if tracing is enabled
            if self._tracing_enabled and not is_observability_event and span_context:
                await self.end_span(
                    span_context=span_context,
                    name=f"Handle Event: {event_type.__name__}",
                    status="OK",
                    source="MessageBus._handle_event",
                )

        except Exception as e:
            # Handle span error - only if tracing is enabled
            if self._tracing_enabled and not is_observability_event and span_context:
                await self.end_span(
                    span_context=span_context,
                    name=f"Handle Event: {event_type.__name__}",
                    status="EXCEPTION",
                    error=e,
                    source="MessageBus._handle_event",
                )
            logger.exception(f"Error handling event {event_type.__name__}")

        finally:
            # Reset trace context
            if trace_token is not None:
                current_span_context.reset(trace_token)
            # Reset session context
            if session_token is not None:
                current_session_id.reset(session_token)

    def _wrap_handler_as_async(self, handler: Callable) -> Callable:
        """Convert synchronous handlers to asynchronous if needed."""
        if asyncio.iscoroutinefunction(handler):
            return handler

        async def async_wrapper(*args, **kwargs):
            return handler(*args, **kwargs)

        return async_wrapper

    def _event_to_dict(self, event: Any) -> Dict[str, Any]:
        """Convert an event to a dictionary for serialization."""
        # Try custom to_dict method
        if hasattr(event, "to_dict") and callable(event.to_dict):
            try:
                return event.to_dict()
            except Exception:
                logger.warning(f"Error calling to_dict on {type(event)}", exc_info=True)

        # Try dataclasses.asdict
        try:
            return asdict(
                event, dict_factory=lambda x: {k: self._convert_value(v) for k, v in x}
            )
        except TypeError:
            pass  # Not a dataclass

        # Use __dict__
        if hasattr(event, "__dict__"):
            return {
                k: self._convert_value(v)
                for k, v in event.__dict__.items()
                if not k.startswith("_")
            }

        # Fallback
        logger.warning(f"Could not serialize {type(event)} to dict, using repr()")
        return {"event_repr": repr(event)}

    def _convert_value(self, value: Any) -> Any:
        """Convert values for serialization."""
        if isinstance(value, Enum):
            return value.value
        elif isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, dict):
            return {str(k): self._convert_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple, set)):
            return [self._convert_value(item) for item in value]
        elif hasattr(value, "to_dict") and callable(value.to_dict):
            try:
                return value.to_dict()
            except Exception:
                pass
        elif hasattr(value, "__dict__") or hasattr(value, "__dataclass_fields__"):
            return self._event_to_dict(value)
        else:
            try:
                return str(value)
            except Exception:
                return repr(value)
