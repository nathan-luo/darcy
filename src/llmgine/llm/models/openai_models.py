"""
This modules contains the models for the OpenAI API.
Each model contains:
- a provider (provided by the llm manager)
- an api key (from env)
- a base url (uniquely hardcoded)
- a model name
"""

import os
import dotenv

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

    def generate(self, **kwargs) -> OpenAIResponse:
        """
        This method will choose the correct generate method based on the provider's class.
        """

        if isinstance(self.provider, OpenRouterProvider):
            return self.__generate_openrouter(**kwargs)
        else:
            return self.__generate_openai(**kwargs)
    
    def __generate_openai(self, **kwargs) -> OpenAIResponse:
        """
        This method will construct a default group of parameters for the OpenAI provider.
        """
        parameters = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
            ],
            "temperature": 0.7,
            "max_completion_tokens": 1000,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
            "response_format": None,
            "reasoning_effort": None,
            "test": False,
        }
        # Update the parameters with the ones provided in the kwargs.
        parameters.update(kwargs)

        return self.provider.generate(**parameters)

    def __generate_openrouter(self, **kwargs) -> OpenAIResponse:
        return self.provider.generate(**kwargs)


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

    def generate(self, **kwargs) -> OpenAIResponse:
        """
        This method will choose the correct generate method based on the provider's class.
        """

        if isinstance(self.provider, OpenRouterProvider):
            return self.__generate_openrouter(**kwargs)
        else:
            return self.__generate_openai(**kwargs)
    
    def __generate_openai(self, **kwargs) -> OpenAIResponse:
        """
        This method will construct a default group of parameters for the OpenAI provider.
        It will update the parameters with the ones provided in the kwargs.
        """
        parameters = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
            ],
            "temperature": 0.7,
            "max_completion_tokens": 1000,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
            "response_format": None,
            "test": False,
        }
        # Update the parameters with the ones provided in the kwargs.
        parameters.update(kwargs)

        return self.provider.generate(**parameters)

    def __generate_openrouter(self, **kwargs) -> OpenAIResponse:
        """
        This method will construct a default group of parameters for the OpenRouter provider.
        """
        return self.provider.generate(**kwargs)