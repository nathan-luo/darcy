"""
This modules contains the models for the OpenAI API.
Each model contains:
- a provider (provided by the llm manager)
- an api key (from env)
- a base url (uniquely hardcoded)
- a model name

Current model:
- GPT-4o Mini
    - openai provider: no restrictions
    - openrouter provider: parallel tool calls restricted
- GPT-o3 Mini: temperature restricted
    - openai provider: no restrictions
    - openrouter provider: parallel tool calls restricted
"""

import os
import dotenv
from typing import List, Dict, Optional, Literal, Union, Any
from llmgine.llm.models.model import Model
from llmgine.llm.providers.openai import OpenAIResponse, OpenAIProvider
from llmgine.llm.providers.openrouter import OpenRouterProvider

dotenv.load_dotenv()

class Gpt_4o_Mini_Latest(Model):
    """
    The latest GPT-4o Mini model.
    """

    def __init__(self, provider: str = None) -> None:
        self.provider = self.__getProvider(provider)
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o-mini"

    def __getProvider(self, provider: str) -> OpenAIProvider:
        if provider == "openrouter":
            return OpenRouterProvider(self.api_key, self.model)
        else:
            return OpenAIProvider(self.api_key, self.model)

    def generate(self, 
                messages: List[Dict], 
                temperature: float = 0.7,
                tools: Optional[List[Dict]] = None,
                tool_choice: Union[Literal["auto", "none", "required"], Dict] = "auto",
                parallel_tool_calls: bool = False,
                max_completion_tokens: int = 5068,
                response_format: Optional[Dict] = None,
                reasoning_effort: Optional[Literal["low", "medium", "high"]] = None,
                test: bool = False,
                **kwargs: Any,
                ) -> OpenAIResponse:
        """
        This method will choose the correct generate method based on the provider's class.
        """

        if isinstance(self.provider, OpenRouterProvider):
            return self.__generate_openrouter(messages, 
                                              temperature, 
                                              tools,
                                              tool_choice, 
                                              parallel_tool_calls, 
                                              max_completion_tokens, 
                                              response_format, 
                                              reasoning_effort, 
                                              test,
                                              **kwargs)
        else:
            return self.__generate_openai(messages,
                                          temperature, 
                                          tools,
                                          tool_choice, 
                                          parallel_tool_calls, 
                                          max_completion_tokens,
                                          response_format, 
                                          reasoning_effort, 
                                          test,
                                          **kwargs)
    
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
        parameters = {
            "messages": messages,
            "tools": tools,
            "temperature": temperature,
            "max_completion_tokens": max_completion_tokens,
            "tool_choice": tool_choice,
            "parallel_tool_calls": parallel_tool_calls,
            "response_format": response_format,
            "reasoning_effort": reasoning_effort,
            "test": test,
            **kwargs,
        }
        return self.provider.generate(**parameters)

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
        parameters = {
            "messages": messages,
            "temperature": temperature,
            "tools": tools,
            "max_completion_tokens": max_completion_tokens,
            "tool_choice": tool_choice,
            "response_format": response_format,
            "reasoning_effort": reasoning_effort,
            "test": test,
            **kwargs,
        }

        return self.provider.generate(**parameters)
    




class Gpt_o3_Mini(Model):
    """
    The latest GPT-o3 Mini model.
    """

    def __init__(self, provider: str = None) -> None:
        self.provider = self.__getProvider(provider)
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "o3-mini"
        
        
    def __getProvider(self, provider: str) -> OpenAIProvider:
        if provider == "openrouter":
            return OpenRouterProvider(self.api_key, self.model)
        else:
            return OpenAIProvider(self.api_key, self.model)

    def generate(self, 
                messages: List[Dict], 
                temperature: float = 0.7,
                tools: Optional[List[Dict]] = None,
                tool_choice: Union[Literal["auto", "none", "required"], Dict] = "auto",
                parallel_tool_calls: bool = False,
                max_completion_tokens: int = 5068,
                response_format: Optional[Dict] = None,
                reasoning_effort: Optional[Literal["low", "medium", "high"]] = None,
                test: bool = False,
                **kwargs: Any,
                ) -> OpenAIResponse:
        """
        This method will choose the correct generate method based on the provider's class.
        """

        if isinstance(self.provider, OpenRouterProvider):
            return self.__generate_openrouter(messages, 
                                              temperature, 
                                              tools,
                                              tool_choice, 
                                              parallel_tool_calls, 
                                              max_completion_tokens, 
                                              response_format, 
                                              reasoning_effort, 
                                              test,
                                              **kwargs)
        else:
            return self.__generate_openai(messages, 
                                          temperature, 
                                          tools,
                                          tool_choice, 
                                          parallel_tool_calls, 
                                          max_completion_tokens,
                                          response_format, 
                                          reasoning_effort, 
                                          test,
                                          **kwargs)
    
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
        parameters = {
            "messages": messages,
            "tools": tools,
            "max_completion_tokens": max_completion_tokens,
            "tool_choice": tool_choice,
            "parallel_tool_calls": parallel_tool_calls,
            "response_format": response_format,
            "reasoning_effort": reasoning_effort,
            "test": test,
            **kwargs,
        }
        
        return self.provider.generate(**parameters)

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

        parameters = {
            "messages": messages,
            "tools": tools,
            "max_completion_tokens": max_completion_tokens,
            "tool_choice": tool_choice,
            "response_format": response_format,
            "reasoning_effort": reasoning_effort,
            "test": test,
            **kwargs,
        }

        return self.provider.generate(**parameters)