"""Utility types for observability.

Basic types used in observability system that aren't events themselves.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
import uuid
from datetime import datetime

# Import Event only for type checking to avoid circular imports
if TYPE_CHECKING:
    from llmgine.messages.events import Event
else:
    # Create a minimal Event class for runtime that will be replaced by the real one
    # This helps avoid circular imports while maintaining type safety
    @dataclass
    class Event:
        id: str = field(default_factory=lambda: str(uuid.uuid4()))
        timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
        metadata: Dict[str, Any] = field(default_factory=dict)
        session_id: Optional[str] = None


class LogLevel(Enum):
    """Standard log levels for observability system."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """A metric measurement."""

    name: str
    value: Union[int, float]
    unit: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class SpanContext:
    """Context for distributed tracing."""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None


@dataclass
class ObservabilityBaseEvent(Event):
    """Base class for all observability-related events.

    This is the parent class for all events that are specifically for
    observability purposes rather than domain logic. Handlers can register
    for this type to receive all observability events.
    """

    level: LogLevel = LogLevel.INFO


@dataclass
class EventLogWrapper(Event):
    """Wrapper event for structured event logging.

    This event wraps any other event and is used to log events to
    the structured log file via the FileEventHandler.
    """

    original_event: Optional[Event] = None
    original_event_type: Optional[str] = None
    original_event_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceEvent(ObservabilityBaseEvent):
    """Specialized event for tracing.

    This is used exclusively for trace spans to separate tracing concerns
    from regular application events.
    """

    # Required fields must have defaults since they follow a field with default (level)
    name: str = field(default="unnamed_span")
    span_context: SpanContext = field(default_factory=SpanContext)
    # True if this is a span start event, False if it's an end event
    is_start: bool = True
    # Start and end timestamps - one or both can be populated depending on is_start
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    # Duration in milliseconds (only for end events)
    duration_ms: Optional[float] = None
    # Status (only for end events)
    status: Optional[str] = None
    # Attributes for the span
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricEvent(ObservabilityBaseEvent):
    """Specialized event for metrics.

    This is used exclusively for metrics to separate metric concerns
    from regular application events.
    """

    metrics: List[Metric] = field(default_factory=list)
