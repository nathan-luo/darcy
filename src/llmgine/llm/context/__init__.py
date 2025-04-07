"""Context Manager interface and implementations.

This module defines the ContextManager interface and its implementations.
The ContextManager is responsible for managing the context/history for LLM interactions.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

# Import this way to avoid circular imports
if TYPE_CHECKING:
    from llmgine.llm.context.memory import InMemoryContextManager


class ContextManager(ABC):
    """Interface for managing the context/history for LLM interactions."""

    @abstractmethod
    def get_context(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get the conversation context for a specific conversation.
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            List[Dict[str, Any]]: The conversation context/history
        """
        ...

    @abstractmethod
    def add_message(self, conversation_id: str, message: Dict[str, Any]) -> None:
        """Add a message to the conversation context.
        
        Args:
            conversation_id: The conversation identifier
            message: The message to add to the context
        """
        ...

    @abstractmethod
    def clear_context(self, conversation_id: str) -> None:
        """Clear the context for a specific conversation.
        
        Args:
            conversation_id: The conversation identifier
        """
        ...

# Import implementations after the interface definition
from llmgine.llm.context.memory import InMemoryContextManager

__all__ = [
    "ContextManager",
    "InMemoryContextManager",
]
