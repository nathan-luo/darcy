from typing import Any

from llmgine.llm.providers.response import LLMResponse


class Model:
    def generate(self, **kwargs: Any) -> LLMResponse:
        raise NotImplementedError
