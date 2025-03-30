# parsing a response for a unified interface


from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

# from .tool_call import ToolCall  # assuming ToolCall has a .from_dict method


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


class DefaultLLMResponse(LLMResponse):
    def __init__(
        self,
        raw_response: Dict[str, Any],
        content_path: List[str],
        tool_call_path: Optional[List[str]] = None,
        finish_reason_path: Optional[List[str]] = None,
        usage_path: Optional[Dict[str, List[str]]] = None,
    ):
        """
        content_path: list of keys to navigate to the content
        tool_call_path: list of keys to navigate to tool calls
        finish_reason_path: list of keys to navigate to finish reason
        usage_path: dict with keys 'prompt_tokens', 'completion_tokens', 'total_tokens'
        """
        self.raw = raw_response
        self._content_path = content_path
        self._tool_call_path = tool_call_path
        self._finish_reason_path = finish_reason_path
        self._usage_path = usage_path or {}

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
        def get_token_value(name: str) -> int:
            path = self._usage_path.get(name, [])
            return self._get_nested(path) if path else 0

        return Usage(
            prompt_tokens=get_token_value("prompt_tokens"),
            completion_tokens=get_token_value("completion_tokens"),
            total_tokens=get_token_value("total_tokens"),
        )
