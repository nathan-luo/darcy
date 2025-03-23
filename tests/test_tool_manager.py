"""Tests for the tool manager."""

import asyncio

import pytest

from llmgine.llm.tools import ToolManager


def test_tool_registration():
    """Test that tools can be registered."""
    # Define a test tool
    def test_tool(arg1: str, arg2: int = 0) -> str:
        """Test tool function."""
        return f"{arg1} - {arg2}"

    # Create tool manager and register tool
    manager = ToolManager()
    manager.register_tool(test_tool)

    # Check that the tool was registered
    assert "test_tool" in manager.tools
    assert manager.tools["test_tool"].name == "test_tool"
    assert manager.tools["test_tool"].description == "Test tool function."
    assert not manager.tools["test_tool"].is_async

    # Check parameter schema
    params = manager.tools["test_tool"].parameters
    assert params["type"] == "object"
    assert "arg1" in params["properties"]
    assert "arg2" in params["properties"]
    assert params["properties"]["arg1"]["type"] == "string"
    assert params["properties"]["arg2"]["type"] == "integer"
    assert "arg1" in params["required"]
    assert "arg2" not in params["required"]  # Has default value


def test_tool_descriptions():
    """Test generating tool descriptions."""
    # Define test tools
    def tool1(arg: str) -> str:
        """First test tool."""
        return arg

    def tool2(x: int, y: int) -> int:
        """Second test tool."""
        return x + y

    # Create tool manager and register tools
    manager = ToolManager()
    manager.register_tool(tool1)
    manager.register_tool(tool2)

    # Get tool descriptions
    descriptions = manager.get_tool_descriptions()

    # Check descriptions
    assert len(descriptions) == 2

    # Check that each tool is described
    tool_names = [d["function"]["name"] for d in descriptions]
    assert "tool1" in tool_names
    assert "tool2" in tool_names

    # Check format
    for desc in descriptions:
        assert desc["type"] == "function"
        assert "function" in desc
        assert "name" in desc["function"]
        assert "description" in desc["function"]
        assert "parameters" in desc["function"]


@pytest.mark.asyncio
async def test_tool_execution():
    """Test executing tools."""
    # Define a test tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    # Create tool manager and register tool
    manager = ToolManager()
    manager.register_tool(add)

    # Execute the tool
    result = await manager.execute_tool("add", {"a": 2, "b": 3})

    # Check result
    assert result == 5


@pytest.mark.asyncio
async def test_async_tool_execution():
    """Test executing async tools."""
    # Define an async test tool
    async def async_echo(message: str) -> str:
        """Echo a message with delay."""
        await asyncio.sleep(0.1)
        return f"Echo: {message}"

    # Create tool manager and register tool
    manager = ToolManager()
    manager.register_tool(async_echo)

    # Execute the tool
    result = await manager.execute_tool("async_echo", {"message": "Hello, world!"})

    # Check result
    assert result == "Echo: Hello, world!"

    # Verify that it was registered as an async tool
    assert manager.tools["async_echo"].is_async


@pytest.mark.asyncio
async def test_tool_execution_error():
    """Test error handling in tool execution."""
    # Define a tool that raises an exception
    def failing_tool() -> str:
        """A tool that always fails."""
        raise ValueError("This tool failed on purpose")

    # Create tool manager and register tool
    manager = ToolManager()
    manager.register_tool(failing_tool)

    # Execute the tool and expect an exception
    with pytest.raises(ValueError) as excinfo:
        await manager.execute_tool("failing_tool", {})

    # Check exception message
    assert "This tool failed on purpose" in str(excinfo.value)


@pytest.mark.asyncio
async def test_unknown_tool():
    """Test handling of unknown tools."""
    # Create tool manager without registering any tools
    manager = ToolManager()

    # Try to execute an unknown tool
    with pytest.raises(ValueError) as excinfo:
        await manager.execute_tool("unknown_tool", {})

    # Check exception message
    assert "Tool not found" in str(excinfo.value)
