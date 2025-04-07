"""LiteLLM provider implementation for unified access to multiple LLM providers."""

from typing import Any, Dict, List, Optional

import litellm
from litellm.utils import ModelResponse

from llmgine.llm.providers import LLMProvider
from llmgine.messages.events import LLMResponse


class LiteLLMProvider(LLMProvider):
    """Provider implementation using LiteLLM for unified access to multiple LLM APIs."""

    def __init__(
        self,
        default_model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        **config,
    ):
        """Initialize the LiteLLM provider.

        Args:
            default_model: The default model to use if none is specified
            api_key: Optional API key for the LLM service
            **config: Additional configuration parameters for LiteLLM
        """
        self.default_model = default_model
        self.api_key = api_key
        self.config = config

        # Set API key if provided
        if api_key:
            litellm.api_key = api_key

    async def generate(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response using LiteLLM.

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
        # Use default model if none provided
        model_name = model or self.default_model

        # Build messages for the conversation
        messages = []

        # Add system message if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add context messages if provided
        if context:
            messages.extend(context)

        # Add the current prompt
        messages.append({"role": "user", "content": prompt})

        # Set up parameters for the completion
        completion_params = {
            "model": model_name,
            "messages": messages,
        }

        # Add optional parameters
        if temperature is not None:
            completion_params["temperature"] = temperature
        if max_tokens is not None:
            completion_params["max_tokens"] = max_tokens

        # Add any additional parameters
        completion_params.update(kwargs)

        try:
            # Call LiteLLM async completion
            response: ModelResponse = await litellm.acompletion(**completion_params)

            # Extract content from response
            content = response.choices[0].message.content

            # Get usage data
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            # Return formatted response
            return LLMResponse(
                content=content,
                role="assistant",
                model=model_name,
                finish_reason=response.choices[0].finish_reason,
                usage=usage,
            )
        except Exception as e:
            # In a production environment, you might want more sophisticated
            # error handling and possibly retry logic here
            raise RuntimeError(f"LiteLLM generation failed: {str(e)}") from e
