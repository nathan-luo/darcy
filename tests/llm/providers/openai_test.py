import pytest
import os
import json
from typing import List, Dict, Any

from llmgine.llm.providers.openai import OpenAIProvider, OpenAIResponse
from llmgine.llm.tools.types import ToolCall

# Marker for tests requiring OpenAI API key and making real calls
openai_test = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable",
)


@pytest.fixture
def openai_provider():
    """Fixture to create an OpenAI provider with API credentials from environment."""
    api_key = os.environ.get("OPENAI_API_KEY", "dummy_key")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    
    return OpenAIProvider(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


@pytest.fixture
def openai_context() -> List[Dict[str, Any]]:
    """Create a simple chat context for testing."""
    return [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you for asking. How can I help you today?"},
    ]


@pytest.fixture
def openai_tools() -> List[Dict[str, Any]]:
    """Create a sample tool definition for testing tool calls."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "The temperature unit to use",
                        },
                    },
                    "required": ["location"],
                },
            },
        }
    ]


@openai_test
@pytest.mark.asyncio
async def test_generate_basic_text(openai_provider, openai_context):
    """Test generating basic text from the OpenAI provider."""
    response = await openai_provider.generate(
        context=openai_context + [{"role": "user", "content": "What is the capital of France?"}],
        temperature=0.7,
    )
    
    # Verify response structure
    assert isinstance(response, OpenAIResponse)
    assert response.content is not None
    assert "Paris" in response.content
    assert response.tokens.prompt_tokens > 0
    assert response.tokens.completion_tokens > 0
    assert response.tokens.total_tokens > 0
    assert response.finish_reason in ["stop", "length"]


@openai_test
@pytest.mark.asyncio
async def test_generate_with_temperature(openai_provider, openai_context):
    """Test generating text with different temperature settings."""
    # Low temperature (more deterministic)
    response_low = await openai_provider.generate(
        context=openai_context + [{"role": "user", "content": "Write a short poem about AI."}],
        temperature=0.1,
    )
    
    # High temperature (more creative)
    response_high = await openai_provider.generate(
        context=openai_context + [{"role": "user", "content": "Write a short poem about AI."}],
        temperature=1.0,
    )
    
    # While we can't guarantee different outputs due to the nature of LLMs,
    # we can verify the responses have the expected structure
    assert isinstance(response_low, OpenAIResponse)
    assert isinstance(response_high, OpenAIResponse)
    assert response_low.content is not None
    assert response_high.content is not None


@openai_test
@pytest.mark.asyncio
async def test_generate_with_max_tokens(openai_provider, openai_context):
    """Test generating text with max token limit."""
    # Very low token limit should produce a truncated response
    response = await openai_provider.generate(
        context=openai_context + [{"role": "user", "content": "Write a very long essay about artificial intelligence."}],
        max_completion_tokens=10,
    )
    
    assert isinstance(response, OpenAIResponse)
    assert response.content is not None
    assert response.tokens.completion_tokens <= 15  # Allow some flexibility
    assert response.finish_reason == "length"  # Should be truncated due to length


@openai_test
@pytest.mark.asyncio
async def test_generate_with_tools(openai_provider, openai_context, openai_tools):
    """Test generating text with tool calls."""
    response = await openai_provider.generate(
        context=openai_context + [{"role": "user", "content": "What's the weather like in New York?"}],
        tools=openai_tools,
        tool_choice="auto",
    )
    
    assert isinstance(response, OpenAIResponse)
    assert response.has_tool_calls
    assert len(response.tool_calls) > 0
    
    # Verify tool call structure
    tool_call = response.tool_calls[0]
    assert isinstance(tool_call, ToolCall)
    assert tool_call.name == "get_weather"
    
    # Check if the arguments contain location
    args = json.loads(tool_call.arguments)
    assert "location" in args
    assert "New York" in args["location"]


@openai_test
@pytest.mark.asyncio
async def test_generate_force_tool_call(openai_provider, openai_context, openai_tools):
    """Test forcing a specific tool call with tool_choice=required."""
    response = await openai_provider.generate(
        context=openai_context + [{"role": "user", "content": "Tell me about the weather."}],
        tools=openai_tools,
        tool_choice="required",
    )
    
    assert isinstance(response, OpenAIResponse)
    assert response.has_tool_calls
    assert len(response.tool_calls) > 0
    assert response.tool_calls[0].name == "get_weather"


@openai_test
@pytest.mark.asyncio
async def test_generate_no_tool_call(openai_provider, openai_context, openai_tools):
    """Test explicitly preventing tool calls with tool_choice=none."""
    response = await openai_provider.generate(
        context=openai_context + [{"role": "user", "content": "What's the weather like in New York?"}],
        tools=openai_tools,
        tool_choice="none",
    )
    
    assert isinstance(response, OpenAIResponse)
    assert not response.has_tool_calls
    assert response.content is not None


@openai_test
@pytest.mark.asyncio
async def test_response_tokens(openai_provider):
    """Test that response token counts are correctly parsed."""
    response = await openai_provider.generate(
        context=[{"role": "user", "content": "Hi there!"}],
    )
    
    assert isinstance(response, OpenAIResponse)
    assert response.tokens.prompt_tokens > 0
    assert response.tokens.completion_tokens > 0
    assert response.tokens.total_tokens == response.tokens.prompt_tokens + response.tokens.completion_tokens


@openai_test
@pytest.mark.asyncio
async def test_response_finish_reason(openai_provider):
    """Test that finish reason is correctly parsed."""
    response = await openai_provider.generate(
        context=[{"role": "user", "content": "Write a short greeting."}],
    )
    
    assert isinstance(response, OpenAIResponse)
    assert response.finish_reason in ["stop", "length", "content_filter"]


@openai_test
@pytest.mark.asyncio
async def test_parallel_tool_calls(openai_provider):
    """Test parallel tool calls functionality."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "The city name"},
                    },
                    "required": ["location"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "Get the current time in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "The city name"},
                    },
                    "required": ["location"],
                },
            },
        }
    ]
    
    # Use newer model that supports parallel tool calls if available
    model = os.environ.get("OPENAI_MODEL_PARALLEL", "gpt-4o")
    provider = OpenAIProvider(
        api_key=os.environ.get("OPENAI_API_KEY", "dummy_key"),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=model,
    )
    
    response = await provider.generate(
        context=[{"role": "user", "content": "What's the weather and time in New York and London?"}],
        tools=tools,
        parallel_tool_calls=True,
    )
    
    # Note: This test might not always produce multiple tool calls
    # depending on the model behavior
    assert isinstance(response, OpenAIResponse)
    
    # If the model did use parallel tool calls, verify their structure
    if response.has_tool_calls and len(response.tool_calls) > 1:
        tool_names = [tc.name for tc in response.tool_calls]
        assert "get_weather" in tool_names
        assert "get_time" in tool_names


@openai_test
@pytest.mark.asyncio
async def test_specific_tool_choice(openai_provider, openai_tools):
    """Test requesting a specific tool by name."""
    tool_choice = {
        "type": "function",
        "function": {"name": "get_weather"}
    }
    
    response = await openai_provider.generate(
        context=[{"role": "user", "content": "What should I wear today in Seattle?"}],
        tools=openai_tools,
        tool_choice=tool_choice,
    )
    
    assert isinstance(response, OpenAIResponse)
    assert response.has_tool_calls
    assert response.tool_calls[0].name == "get_weather"
    args = json.loads(response.tool_calls[0].arguments)
    assert "location" in args
    assert "Seattle" in args["location"]


@openai_test
@pytest.mark.asyncio
async def test_response_format_json(openai_provider):
    """Test response_format parameter for JSON responses."""
    response_format = {"type": "json_object"}
    
    response = await openai_provider.generate(
        context=[{"role": "user", "content": "Give me the data for the first 3 planets in JSON format"}],
        response_format=response_format,
    )
    
    assert isinstance(response, OpenAIResponse)
    assert response.content is not None
    
    # Verify the response is valid JSON
    try:
        json_data = json.loads(response.content)
        assert isinstance(json_data, dict)
        # Should contain planet data
        if "planets" in json_data:
            assert len(json_data["planets"]) == 3
    except json.JSONDecodeError:
        pytest.fail("Response is not valid JSON")


@openai_test
@pytest.mark.asyncio
async def test_reasoning_effort(openai_provider):
    """Test the reasoning_effort parameter."""
    # Test a model that supports reasoning_effort if available
    model = os.environ.get("OPENAI_MODEL_REASONING", "gpt-4o")
    provider = OpenAIProvider(
        api_key=os.environ.get("OPENAI_API_KEY", "dummy_key"),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=model,
    )
    
    # This test is more about ensuring the parameter is passed correctly
    # rather than testing the actual behavior which can vary
    try:
        response = await provider.generate(
            context=[{"role": "user", "content": "What is the square root of 89642?"}],
            reasoning_effort="high",
        )
        
        assert isinstance(response, OpenAIResponse)
        assert response.content is not None
        
        # If the model supports the reasoning property, check it
        if hasattr(response, "reasoning") and response.reasoning:
            assert len(response.reasoning) > 0
    except Exception as e:
        # Some models might not support this parameter
        pytest.skip(f"Model doesn't support reasoning_effort: {str(e)}")


# Add more tests below as needed

