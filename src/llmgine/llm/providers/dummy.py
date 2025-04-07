"""Dummy LLM provider implementation for testing purposes."""

from typing import Any, Dict, List, Optional

from llmgine.llm.providers import LLMProvider
from llmgine.messages.events import LLMResponse


class DummyProvider(LLMProvider):
    """A dummy provider for testing purposes."""

    async def generate(self,
                      prompt: str,
                      context: Optional[List[Dict[str, Any]]] = None,
                      system_prompt: Optional[str] = None,
                      temperature: Optional[float] = None,
                      max_tokens: Optional[int] = None,
                      model: Optional[str] = None,
                      **kwargs) -> LLMResponse:
        """Generate a response from the dummy LLM.
        
        Args:
            prompt: The user prompt to send to the LLM
            context: Optional conversation context/history
            system_prompt: Optional system prompt/instructions
            temperature: Optional temperature parameter
            max_tokens: Optional maximum tokens for the response
            model: Optional model name/identifier
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse: The response from the LLM
        """
        return LLMResponse(
            content=f"This is a dummy response to: {prompt}",
            role="assistant",
            model="dummy-model",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
        )
