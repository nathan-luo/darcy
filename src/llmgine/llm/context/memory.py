"""In-memory implementation of the ContextManager interface."""

from typing import Any, Dict, List, Optional
import uuid

from llmgine.llm.context import ContextManager
from llmgine.llm.engine.core import LLMEngine
from llmgine.llm.providers.response import DefaultLLMResponse


class SimpleChatHistory:
    def __init__(self, engine: LLMEngine):
        self.engine = engine
        self.engine_id = engine.engine_id
        self.session_id = engine.session_id
        self.id = str(uuid.uuid4())
        self.response_log: List[Any] = []  # need to define type
        self.chat_history: List[Any] = []
        self.system: Optional[str] = None

    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt

    def store_response(self, response: DefaultLLMResponse, role: str):
        self.response_log.append(response)
        self.chat_history.append({"role": role, "content": response.content})

    def store_string(self, string: str, role: str):
        self.response_log.append([role, string])
        self.chat_history.append({"role": role, "content": string})

    def store_tool_response(self, response: DefaultLLMResponse):
        """Store a tool response in the chat history"""
        self.response_log.append(response)
        self.chat_history.append(response.full.choices[0].message)
        for tool_call in response.full.choices[0].message.tool_calls:
            self.chat_history.append(tool_call)

    def store_function_call_result(self, result: Dict):
        """Store function call result in the chat history

        Args:
            result: Dictionary containing role, tool_call_id, name, and result
        """
        self.response_log.append(result)
        self.chat_history.append(result)

    def retrieve(self):
        result = self.chat_history.copy()
        if self.system_prompt:
            result.insert(0, {"role": "system", "content": self.system_prompt})
        return result

    def clear(self):
        self.response_log = []
        self.chat_history = []
        self.system_prompt = ""


class SingleChatContextManager(ContextManager):
    def __init__(self, max_context_length: int = 100):
        """Initialize the single chat context manager.

        Args:
            max_context_length: Maximum number of messages to keep in context
        """
        self.context_raw = []

    def get_context(self) -> List[Dict[str, Any]]:
        """Get the conversation context for a specific conversation.

        Returns:
            List[Dict[str, Any]]: The conversation context/history
        """
        return self.context_raw

    def add_message(self, message: Dict[str, Any]) -> None:
        """Add a message to the conversation context.

        Args:
            message: The message to add to the context
        """
        self.context_raw.append(message)


class InMemoryContextManager(ContextManager):
    """In-memory implementation of the context manager interface."""

    def __init__(self, max_context_length: int = 100):
        """Initialize the in-memory context manager.

        Args:
            max_context_length: Maximum number of messages to keep in context
        """
        self.contexts: Dict[str, List[Dict[str, Any]]] = {}
        self.max_context_length = max_context_length

    def get_context(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get the conversation context for a specific conversation.

        Args:
            conversation_id: The conversation identifier

        Returns:
            List[Dict[str, Any]]: The conversation context/history
        """
        return self.contexts.get(conversation_id, [])

    def add_message(self, conversation_id: str, message: Dict[str, Any]) -> None:
        """Add a message to the conversation context.

        Args:
        conversation_id: The conversation identifier
            message: The message to add to the context
        """
        if conversation_id not in self.contexts:
            self.contexts[conversation_id] = []

        self.contexts[conversation_id].append(message)

        # Trim context if it exceeds max length
        if len(self.contexts[conversation_id]) > self.max_context_length:
            # Keep the first message (usually system prompt) and trim the oldest messages
            first_message = self.contexts[conversation_id][0]
            self.contexts[conversation_id] = [first_message] + self.contexts[
                conversation_id
            ][-(self.max_context_length - 1) :]

    def clear_context(self, conversation_id: str) -> None:
        """Clear the context for a specific conversation.

        Args:
            conversation_id: The conversation identifier
        """
        if conversation_id in self.contexts:
            self.contexts[conversation_id] = []
