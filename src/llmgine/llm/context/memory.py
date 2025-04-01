"""In-memory implementation of the ContextManager interface."""

from typing import Any, Dict, List

from llmgine.llm.context import ContextManager


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
