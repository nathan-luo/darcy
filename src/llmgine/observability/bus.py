"""Core observability bus implementation.

The observability bus is the central component for handling logging, metrics, and tracing.
It provides a unified interface for all observability concerns.
"""

import asyncio
import inspect
import logging
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
)

from llmgine.observability.events import (
    BaseEvent,
    LogEvent,
    LogLevel,
    Metric,
    MetricEvent,
    SpanContext,
    TraceEvent,
)

# These will be imported inside methods to avoid circular imports
# from llmgine.observability.handlers import ConsoleLogHandler, JsonFileHandler, ObservabilityHandler

logger = logging.getLogger(__name__)

TEvent = TypeVar("TEvent", bound=BaseEvent)
EventHandler = Callable[[TEvent], None]
AsyncEventHandler = Callable[[TEvent], "asyncio.Future[None]"]


class ObservabilityBus:
    """Central bus for handling observability events.

    This bus manages logging, metrics, and tracing and allows for
    extensible handlers for each type of event.
    """

    _instance: Optional["ObservabilityBus"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "ObservabilityBus":
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(ObservabilityBus, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_dir: str = "logs"):
        """Initialize the observability bus.

        Args:
            log_dir: Directory for logs
        """
        # Only initialize once due to singleton pattern
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self._event_handlers: Dict[Type[BaseEvent], List[AsyncEventHandler]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task = None
        self._handlers: List[Any] = []  # Will store ObservabilityHandler instances

        # Setup log directory
        self.log_dir = Path(log_dir)

        # Initialize default handlers (delayed to avoid circular imports)
        self._setup_default_handlers(log_dir)

    def _setup_default_handlers(self, log_dir: str) -> None:
        """Set up default handlers for observability events.

        Args:
            log_dir: Directory for logs
        """
        # Import here to avoid circular imports
        from llmgine.observability.handlers import (
            ConsoleLogHandler,
            JsonFileHandler,
            ConsoleMetricsHandler,
            ConsoleTraceHandler,
        )

        # Add console handlers for different event types
        self.add_handler(ConsoleLogHandler())  # For logs
        self.add_handler(ConsoleMetricsHandler())  # For metrics
        self.add_handler(ConsoleTraceHandler())  # For traces

        # Add JSON file handler (for all events)
        self.add_handler(JsonFileHandler(log_dir=log_dir))

        # QUESTION: Where is logging going to if this is the logging bus?
        logger.info(
            f"Observability bus initialized with handlers: {[h.__class__.__name__ for h in self._handlers]}"
        )

    async def start(self) -> None:
        """Start the observability bus event processing loop."""
        if self._processing_task is None:
            self._processing_task = asyncio.create_task(self._process_events())
            logger.info("Observability bus started")

    async def stop(self) -> None:
        """Stop the observability bus event processing loop."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            logger.info("Observability bus stopped")

    def add_handler(self, handler: Any) -> None:
        """Add a handler to the bus.

        Args:
            handler: The handler to add
        """
        # Late import to avoid circular imports
        from llmgine.observability.handlers import ObservabilityHandler

        if not isinstance(handler, ObservabilityHandler):
            raise TypeError(
                f"Handler must be an ObservabilityHandler, got {type(handler)}"
            )

        # Add to our list of handlers
        self._handlers.append(handler)

        # Register with the event system
        self.register_event_handler(handler.event_type, handler.handle_sync)

    def remove_handler(self, handler: Any) -> None:
        """Remove a handler from the bus.

        Args:
            handler: The handler to remove
        """
        if handler in self._handlers:
            self._handlers.remove(handler)
            # Note: We don't unregister from event handlers list as that's more complex

    def add_log_handler(self, handler: Any) -> None:
        """Add a handler specifically for log events.

        This is a convenience method for adding handlers that target LogEvent.

        Args:
            handler: The handler to add
        """
        from llmgine.observability.handlers import ObservabilityHandler
        from llmgine.observability.events import LogEvent

        # Create a handler if a raw function was passed
        if callable(handler) and not isinstance(handler, ObservabilityHandler):
            from llmgine.observability.handlers.base import ObservabilityHandler

            class FunctionLogHandler(ObservabilityHandler[LogEvent]):
                def __init__(self, func: Callable) -> None:
                    super().__init__()
                    self.func = func

                def _get_event_type(self) -> Type[LogEvent]:
                    return LogEvent

                async def handle(self, event: LogEvent) -> None:
                    self.func(event)

            handler = FunctionLogHandler(handler)

        self.add_handler(handler)

    def add_metric_handler(self, handler: Any) -> None:
        """Add a handler specifically for metric events.

        This is a convenience method for adding handlers that target MetricEvent.

        Args:
            handler: The handler to add
        """
        from llmgine.observability.handlers import ObservabilityHandler
        from llmgine.observability.events import MetricEvent

        # Create a handler if a raw function was passed
        if callable(handler) and not isinstance(handler, ObservabilityHandler):
            from llmgine.observability.handlers.base import ObservabilityHandler

            class FunctionMetricHandler(ObservabilityHandler[MetricEvent]):
                def __init__(self, func: Callable) -> None:
                    super().__init__()
                    self.func = func

                def _get_event_type(self) -> Type[MetricEvent]:
                    return MetricEvent

                async def handle(self, event: MetricEvent) -> None:
                    self.func(event)

            handler = FunctionMetricHandler(handler)

        self.add_handler(handler)

    def add_trace_handler(self, handler: Any) -> None:
        """Add a handler specifically for trace events.

        This is a convenience method for adding handlers that target TraceEvent.

        Args:
            handler: The handler to add
        """
        from llmgine.observability.handlers import ObservabilityHandler
        from llmgine.observability.events import TraceEvent

        # Create a handler if a raw function was passed
        if callable(handler) and not isinstance(handler, ObservabilityHandler):
            from llmgine.observability.handlers.base import ObservabilityHandler

            class FunctionTraceHandler(ObservabilityHandler[TraceEvent]):
                def __init__(self, func: Callable) -> None:
                    super().__init__()
                    self.func = func

                def _get_event_type(self) -> Type[TraceEvent]:
                    return TraceEvent

                async def handle(self, event: TraceEvent) -> None:
                    self.func(event)

            handler = FunctionTraceHandler(handler)

        self.add_handler(handler)

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
        logger.debug(f"Registered event handler for {event_type.__name__}")

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
        logger.debug(f"Registered async event handler for {event_type.__name__}")

    async def publish(self, event: BaseEvent) -> None:
        """Publish an event to the observability bus.

        The event will be added to the queue and processed asynchronously.

        Args:
            event: The event to publish
        """
        await self._event_queue.put(event)

    def log(
        self, level: LogLevel, message: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a message.

        Args:
            level: The log level
            message: The log message
            context: Additional context for the log event
        """
        event = LogEvent(
            level=level,
            message=message,
            context=context or {},
            source=self._get_caller_info(),
        )
        asyncio.create_task(self.publish(event))

    def metric(
        self,
        name: str,
        value: Union[int, float],
        unit: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a metric.

        Args:
            name: Metric name
            value: Metric value
            unit: Optional unit for the metric
            tags: Optional tags for the metric
        """
        event = MetricEvent(
            metrics=[Metric(name=name, value=value, unit=unit, tags=tags or {})],
            source=self._get_caller_info(),
        )
        asyncio.create_task(self.publish(event))

    def start_trace(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        parent_context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Start a trace span.

        Args:
            name: Name of the trace span
            attributes: Attributes for the span
            parent_context: Optional parent span context

        Returns:
            Span context dictionary for correlation
        """
        span_context = SpanContext()
        if parent_context:
            span_context.parent_span_id = parent_context.get("span_id")
            span_context.trace_id = parent_context.get("trace_id", span_context.trace_id)

        event = TraceEvent(
            name=name,
            span_context=span_context,
            start_time=datetime.now().isoformat(),
            attributes=attributes or {},
            source=self._get_caller_info(),
        )
        asyncio.create_task(self.publish(event))

        return {"trace_id": span_context.trace_id, "span_id": span_context.span_id}

    def end_trace(self, span_context: Dict[str, str], status: str = "OK") -> None:
        """End a trace span.

        Args:
            span_context: The span context from start_trace
            status: Final status of the span
        """
        context = SpanContext(
            trace_id=span_context.get("trace_id", ""),
            span_id=span_context.get("span_id", ""),
        )

        end_time = datetime.now().isoformat()

        event = TraceEvent(
            name="end_span",
            span_context=context,
            end_time=end_time,
            status=status,
            source=self._get_caller_info(),
        )
        asyncio.create_task(self.publish(event))

    def _get_caller_info(self) -> str:
        """Get information about the caller for better context.

        Returns:
            String with caller information
        """
        stack = inspect.stack()
        # Skip this function and its caller (log/metric/trace)
        if len(stack) > 2:
            caller = stack[2]
            return f"{caller.filename}:{caller.lineno}"
        return "unknown"

    async def _process_events(self) -> None:
        """Process events from the event queue."""
        while True:
            event = await self._event_queue.get()
            try:
                await self._handle_event(event)
            except Exception as e:
                logger.exception(f"Error handling event {type(event).__name__}: {e}")
            finally:
                self._event_queue.task_done()

    async def _handle_event(self, event: BaseEvent) -> None:
        """Handle an event by dispatching it to registered handlers.

        Args:
            event: The event to handle
        """
        event_type = type(event)
        handlers = []

        # Find handlers for this specific event type
        if event_type in self._event_handlers:
            handlers.extend(self._event_handlers[event_type])

        # Find handlers for parent event types
        for registered_type, type_handlers in self._event_handlers.items():
            if event_type != registered_type and isinstance(event, registered_type):
                handlers.extend(type_handlers)

        # Execute all handlers
        if handlers:
            tasks = [handler(event) for handler in handlers]
            await asyncio.gather(*tasks)

    def _wrap_sync_event_handler(self, handler: EventHandler) -> AsyncEventHandler:
        """Wrap a synchronous event handler as an async handler.

        Args:
            handler: The synchronous event handler to wrap

        Returns:
            An asynchronous version of the handler
        """
        if asyncio.iscoroutinefunction(handler):
            return cast(AsyncEventHandler, handler)

        async def async_handler(event: BaseEvent) -> None:
            handler(event)

        return async_handler
