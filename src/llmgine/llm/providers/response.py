# parsing a response for a unified interface


from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI
from llmgine.messages.events import ToolCall

# Where to store this?
USAGE_PATH_REGISTRY: Dict[str, Dict[str, List[str]]] = {
    "openai": {
        "prompt_tokens": ["usage", "prompt_tokens"],
        "completion_tokens": ["usage", "completion_tokens"],
        "total_tokens": ["usage", "total_tokens"],
    },
    "anthropic": {
        "prompt_tokens": ["usage", "input_tokens"],
        "completion_tokens": ["usage", "output_tokens"],
        "total_tokens": ["usage", "total_tokens"],
    },
    # Add more providers as needed
}


@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

# Defining exactly what every class must provide
class LLMResponse(ABC):
    @property
    @abstractmethod
    def content(self) -> str: ...

    @property
    @abstractmethod
    def tool_calls(self) -> List[ToolCall]: ...

    @property
    @abstractmethod
    def has_tool_calls(self) -> bool: ...

    @property
    @abstractmethod
    def finish_reason(self) -> str: ...

    @property
    @abstractmethod
    def usage(self) -> Usage: ...

# Generic LLM response parser
class DefaultLLMResponse(LLMResponse):
    def __init__(
        self,
        raw_response: Dict[str, Any],
        content_path: List[str],
        tool_call_path: Optional[List[str]] = None,
        finish_reason_path: Optional[List[str]] = None,
        usage_key: Optional[str] = None,
    ):
        self.raw = raw_response
        self._content_path = content_path
        self._tool_call_path = tool_call_path
        self._finish_reason_path = finish_reason_path
        self._usage_key = usage_key

    def _get_nested(self, path: List[str]) -> Any:
        data = self.raw
        for key in path:
            if isinstance(data, list):
                data = data[int(key)]
            else:
                data = data.get(key, {})
        return data

    @property
    def content(self) -> str:
        return self._get_nested(self._content_path)

    @property
    def tool_calls(self) -> List[ToolCall]:
        if not self._tool_call_path:
            return []
        raw_tool_calls = self._get_nested(self._tool_call_path)
        return [ToolCall.from_dict(call) for call in raw_tool_calls or []]

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)

    @property
    def finish_reason(self) -> str:
        if not self._finish_reason_path:
            return ""
        return self._get_nested(self._finish_reason_path)

    @property
    def usage(self) -> Usage:
        usage_path = USAGE_PATH_REGISTRY.get(self._usage_key, {})
        def get_token_value(name: str) -> int:
            path = usage_path.get(name, [])
            return self._get_nested(path) if path else 0

        return Usage(
            prompt_tokens=get_token_value("prompt_tokens"),
            completion_tokens=get_token_value("completion_tokens"),
            total_tokens=get_token_value("total_tokens"),
        )


# manages OpenAI instance
class OpenAIManager:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        context: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = "gpt-4o-mini",
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> DefaultLLMResponse:
        messages = context 

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature or 0.7,
            max_tokens=max_tokens or 512,
            tools=tools,
            **kwargs,
        )

        raw_response = response.model_dump()

        # returns default llm response from OpenAI instance
        return DefaultLLMResponse(
            raw_response=raw_response,
            content_path=["choices", "0", "message", "content"],
            tool_call_path=["choices", "0", "message", "tool_calls"],
            finish_reason_path=["choices", "0", "finish_reason"],
            usage_key="openai"
        )