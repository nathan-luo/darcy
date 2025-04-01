"""Test function studio weather integration."""

import pytest
import pytest_asyncio
import os
from unittest.mock import AsyncMock, patch
from llmgine.studio.function_studio import FunctionStudio
from llmgine.llm.tools.weather import get_weather
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@pytest_asyncio.fixture
async def studio():
    """Create a function studio instance for testing."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")
    
    studio_instance = FunctionStudio(api_key)
    await studio_instance.start()
    
    try:
        yield studio_instance
    finally:
        await studio_instance.stop()

@pytest.mark.asyncio
async def test_weather_tool_handling(studio):
    """Test that the LLM engine properly handles weather tool calls."""
    # Verify studio instance
    assert isinstance(studio, FunctionStudio), "Expected studio to be a FunctionStudio instance"
    assert hasattr(studio, 'llm_engine'), "Studio should have llm_engine attribute"
    
    # Test prompt that should trigger weather tool
    prompt = "what's the current temperature in melbourne?"
    print(f"\nTesting prompt: {prompt}")
    
    # Create and send PromptCommand
    response = await studio.query(prompt)
    print(f"\nResponse: {response}")
    
    # Verify that the weather tool is registered
    print(f"\nRegistered tools: {list(studio.tool_manager.tools.keys())}")
    assert "get_weather" in studio.tool_manager.tools, "Weather tool should be registered"
    
    # Verify tool registration in tool manager
    tools = studio.tool_manager.get_tools()
    print(f"\nTool manager tools:")
    for tool in tools:
        print(f"Tool: {tool}")
    
    # Verify that the tool was called
    assert response is not None, "Response should not be None"
    assert isinstance(response, str), "Response should be a string"
    