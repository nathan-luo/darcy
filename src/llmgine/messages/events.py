"""Events used in the system.

This module defines events that can be published on the message bus.
Events represent things that have happened in the system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from llmgine.messages.commands import Command, CommandResult


@dataclass
class Event:
    """Base class for all events in the system.
    
    Events represent things that have happened in the system.
    Multiple handlers can process each event.
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandEvent(Event):
    """Event emitted when a command starts executing."""
    
    command_type: str = ""
    command_id: str = ""
    command_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandResultEvent(Event):
    """Event emitted when a command completes execution."""
    
    command_type: str = ""
    command_id: str = ""
    success: bool = False
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


@dataclass
class CommandErrorEvent(Event):
    """Event emitted when a command fails with an error."""
    
    command_type: str = ""
    command_id: str = ""
    error: str = ""
    stack_trace: Optional[str] = None


@dataclass
class LLMResponse:
    """Response from an LLM."""
    
    content: str
    role: str = "assistant"
    model: str = "unknown"
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    tool_calls: Optional[List[Any]] = None