"""Tests for the tool manager."""

import asyncio
import json
import uuid
import pytest

from llmgine.llm.tools import ToolManager

class SampleEngine:
    """A sample engine for testing."""

    def __init__(self):
        """Initialize the sample engine."""
        self.engine_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())

def create_tool_manager(llm_model_name: str = "openai"):
    """Create a tool manager with a message bus and an observability bus."""
    engine = SampleEngine()
    return ToolManager(engine_id=engine.engine_id, session_id=engine.session_id, llm_model_name=llm_model_name)


@pytest.mark.asyncio
async def test_tool_register_notion_functions():
    """Test that the tool register can be initialized."""
    tool_manager = create_tool_manager()
    await tool_manager.register_tools(["notion"])

    # Check that the tools are registered
    assert len(tool_manager.tools) > 0
    assert tool_manager.tools["get_all_users"] is not None
    assert tool_manager.tools["get_active_tasks"] is not None
    assert tool_manager.tools["get_active_projects"] is not None
    assert tool_manager.tools["create_task"] is not None
    assert tool_manager.tools["update_task"] is not None
