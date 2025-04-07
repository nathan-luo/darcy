# parsing a response for a unified interface


from abc import ABC, abstractmethod
from dataclasses import dataclass
import inspect
import json
from typing import List, Optional, Dict, Any, Union, Callable
import uuid
import logging
from openai import AsyncOpenAI
from llmgine.bus.bus import MessageBus
from llmgine.llm.engine.core import LLMEngine
from llmgine.llm.providers.llm_manager_events import LLMResponseEvent
from llmgine.messages.events import ToolCall

# Set up logging
logger = logging.getLogger(__name__)

# Where to store this?
USAGE_PATH_REGISTRY: Dict[str, Dict[str, List[str]]] = {
    "openai": {
        "prompt_tokens": ["usage", "prompt_tokens"],
        "completion_tokens": ["usage", "completion_tokens"],
        "total_tokens": ["usage", "total_tokens"],
    },
    "anthropic": {
        "prompt_tokens": ["usage", "input_tokens"],
        "completion_tokens": ["usage", "output_tokens"],
        "total_tokens": ["usage", "total_tokens"],
    },
    # Add more providers as needed
}


@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


# Defining exactly what every class must provide
class LLMResponse(ABC):
    @property
    @abstractmethod
    def content(self) -> str: ...

    @property
    @abstractmethod
    def tool_calls(self) -> List[ToolCall]: ...

    @property
    @abstractmethod
    def has_tool_calls(self) -> bool: ...

    @property
    @abstractmethod
    def finish_reason(self) -> str: ...

    @property
    @abstractmethod
    def usage(self) -> Usage: ...


# Generic LLM response parser
class DefaultLLMResponse(LLMResponse):
    def __init__(
        self,
        raw_response: Any,
        content_path: List[str],
        tool_call_path: Optional[List[str]] = None,
        finish_reason_path: Optional[List[str]] = None,
        usage_key: Optional[str] = None,
        provider: str = "openai",
    ):
        self.raw = raw_response
        self._content_path = content_path
        self._tool_call_path = tool_call_path
        self._finish_reason_path = finish_reason_path
        self._usage_key = usage_key
        self._provider = provider
        self._cached_tool_calls = None

    def _get_nested(self, path: List[str]) -> Any:
        """Access nested attributes from response objects or dictionaries.

        This method handles both attribute access (for objects) and key access (for dictionaries),
        navigating through lists when needed.
        """
        if not path:
            return None

        data = self.raw
        for key in path:
            if data is None:
                return None

            if isinstance(data, list):
                try:
                    index = int(key)
                    if 0 <= index < len(data):
                        data = data[index]
                    else:
                        logger.warning(
                            f"Index {index} out of range for list of length {len(data)}"
                        )
                        return None
                except (ValueError, TypeError):
                    logger.warning(f"Invalid list index: {key}")
                    return None
            elif hasattr(data, key):
                # Try attribute access first
                data = getattr(data, key)
            elif isinstance(data, dict) and key in data:
                # Dictionary access
                data = data[key]
            elif hasattr(data, "__getitem__") and not inspect.ismethod(
                getattr(data, "__getitem__")
            ):
                # Then try dictionary-like access if it has __getitem__
                try:
                    data = data[key]
                except (KeyError, TypeError):
                    # If key doesn't exist, try attribute access as fallback
                    try:
                        data = getattr(data, key, None)
                    except (AttributeError, TypeError):
                        logger.debug(f"Could not access '{key}' in response object")
                        return None
            else:
                logger.debug(f"Could not access '{key}' in response object")
                return None

        return data

    @property
    def content(self) -> str:
        """Get the content from the response.

        Returns an empty string if content is not available.
        """
        content = self._get_nested(self._content_path)
        return content if isinstance(content, str) else ""

    def _extract_openai_tool_calls(self, raw_calls) -> List[Dict[str, Any]]:
        """Extract tool calls from OpenAI response format."""
        result = []

        # No tool calls
        if not raw_calls:
            return result

        # Handle both list and single cases
        if not isinstance(raw_calls, list):
            raw_calls = [raw_calls]

        for call in raw_calls:
            try:
                # Handle OpenAI v2 format (objects with attributes)
                if hasattr(call, "id") and hasattr(call, "function"):
                    func = call.function
                    tool_data = {
                        "id": call.id,
                        "name": func.name if hasattr(func, "name") else "",
                        "arguments": func.arguments
                        if hasattr(func, "arguments")
                        else "{}",
                    }
                    result.append(tool_data)
                # Handle dictionary format
                elif isinstance(call, dict) and "function" in call:
                    func = call["function"]
                    tool_data = {
                        "id": call.get("id", str(uuid.uuid4())),
                        "name": func.get("name", ""),
                        "arguments": func.get("arguments", "{}"),
                    }
                    result.append(tool_data)
                else:
                    logger.warning(f"Unknown tool call format: {call}")
            except Exception as e:
                logger.warning(f"Error extracting tool call data: {e}")

        return result

    @property
    def tool_calls(self) -> List[ToolCall]:
        """Get tool calls from the response."""
        # Return cached results if available
        if self._cached_tool_calls is not None:
            return self._cached_tool_calls

        if not self._tool_call_path:
            self._cached_tool_calls = []
            return []

        # Get raw tool calls data
        raw_tool_calls = self._get_nested(self._tool_call_path)

        # Process based on provider
        if self._provider == "openai":
            extracted_calls = self._extract_openai_tool_calls(raw_tool_calls)
        else:
            # Default fallback to handle basic dictionary structure
            if not raw_tool_calls:
                extracted_calls = []
            elif isinstance(raw_tool_calls, list):
                extracted_calls = raw_tool_calls
            else:
                extracted_calls = [raw_tool_calls]

        # Convert extracted data to ToolCall objects
        tool_calls = []
        for call_data in extracted_calls:
            try:
                tool_calls.append(
                    ToolCall(
                        id=call_data.get("id", str(uuid.uuid4())),
                        name=call_data.get("name", ""),
                        arguments=call_data.get("arguments", "{}"),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to create ToolCall object: {e}")

        # Cache results
        self._cached_tool_calls = tool_calls
        return tool_calls

    @property
    def has_tool_calls(self) -> bool:
        """Check if the response has any tool calls."""
        return len(self.tool_calls) > 0

    @property
    def finish_reason(self) -> str:
        if not self._finish_reason_path:
            return ""
        finish = self._get_nested(self._finish_reason_path)
        return str(finish) if finish is not None else ""

    @property
    def usage(self) -> Usage:
        """Get token usage information from the response."""
        usage_path = USAGE_PATH_REGISTRY.get(self._usage_key, {})

        def get_token_value(name: str) -> int:
            path = usage_path.get(name, [])
            if not path:
                return 0

            value = self._get_nested(path)
            # Ensure we return an integer
            try:
                return int(value) if value is not None else 0
            except (ValueError, TypeError):
                logger.warning(f"Could not convert token usage '{name}' to int")
                return 0

        return Usage(
            prompt_tokens=get_token_value("prompt_tokens"),
            completion_tokens=get_token_value("completion_tokens"),
            total_tokens=get_token_value("total_tokens"),
        )


# manages OpenAI instance
class OpenAIManager:
    def __init__(self, engine_id: str, session_id: str):
        self.engine_id = engine_id
        self.session_id = session_id
        self.llm_manager_id = str(uuid.uuid4())
        self.bus = MessageBus()
        import dotenv
        import os

        dotenv.load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate(
        self,
        context: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = "gpt-4o-mini",
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> DefaultLLMResponse:
        """Generate a response from the OpenAI API.

        Args:
            context: List of messages to send to the API
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            model: The model to use
            tools: List of tools to make available to the model

        Returns:
            DefaultLLMResponse with the model's response
        """
        try:
            request_params = {
                "model": model,
                "messages": context,
                "temperature": temperature or 0.7,
                "max_tokens": max_tokens or 5068,
                "parallel_tool_calls": False,
            }

            # Only add tools if provided
            if tools:
                request_params["tools"] = tools

            # Add any additional kwargs
            request_params.update(kwargs)

            # Call OpenAI API
            response = await self.client.chat.completions.create(**request_params)

            # Publish event
            await self.bus.publish(
                LLMResponseEvent(
                    llm_manager_id=self.llm_manager_id,
                    session_id=self.session_id,
                    engine_id=self.engine_id,
                    raw_response=response,
                )
            )

            # Create and return response object
            return DefaultLLMResponse(
                raw_response=response,
                content_path=["choices", "0", "message", "content"],
                tool_call_path=["choices", "0", "message", "tool_calls"],
                finish_reason_path=["choices", "0", "finish_reason"],
                usage_key="openai",
                provider="openai",
            )
        except Exception as e:
            logger.error(f"Error generating response from OpenAI: {e}")
            raise
