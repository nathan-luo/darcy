from dataclasses import dataclass, field
from typing import Any, Dict

from llmgine.messages.events import Event


@dataclass
class LLMResponseEvent(Event):
    llm_manager_id: str = ""
    engine_id: str = ""
    raw_response: Dict[str, Any] = field(default_factory=dict)
