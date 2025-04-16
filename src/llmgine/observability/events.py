"""Event types specific to the observability system.

This module contains event types used primarily for observability purposes,
such as logging, tracing, and metrics.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from llmgine.messages.events import Event


class LogLevel(Enum):
    """Standard log levels for observability system."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ObservabilityBaseEvent(Event):
    """Base class for all observability-related events.

    This is the parent class for all events that are specifically for
    observability purposes rather than domain logic. Handlers can register
    for this type to receive all observability events.
    """

    level: LogLevel = LogLevel.INFO


class ToolManagerLogEvent(LogEvent):
    """Event for tool manager logs."""


@dataclass
class EventLogWrapper(Event):
    """Wrapper event for structured event logging.

    This event wraps any other event and is used to log events to
    the structured log file via the FileEventHandler.
    """

    original_event: Optional[Event] = None
    original_event_type: Optional[str] = None
    original_event_data: Dict[str, Any] = field(default_factory=dict)
