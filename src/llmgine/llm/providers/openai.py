"""OpenAI provider implementation."""

from typing import Any, Dict, List, Literal, Optional, Union
import json

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from llmgine.llm.providers import LLMProvider, create_tool_call
from llmgine.llm.providers.response import ResponseTokens
from llmgine.llm.tools.types import ToolCall
from llmgine.messages.events import LLMResponse
from llmgine.bus.bus import MessageBus

class OpenAIResponse(LLMResponse):
    def __init__(self, response: ChatCompletion) -> None:
        self.response = response

    @property
    def raw(self) -> ChatCompletion:
        return self.response

    @property
    def content(self) -> str:
        return self.response.choices[0].message.content

    @property
    def tool_calls(self) -> List[ToolCall]:
        return [
            ToolCall(tool_call)
            for tool_call in self.response.choices[0].message.tool_calls
        ]

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

    @property
    def finish_reason(self) -> str:
        return self.response.choices[0].finish_reason

    @property
    def tokens(self) -> ResponseTokens:
        return ResponseTokens(
            prompt_tokens=self.response.usage.prompt_tokens,
            completion_tokens=self.response.usage.completion_tokens,
            total_tokens=self.response.usage.total_tokens,
        )

    @property
    def reasoning(self) -> str:
        return self.response.choices[0].message.reasoning


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        self.client = AsyncOpenAI(api_key=api_key, base_url=self.base_url)
        self.bus = MessageBus()

    async def generate(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        tool_choice: Union[Literal["auto", "none", "required"], Dict] = "auto",
        parallel_tool_calls: Optional[bool] = None,
        temperature: Optional[float] = None,
        max_completion_tokens: int = 5068,
        response_format: Optional[Dict] = None,
        reasoning_effort: Optional[Literal["low", "medium", "high"]] = None,
        test: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        # id = str(uuid.uuid4())

        # construct the payload
        payload = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
        }

        if temperature:
            payload["temperature"] = temperature

        if tools:
            payload["tools"] = tools

            if tool_choice:
                payload["tool_choice"] = tool_choice
                
            if parallel_tool_calls:
                payload["parallel_tool_calls"] = parallel_tool_calls

        if response_format:
            payload["response_format"] = response_format

        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        payload.update(**kwargs)
        # self.bus.emit(LLMCallEvent(id=id, provider=Providers.OPENAI, payload=payload))
        try:
            response = await self.client.chat.completions.create(**payload)
        except Exception as e:
            # self.bus.emit(LLMResponseEvent(call_id=id, provider=Providers.OPENAI, response=e))
            raise e
        # self.bus.emit(LLMResponseEvent(call_id=id, provider=Providers.OPENAI, response=response))
        if test:
            return response
        else:
            return OpenAIResponse(response)

    def stream():
        # TODO: Implement streaming
        raise NotImplementedError("Streaming is not supported for OpenAI")
