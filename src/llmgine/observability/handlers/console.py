"""Console handler for printing event information."""

import logging
from typing import Any, Dict

from llmgine.messages.events import Event
from llmgine.observability.events import Metric, SpanContext, TraceEvent, MetricEvent
from llmgine.observability.handlers.base import ObservabilityEventHandler

logger = logging.getLogger(__name__)  # Use standard logger


class ConsoleEventHandler(ObservabilityEventHandler):
    """Prints a summary of events to the console using standard logging."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Could add level filtering here if needed

    async def handle(self, event: Event) -> None:
        """Process the event and print relevant information to the console logger."""

        event_type = type(event).__name__
        event_dict = self.event_to_dict(event)

        # Default representation for standard events
        log_level = logging.INFO
        message = f"[EVENT] {event_type}, ID={event.id}"

        try:
            # Handle specialized event types directly

            # Handle TraceEvent
            if isinstance(event, TraceEvent):
                span_context = event.span_context
                name = event.name

                if event.is_start:
                    message = (
                        f"TRACE START: {name} [trace={span_context.trace_id[:8]}] "
                        f"[span={span_context.span_id[:8]}] "
                        f"(parent={span_context.parent_span_id[:8] if span_context.parent_span_id else 'None'})"
                    )
                else:
                    duration_ms = event.duration_ms
                    duration = (
                        f" ({duration_ms:.2f}ms)" if duration_ms is not None else ""
                    )
                    status = event.status or "OK"
                    message = (
                        f"TRACE END: {name} [trace={span_context.trace_id[:8]}] "
                        f"[span={span_context.span_id[:8]}] {status}{duration}"
                    )
                log_level = logging.DEBUG

            # Handle MetricEvent
            elif isinstance(event, MetricEvent):
                messages = []
                for metric in event.metrics:
                    unit_str = f" {metric.unit}" if metric.unit else ""
                    tags_str = (
                        " " + " ".join(f"{k}={v}" for k, v in metric.tags.items())
                        if metric.tags
                        else ""
                    )
                    messages.append(
                        f"METRIC {metric.name}={metric.value}{unit_str}{tags_str}"
                    )
                message = f"[METRICS] {', '.join(messages)}" if messages else message
                log_level = logging.DEBUG

            # Legacy handling for backwards compatibility
            # This allows the handler to still work with events using the old format
            elif (
                hasattr(event, "metrics")
                and isinstance(event.metrics, list)
                and event.metrics
            ):
                messages = []
                for metric in event.metrics:
                    if isinstance(metric, Metric):
                        unit_str = f" {metric.unit}" if metric.unit else ""
                        tags_str = (
                            " " + " ".join(f"{k}={v}" for k, v in metric.tags.items())
                            if metric.tags
                            else ""
                        )
                        messages.append(
                            f"METRIC {metric.name}={metric.value}{unit_str}{tags_str}"
                        )
                if messages:
                    message = f"[METRICS] {', '.join(messages)}"

            # Legacy handling for trace data in regular events (backward compatibility)
            elif (
                hasattr(event, "span_context")
                and isinstance(event.span_context, SpanContext)
                and hasattr(event, "start_time")
                and hasattr(event, "end_time")
            ):
                span_context = event.span_context
                name = getattr(event, "name", event_type)

                if getattr(event, "start_time") and not getattr(event, "end_time"):
                    message = (
                        f"TRACE START: {name} [trace={span_context.trace_id[:8]}] "
                        f"[span={span_context.span_id[:8]}] "
                        f"(parent={span_context.parent_span_id[:8] if span_context.parent_span_id else 'None'})"
                    )
                elif getattr(event, "end_time"):
                    duration_ms = getattr(event, "duration_ms", None)
                    duration = (
                        f" ({duration_ms:.2f}ms)" if duration_ms is not None else ""
                    )
                    status = getattr(event, "status", "OK")
                    message = (
                        f"TRACE END: {name} [trace={span_context.trace_id[:8]}] "
                        f"[span={span_context.span_id[:8]}] {status}{duration}"
                    )

        except Exception as e:
            logger.error(
                f"Error formatting event in ConsoleEventHandler: {e}", exc_info=True
            )
            # Fall back to default message

        # Log the formatted message using the standard logger
        logger.log(log_level, message)
