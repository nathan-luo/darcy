"""LLM module for managing interactions with language models.

This package provides a structured way to interact with language models through a
clean, modular architecture built around protocols, dependency injection, and events.
"""

from llmgine.llm.context import ContextManager, InMemoryContextManager
from llmgine.llm.engine import LLMEngine, LLMResponseEvent, PromptCommand
from llmgine.llm.providers import DefaultLLMManager, DummyProvider, LLMManager, LLMProvider
from llmgine.llm.tools import ToolCallEvent, ToolDescription, ToolManager, ToolResultEvent

__all__ = [
    # Engine
    "LLMEngine",
    "PromptCommand",
    "LLMResponseEvent",

    # Providers
    "LLMProvider",
    "LLMManager",
    "DefaultLLMManager",
    "DummyProvider",

    # Context
    "ContextManager",
    "InMemoryContextManager",
    
    # Tools
    "ToolManager",
    "ToolCallEvent",
    "ToolResultEvent",
    "ToolDescription",
]
