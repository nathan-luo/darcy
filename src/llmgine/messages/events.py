"""Events used in the system.

This module defines events that can be published on the message bus.
Events represent things that have happened in the system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, ForwardRef, TYPE_CHECKING
import uuid
import inspect

from llmgine.llm.tools.types import ToolCall
from llmgine.messages.commands import Command, CommandResult


@dataclass
class Event:
    """Base class for all events in the system.

    Events represent things that have happened in the system.
    Multiple handlers can process each event.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None

    def __post_init__(self):
        # Set the session id to GLOBAL if it is not set
        if self.session_id is None:
            self.session_id = "ROOT"

        # Add metadata about where this event was created
        frame = inspect.currentframe().f_back
        if frame:
            module = frame.f_globals.get("__name__", "unknown")
            function = frame.f_code.co_name
            line = frame.f_lineno
            self.metadata["emitted_from"] = f"{module}.{function}:{line}"
        else:
            self.metadata["emitted_from"] = "unknown"


@dataclass
class EventHandlerFailedEvent(Event):
    """Event emitted when an event handler fails."""

    event: Event = None
    handler: str = None
    exception: Exception = None


@dataclass
class CommandStartedEvent(Event):
    """Event emitted when a command is started."""

    command: Command = None


@dataclass
class CommandResultEvent(Event):
    """Event emitted when a command result is created."""

    command_result: CommandResult = None
