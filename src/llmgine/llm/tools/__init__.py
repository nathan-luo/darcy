"""Tools for LLMs.

This module provides tools that can be called by language models.
"""

from llmgine.llm.tools.tool_manager import Tool, ToolManager, default_tool_manager

# Re-export tool call events from messages
from llmgine.messages.events import ToolCall

__all__ = [
    "default_tool_manager",
    "ToolCall",
    "Tool",
    "ToolManager",
]