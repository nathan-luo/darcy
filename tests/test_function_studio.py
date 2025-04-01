"""Test function studio weather integration."""

import pytest
import pytest_asyncio
import os
import json
from llmgine.studio.function_studio import FunctionStudio
from llmgine.llm.tools.weather import get_weather, TOOL_DEFINITION
from llmgine.llm.engine.messages import PromptCommand
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@pytest_asyncio.fixture
async def studio():
    """Create a function studio instance for testing."""
    # Get OpenAI API key from environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")
    
    # Create and initialize studio
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
    command = PromptCommand(prompt=prompt)
    response = await studio.llm_engine._handle_prompt(command)
    print(f"\nCommand result: {response}")
    
    # Verify command execution was successful
    assert response.success, f"Command failed: {response.error}"
    assert response.result, "Command result should not be None"
    
    # Get the LLM response from the result
    llm_response = response.result
    print(f"\nLLM Response content: {llm_response.content if hasattr(llm_response, 'content') else llm_response}")
    print(f"Response type: {type(llm_response)}")
    print(f"Response attributes: {dir(llm_response)}")
    
    # Verify that the response has tool calls
    assert hasattr(llm_response, 'tool_calls'), "Response should have tool_calls attribute"
    
    # Verify that the tool call is for get_weather
    tool_calls = llm_response.tool_calls
    print(f"\nNumber of tool calls: {len(tool_calls) if tool_calls else 0}")
    if tool_calls:
        print(f"First tool call name: {tool_calls[0].name}")
        print(f"Tool call details: {tool_calls[0].__dict__}")
    
    assert tool_calls and len(tool_calls) > 0, "Expected at least one tool call"
    assert tool_calls[0].name == "get_weather", "Expected tool call to be get_weather"
    
    # Verify tool arguments contain melbourne
    tool_args = json.loads(tool_calls[0].arguments)
    print(f"\nTool arguments: {tool_args}")
    assert "city" in tool_args, "Expected city in tool arguments"
    assert tool_args["city"].lower() == "melbourne", "Expected city to be melbourne"
    
    # Verify that the weather tool is registered
    print(f"\nRegistered tools: {list(studio.tool_manager.tools.keys())}")
    assert "get_weather" in studio.tool_manager.tools, "Weather tool should be registered"
    
    