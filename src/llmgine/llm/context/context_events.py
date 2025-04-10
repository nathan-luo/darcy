from dataclasses import dataclass, field
from typing import Any, Dict, List

from llmgine.messages.events import Event


@dataclass
class ContextEvent(Event):
    """Base class for all context events."""

    engine_id: str = ""
    context_manager_id: str = ""


@dataclass
class ChatHistoryRetrievedEvent(ContextEvent):
    """Event for when chat history is retrieved."""

    context: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ChatHistoryUpdatedEvent(ContextEvent):
    """Event for when chat history is updated."""

    context: List[Dict[str, Any]] = field(default_factory=list)
