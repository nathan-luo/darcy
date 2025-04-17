from typing import Any, Dict, List, Literal, Optional, Union
from litellm import AsyncOpenAI
import openai
import os

from llmgine.bus.bus import MessageBus
from llmgine.llm.providers import LLMProvider
from llmgine.llm.providers.response import LLMResponse, ResponseTokens
from openai.types.chat import ChatCompletion

from llmgine.llm.tools.types import ToolCall

OpenRouterProviders = Literal[
    "OpenAI",
    "Anthropic",
    "Google",
    "Google AI Studio",
    "Amazon Bedrock",
    "Groq",
    "SambaNova",
    "Cohere",
    "Mistral",
    "Together",
    "Together 2",
    "Fireworks",
    "DeepInfra",
    "Lepton",
    "Novita",
    "Avian",
    "Lambda",
    "Azure",
    "Modal",
    "AnyScale",
    "Replicate",
    "Perplexity",
    "Recursal",
    "OctoAI",
    "DeepSeek",
    "Infermatic",
    "AI21",
    "Featherless",
    "Inflection",
    "xAI",
    "Cloudflare",
    "SF Compute",
    "Minimax",
    "Nineteen",
    "Liquid",
    "Stealth",
    "NCompass",
    "InferenceNet",
    "Friendli",
    "AionLabs",
    "Alibaba",
    "Nebius",
    "Chutes",
    "Kluster",
    "Crusoe",
    "Targon",
    "Ubicloud",
    "Parasail",
    "Phala",
    "Cent-ML",
    "Venice",
    "OpenInference",
    "Atoma",
    "01.AI",
    "HuggingFace",
    "Mancer",
    "Mancer 2",
    "Hyperbolic",
    "Hyperbolic 2",
    "Lynn 2",
    "Lynn",
    "Reflection",
]


class OpenRouterResponse(LLMResponse):
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


class OpenRouterProvider(LLMProvider):
    def __init__(
        self, api_key: str, model: str, provider: Optional[OpenRouterProviders] = None
    ) -> None:
        self.model = model
        self.provider = provider
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = AsyncOpenAI(
            api_key=api_key, base_url=self.base_url
        )
        self.bus = MessageBus()

    async def generate(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        tool_choice: Union[Literal["auto", "none", "required"], Dict] = "auto",
        temperature: float = 0.7,
        max_completion_tokens: int = 5068,
        response_format: Optional[Dict] = None,
        reasoning: bool = False,
        reasoning_max_tokens: Optional[int] = None,
        reasoning_effort: Optional[Literal["low", "medium", "high"]] = None,
        reasoning_include_reasoning: Optional[bool] = False,
        test: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        # id = str(uuid.uuid4())
        payload = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
        }

        if self.provider:
            payload["extra_body"] = {
                "provider": {
                    "order": [self.provider],
                    "allow_fallbacks": False,
                    "data_collection": "deny",
                }
            }

        if temperature:
            payload["temperature"] = temperature

        if tools:
            payload["tools"] = tools

            if tool_choice:
                payload["tool_choice"] = tool_choice

        if response_format:
            payload["response_format"] = response_format

        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        if reasoning:
            payload["extra_body"]["reasoning"] = {}
            if reasoning_max_tokens:
                payload["extra_body"]["reasoning"]["max_tokens"] = reasoning_max_tokens
            if reasoning_effort:
                payload["extra_body"]["reasoning"]["effort"] = reasoning_effort
            if not reasoning_include_reasoning:
                payload["extra_body"]["reasoning"]["exclude"] = True

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
            return OpenRouterResponse(response)

    def stream():
        # TODO: Implement streaming
        raise NotImplementedError("Streaming is not supported for OpenRouter")
