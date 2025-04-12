"""Tools for LLMs.

This module provides tools that can be called by language models.
"""

from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.llm.tools.types import AsyncToolFunction

# Re-export tool call events from messages
from llmgine.llm.tools.types import Parameter, Tool, ToolCall, ToolFunction

__all__ = [
    "ToolCall",
    "Tool",
    "ToolManager",
    "ToolFunction",
    "AsyncToolFunction",
    "Parameter",
]