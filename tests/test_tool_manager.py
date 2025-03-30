"""Tests for the tool manager."""

import asyncio

import pytest

from llmgine.llm.tools import ToolManager
from llmgine.llm.engine.core import LLMEngine
from llmgine.bus.bus import MessageBus
from llmgine.observability import ObservabilityBus

def create_tool_manager(llm_model_name: str = "openai"):
    """Create a tool manager with a message bus and an observability bus."""
    return ToolManager(llm_model_name=llm_model_name)

def test_tool_registration():
    """Test that tools can be registered."""
    # Define a test tool
    def test_tool1(arg1: str, arg2: int = 0) -> str:
        """Test tool function."""
        return f"{arg1} - {arg2}"

    # A tool with no description
    def test_tool2(arg1: str, arg2: int = 0) -> str:
        return f"{arg1} - {arg2}"

    # Create tool manager and register tool with default LLM model: OpenAI
    manager = create_tool_manager()
    manager.register_tool(test_tool1)
    manager.register_tool(test_tool2)

    # Check that the tool was registered
    assert "test_tool1" in manager.tools
    assert manager.tools["test_tool1"].name == "test_tool1"
    assert manager.tools["test_tool1"].description == "Test tool function."
    assert not manager.tools["test_tool1"].is_async

    # Check parameter schema for the first tool
    params = manager.tools["test_tool1"].parameters
    assert type(params) == list
    assert len(params) == 2
    assert params[0].name == "arg1"
    assert params[0].description == "Parameter: arg1"
    assert params[0].type == "string"
    assert params[0].required
    assert params[1].name == "arg2"
    assert params[1].description == "Parameter: arg2"
    assert params[1].type == "integer"
    assert not params[1].required

    # Check that the second tool has correct description
    assert manager.tools["test_tool2"].description == "No description provided"
    
def test_tool_registration_with_args_docstring():
    """Test that tools can be registered with 'Args:' in the docstring."""
    # Define a test tool
    def test_tool(arg1: str, arg2: int = 0) -> str:
        """Test tool function.
        
        Args:
            arg1: The first argument.
            arg2: The second argument.
        """
        return f"{arg1} - {arg2}"

    # Create tool manager and register tool
    manager = create_tool_manager()
    manager.register_tool(test_tool)

    # Check that the tool was registered
    assert "test_tool" in manager.tools
    assert manager.tools["test_tool"].name == "test_tool"
    assert manager.tools["test_tool"].description == "Test tool function."
    assert not manager.tools["test_tool"].is_async

    # Check parameter schema
    params = manager.tools["test_tool"].parameters
    assert type(params) == list
    assert len(params) == 2
    assert params[0].name == "arg1"
    assert params[0].description == "The first argument."
    assert params[0].type == "string"
    assert params[0].required
    assert params[1].name == "arg2"
    assert params[1].description == "The second argument."
    assert params[1].type == "integer"
    assert not params[1].required

def test_tool_registration_with_args_docstring_and_returns_docstring():
    """Test that tools can be registered with 'Args:' in the docstring and 'Returns:' in the docstring.
       One argument specified in the docstring, one argument not specified.
    """
    # Define a test tool
    def test_tool(arg1: str, arg2: int = 0) -> str:
        """Test tool function.
        
        Args:
            arg1: The first argument.

        Returns:
            The result of the tool.
        """
        return f"{arg1} - {arg2}"

    # Create tool manager and register tool
    manager = create_tool_manager()
    manager.register_tool(test_tool)

    # Check that the tool was registered
    assert "test_tool" in manager.tools
    assert manager.tools["test_tool"].name == "test_tool"
    assert manager.tools["test_tool"].description == "Test tool function."
    assert not manager.tools["test_tool"].is_async

    # Check parameter schema
    params = manager.tools["test_tool"].parameters
    assert type(params) == list
    assert len(params) == 2
    assert params[0].name == "arg1"
    assert params[0].description == "The first argument."
    assert params[0].type == "string"
    assert params[0].required
    assert params[1].name == "arg2"
    assert params[1].description == "Parameter: arg2"
    assert params[1].type == "integer"
    assert not params[1].required

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
    manager = create_tool_manager()
    manager.register_tool(tool1)
    manager.register_tool(tool2)

    # Get tool descriptions
    tools = manager.get_tools()

    # Check descriptions format
    assert len(tools) == 2
    assert tools[0]["function"].keys() == {"name", "description", "parameters"}
    assert tools[0]["function"]["parameters"].keys() == {"type", "properties", "required"}

def test_tool_descriptions_with_llm_model():
    """Test generating tool descriptions with a specific LLM model."""
    # Define test tools
    def tool1(arg: str) -> str:
        """First test tool."""
        return arg
    
    def tool2(x: int, y: int) -> int:
        """Second test tool."""
        return x + y

    # Test OpenAI
    manager = create_tool_manager(llm_model_name="openai")
    manager.register_tool(tool1)
    manager.register_tool(tool2)

    # Get tools in OpenAI format
    openai_tools = manager.get_tools()
    assert len(openai_tools) == 2
    assert openai_tools[0]["function"].keys() == {"name", "description", "parameters"}
    assert openai_tools[0]["function"]["parameters"].keys() == {"type", "properties", "required"}

    # Test Claude
    manager = create_tool_manager(llm_model_name="claude")
    manager.register_tool(tool1)
    manager.register_tool(tool2)

    # Get tools in Claude format
    claude_tools = manager.get_tools()
    assert len(claude_tools) == 2
    assert claude_tools[0]["function"].keys() == {"name", "description", "input_schema"}
    assert claude_tools[0]["function"]["input_schema"].keys() == {"type", "properties", "required"}


    # Test DeepSeek
    manager = create_tool_manager(llm_model_name="deepseek")
    manager.register_tool(tool1)
    manager.register_tool(tool2)

    # Get tools in DeepSeek format
    deepseek_tools = manager.get_tools()
    assert len(deepseek_tools) == 2
    assert deepseek_tools[0]["function"].keys() == {"name", "description", "parameters"}
    assert deepseek_tools[0]["function"]["parameters"].keys() == {"type", "properties", "required"}

@pytest.mark.asyncio
async def test_tool_execution():
    """Test executing tools."""
    # Define a test tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    # Create tool manager and register tool
    manager = create_tool_manager()
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
    manager = create_tool_manager()
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
    manager = create_tool_manager()
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
    manager = create_tool_manager()

    # Try to execute an unknown tool
    with pytest.raises(ValueError) as excinfo:
        await manager.execute_tool("unknown_tool", {})

    # Check exception message
    assert "Tool not found" in str(excinfo.value)
