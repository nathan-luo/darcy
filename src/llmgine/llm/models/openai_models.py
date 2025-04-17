from llmgine.llm.models.model import Model
from llmgine.llm.providers import Providers
from llmgine.llm.providers.openai_provider import OpenAIProvider
from llmgine.llm.providers.response import OpenAIResponse
from typing import Any, Dict, List, Literal, Optional, Union
import os


class Gpt_4o_Mini_Latest(Model):
    """
    The latest GPT-4o Mini model.
    """

    def __init__(self, provider: Providers) -> None:
        super().__init__(provider)


class o4_mini(Model):
    """
    The latest o4_mini model.
    """

    def __init__(self, provider: Providers) -> None:
        if provider == Providers.OPENAI:
            self.provider = OpenAIProvider(
                api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o-mini"
            )
            self.generate = self.generate_from_openai
        else:
            raise ValueError(
                f"Provider {provider} not supported for {self.__class__.__name__}"
            )

    def generate_from_openai(
        self,
        context: List[Dict],
        tools: Optional[List[Dict]] = None,
        tool_choice: Union[Literal["auto", "none", "required"], Dict] = "auto",
        parallel_tool_calls: bool = False,
        max_completion_tokens: int = 5068,
        response_format: Optional[Dict] = None,
        reasoning_effort: Literal["low", "medium", "high"] = "low",
        test: bool = False,
        **kwargs: Any,
    ) -> OpenAIResponse:
        return self.provider.generate(
            context=context,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            temperature=None,
            max_completion_tokens=max_completion_tokens,
            response_format=response_format,
            reasoning_effort=reasoning_effort,
            test=test,
            **kwargs,
        )
