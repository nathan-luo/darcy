"""LLM module for managing interactions with language models.

This package provides a structured approach to building LLM applications
with standardized components for engine management, provider integrations,
context handling, and tool execution.
"""

# Response format - central types
from llmgine.messages.events import LLMResponse, ToolCall

# Engine components
from llmgine.llm.engine import (
    ClearHistoryCommand,
    LLMEngine, 
    LLMResponseEvent, 
    PromptCommand,
    SystemPromptCommand,
    ToolCallEvent,
    ToolResultEvent
)

# Context management
from llmgine.llm.context import ContextManager, InMemoryContextManager

# LLM providers
from llmgine.llm.providers import (
    create_tool_call,
    DefaultLLMManager, 
    DummyProvider, 
    LLMManager, 
    LLMProvider
)

# Tool management
from llmgine.llm.tools import (
    Tool, 
    ToolManager
)

__all__ = [
    # Core types
    "LLMResponse",
    "ToolCall",
    
    # Engine
    "ClearHistoryCommand",
    "LLMEngine",
    "LLMResponseEvent",
    "PromptCommand",
    "SystemPromptCommand",
    "ToolCallEvent",
    "ToolResultEvent",

    # Providers
    "create_tool_call",
    "DefaultLLMManager",
    "DummyProvider",
    "LLMManager",
    "LLMProvider",

    # Context
    "ContextManager",
    "InMemoryContextManager",
    
    # Tools
    "Tool",
    "ToolManager",
]