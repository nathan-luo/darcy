"""OpenAI provider implementation."""

from typing import Any, Dict, List, Optional, Union
import json

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from llmgine.llm.providers import LLMProvider, create_tool_call
from llmgine.llm.tools.types import ToolCall
from llmgine.messages.events import LLMResponse




class OpenAIProvider(LLMProvider):
    """Provider implementation for OpenAI's API."""

    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-3.5-turbo",
        organization: Optional[str] = None,
        **kwargs
    ):
        """Initialize the OpenAI provider.

        Args:
            api_key: The OpenAI API key
            default_model: The default model to use if none is specified
            organization: Optional organization ID for the OpenAI API
            **kwargs: Additional configuration parameters for the OpenAI client
        """
        self.default_model = default_model
        self.client = AsyncOpenAI(
            api_key=api_key,
            organization=organization,
            **kwargs
        )

    async def generate(
        self,
        prompt: str, 
        context: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using OpenAI's API.

        Args:
            prompt: The user prompt to send to the LLM
            context: Optional conversation context/history
            system_prompt: Optional system prompt/instructions
            temperature: Optional temperature parameter
            max_tokens: Optional maximum tokens for the response
            model: Optional model name/identifier
            tools: Optional list of tools to provide to the LLM
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

        # Process context messages following OpenAI's requirements
        # Note: OpenAI requires that tool messages must follow an assistant message with tool_calls
        if context:
            for msg in context:
                # Normalize message format
                msg_to_add = {}
                
                # Basic message properties
                msg_to_add["role"] = msg.get("role", "user")
                
                # Add content if present
                if "content" in msg and msg["content"] is not None:
                    msg_to_add["content"] = msg["content"]
                elif msg_to_add["role"] not in ["tool"]:  # tool role doesn't require content
                    msg_to_add["content"] = ""
                
                # Handle specific roles
                if msg_to_add["role"] == "assistant" and "tool_calls" in msg:
                    # Format tool_calls according to OpenAI's expectations
                    msg_to_add["tool_calls"] = msg["tool_calls"]
                
                elif msg_to_add["role"] == "tool":
                    # Tool messages need tool_call_id and name
                    if "tool_call_id" in msg:
                        msg_to_add["tool_call_id"] = msg["tool_call_id"]
                    if "name" in msg:
                        msg_to_add["name"] = msg["name"]
                
                # Add message to the list
                messages.append(msg_to_add)

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
        if tools:
            completion_params["tools"] = tools

        # Add any additional parameters
        completion_params.update(kwargs)

        try:
            # Call OpenAI ChatCompletion
            response: ChatCompletion = await self.client.chat.completions.create(**completion_params)

            # Get the first choice
            choice = response.choices[0]
            
            # Extract tool calls if present
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = []
                for tc in choice.message.tool_calls:
                    # Convert to our internal ToolCall format
                    try:
                        # Try to parse JSON arguments
                        args_json = json.loads(tc.function.arguments)
                        args_str = json.dumps(args_json)
                    except json.JSONDecodeError:
                        # If not valid JSON, use as is
                        args_str = tc.function.arguments
                        
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args_str
                    ))

            # Get usage data
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            # Return formatted response
            return LLMResponse(
                content=choice.message.content,
                role="assistant",
                model=model_name,
                finish_reason=choice.finish_reason,
                usage=usage,
                tool_calls=tool_calls
            )
        except Exception as e:
            # In a production environment, you might want more sophisticated
            # error handling and possibly retry logic here
            raise RuntimeError(f"OpenAI generation failed: {str(e)}") from e