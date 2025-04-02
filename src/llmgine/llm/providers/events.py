from typing import Any, Dict

from llmgine.messages.events import Event


class LLMResponseEvent(Event):
    def __init__(self, session_id: str, engine_id: str, response: Dict[str, Any]):
        super().__init__(session_id=session_id)
        self.engine_id = engine_id
        self.raw_response = response
