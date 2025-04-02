from abc import ABC, abstractmethod


@dataclass
class Usage:
    """The usage information for a completion."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMResponse(ABC):
    """A response from an LLM completion."""

    @abstractmethod
    @property
    def content(self) -> str:
        """The content of the response."""
        ...

    @abstractmethod
    @property
    def tool_calls(self) -> List[ToolCall]:
        """The tool calls in the response."""
        ...

    @abstractmethod
    @property
    def has_tool_calls(self) -> bool:
        """Whether the response has tool calls."""
        ...

    @abstractmethod
    @property
    def finish_reason(self) -> str:
        """The reason the completion finished."""
        ...

    @abstractmethod
    @property
    def usage(self) -> Usage:
        """The usage information for the completion."""
        ...
