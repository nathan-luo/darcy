"""
This modules contains the models for the OpenAI API.
Each model contains:
- a provider (provided by the llm manager)
- an api key (from env)
- a base url (uniquely hardcoded)
- a model name

Current supported models:
- GPT-4o Mini
    - openai provider: no restrictions
    - openrouter provider: parallel tool calls restricted
- GPT-o3 Mini: temperature restricted
    - openai provider: no restrictions
    - openrouter provider: parallel tool calls restricted

Current supported providers:
- OpenAI
- OpenRouter
"""

import os
import dotenv
from typing import List, Dict, Optional, Literal, Union, Any
from llmgine.llm.models.model import Model
from llmgine.llm.providers.openai_provider import OpenAIResponse, OpenAIProvider
from llmgine.llm.providers.openrouter import OpenRouterProvider
from llmgine.llm.providers import Providers

dotenv.load_dotenv()

class Gpt_4o_Mini_Latest(Model):
    """
    The latest GPT-4o Mini model.
    """
    def __init__(self, provider: Providers) -> None:
        self.generate = None
        self.provider = self.__getProvider(provider)
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o-mini"

    def __getProvider(self, provider: Providers) -> OpenAIProvider:
        """Get the provider and set the generate method."""
        if provider == Providers.OPENROUTER:
            self.generate = self.__generate_openrouter
            return OpenRouterProvider(self.api_key, self.model)
        elif provider == Providers.OPENAI:
            self.generate = self.__generate_openai
            return OpenAIProvider(self.api_key, self.model)
        else:
            raise ValueError(
                f"Provider {provider} not supported for {self.__class__.__name__}"
            )
    
    def __generate_openai(self, 
                          messages: List[Dict], 
                          temperature: float,
                          tools: Optional[List[Dict]],
                          tool_choice: Union[Literal["auto", "none", "required"], Dict],
                          parallel_tool_calls: bool,
                          max_completion_tokens: int,
                          response_format: Optional[Dict],
                          reasoning_effort: Optional[Literal["low", "medium", "high"]],
                          test: bool,
                          **kwargs: Any,
                          ) -> OpenAIResponse:
        """
        This method will hardcode a group of default parameters for the OpenAI provider for the GPT-4o Mini model.
        """
        # Update the parameters with the ones provided in the kwargs.
        return self.provider.generate(messages, 
                                      temperature, 
                                      tools, 
                                      tool_choice, 
                                      parallel_tool_calls, 
                                      max_completion_tokens, 
                                      response_format, 
                                      reasoning_effort, 
                                      test,
                                      **kwargs)

    def __generate_openrouter(self, 
                              messages: List[Dict], 
                              temperature: float,
                              tools: Optional[List[Dict]],
                              tool_choice: Union[Literal["auto", "none", "required"], Dict],
                              parallel_tool_calls: bool,
                              max_completion_tokens: int,
                              response_format: Optional[Dict],
                              reasoning_effort: Optional[Literal["low", "medium", "high"]],
                              test: bool,
                              **kwargs: Any,
                              ) -> OpenAIResponse:
        """
        This method will construct a default group of parameters for the OpenRouter provider.
        """
        return self.provider.generate(messages, 
                                      temperature, 
                                      tools, 
                                      tool_choice, 
                                      max_completion_tokens, 
                                      response_format, 
                                      reasoning_effort, 
                                      test, 
                                      **kwargs)


class Gpt_o3_Mini(Model):
    """
    The latest GPT-o3 Mini model.
    """

    def __init__(self, provider: Providers) -> None:
        self.generate = None
        self.provider = self.__getProvider(provider)
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "o3-mini"
        
        
    def __getProvider(self, provider: Providers) -> OpenAIProvider:
        """Get the provider and set the generate method."""
        if provider == Providers.OPENROUTER:
            self.generate = self.__generate_openrouter
            return OpenRouterProvider(self.api_key, self.model)
        elif provider == Providers.OPENAI:
            self.generate = self.__generate_openai
            return OpenAIProvider(self.api_key, self.model)
        else:
            raise ValueError(
                f"Provider {provider} not supported for {self.__class__.__name__}"
            )
    
    def __generate_openai(self, 
                          messages: List[Dict], 
                          temperature: float,
                          tools: Optional[List[Dict]],
                          tool_choice: Union[Literal["auto", "none", "required"], Dict],
                          parallel_tool_calls: bool,
                          max_completion_tokens: int,
                          response_format: Optional[Dict],
                          reasoning_effort: Optional[Literal["low", "medium", "high"]],
                          test: bool,
                          **kwargs: Any,
                          ) -> OpenAIResponse:
        """
        This method will construct a default group of parameters for the OpenAI provider.
        It will update the parameters with the ones provided in the kwargs.
        """
        return self.provider.generate(messages, 
                                      tools, 
                                      tool_choice, 
                                      parallel_tool_calls, 
                                      max_completion_tokens, 
                                      response_format, 
                                      reasoning_effort, 
                                      test, 
                                      **kwargs)

    def __generate_openrouter(self, 
                              messages: List[Dict], 
                              temperature: float,
                              tools: Optional[List[Dict]],
                              tool_choice: Union[Literal["auto", "none", "required"], Dict],
                              parallel_tool_calls: bool,
                              max_completion_tokens: int,
                              response_format: Optional[Dict],
                              reasoning_effort: Optional[Literal["low", "medium", "high"]],
                              test: bool,
                              **kwargs: Any,
                              ) -> OpenAIResponse:
        """
        This method will construct a default group of parameters for the OpenRouter provider.
        """
        return self.provider.generate(messages, 
                                      tools, 
                                      tool_choice, 
                                      max_completion_tokens, 
                                      response_format, 
                                      reasoning_effort, 
                                      test, 
                                      **kwargs)