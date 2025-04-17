# parsing a response for a unified interface


from abc import ABC, abstractmethod
from dataclasses import dataclass
import inspect
import json
from typing import List, Optional, Dict, Any, Union, Callable
import uuid
import logging
from llmgine.llm.tools.types import ToolCall

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class ResponseTokens:
    # TODO: better structure, cost calculation, etc
    prompt_tokens: int
    reasoning_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ResponseMetrics:
    # TODO: better structure, cost calculation, etc
    tokens: ResponseTokens
    cost: float
    ttf: float
    tps: float


# Base class for LLM responses
class LLMResponse:
    def __init__(self, raw_response: Any):
        self.raw = raw_response

    @property
    def content(self) -> str:
        raise NotImplementedError

    @property
    def tool_calls(self) -> List[ToolCall]:
        raise NotImplementedError

    @property
    def has_tool_calls(self) -> bool:
        raise NotImplementedError

    @property
    def finish_reason(self) -> str:
        raise NotImplementedError

    @property
    def tokens(self) -> ResponseTokens:
        raise NotImplementedError

    @property
    def metrics(self) -> Dict[str, Any]:
        raise NotImplementedError

    @property
    def model(self) -> Dict[str, Any]:
        raise NotImplementedError

    @property
    def reasoning(self) -> str:
        raise NotImplementedError
