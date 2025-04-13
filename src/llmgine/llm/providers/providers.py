from enum import Enum
from typing import Any
from llmgine.llm.providers.response import LLMResponse


class Providers(Enum):
    OPENAI = "openai"
    LITELLM = "litellm"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    VERTEX_AI = "vertex_ai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"


class Provider:
    def generate(self, **kwargs: Any) -> LLMResponse:
        raise NotImplementedError
