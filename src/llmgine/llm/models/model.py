from typing import Any
from abc import ABC, abstractmethod
from llmgine.llm.providers.response import LLMResponse


class Model(ABC):
    """
    Base class for all models.
    """

    @abstractmethod
    def generate(self, **kwargs: Any) -> LLMResponse:
        """
        Generate a response from the model.
        """
        
