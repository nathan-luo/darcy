"""
This module provides a thorough test suit for the OpenAIProvider class,
specifically the generate method.

1. Opening call with content and normal finish reason. Provide temperature and reasoning effort parameters.
2. An error is successfully raised.
3. A default tool with get weather function (parallel is false) with tool finish reason
4. Parallel is true, prompt both get_weather and get_email functions.
5. Max tokens as finish reason
6. Tool choice is auto
7. Tool choice is none
8. Tool choice is required
9. Complete deterministic response with temperature set to 0.0

Each test will create a corresponding file to the test name in the
tests/llm/providers/openai_response_test directory to save the llm response,
if such file exists, the tests will not make real api call to the OpenAI API.
"""

import pytest
import os
import json
from openai.types.chat import ChatCompletion
from llmgine.llm.providers.openai_provider import OpenAIProvider

# =================== TEST TOOLS ===================

TOOLS = [
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_location",
            "description": "Get the location of a given name",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the person"},
                },
                "required": ["name"],
            },
        },
    },
]


@pytest.fixture
def openai_provider_4o_mini():
    return OpenAIProvider(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
    )


@pytest.fixture
def openai_provider_o3_mini():
    return OpenAIProvider(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url="https://api.openai.com/v1",
        model="o3-mini-2025-01-31",
    )


def get_saved_response(test_name: str):
    response = None
    if os.path.exists(f"tests/llm/providers/openai_responses/{test_name}.json"):
        with open(f"tests/llm/providers/openai_responses/{test_name}.json", "r") as f:
            response = json.load(f)
    return response


def save_response(test_name: str, response: ChatCompletion):
    file_path = f"tests/llm/providers/openai_responses/{test_name}.json"
    if not os.path.exists(file_path):
        # Convert ChatCompletion to a dictionary
        serialized_response = response.model_dump_json()

        with open(file_path, "w") as f:
            f.write(serialized_response)


@pytest.mark.asyncio
async def test_normal_call_o3_mini(openai_provider_o3_mini):
    parsed_response = get_saved_response("test_normal_call_o3_mini")
    if parsed_response is None:
        response = await openai_provider_o3_mini.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, how are you?"},
            ],
            reasoning_effort="low",
            temperature=None,
            test=True,
        )

        save_response("test_normal_call_o3_mini", response)
        parsed_response = get_saved_response("test_normal_call_o3_mini")

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["message"]["content"] is not None
    assert parsed_response["choices"][0]["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_normal_call_4o_mini(openai_provider_4o_mini):
    parsed_response = get_saved_response("test_normal_call_4o_mini")
    if parsed_response is None:
        response = await openai_provider_4o_mini.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, how are you?"},
            ],
            temperature=0.5,
            test=True,
        )

        save_response("test_normal_call_4o_mini", response)
        parsed_response = get_saved_response("test_normal_call_4o_mini")

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["message"]["content"] is not None
    assert parsed_response["choices"][0]["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_error_4o_mini(openai_provider_4o_mini):
    with pytest.raises(Exception) as e:
        await openai_provider_4o_mini.generate(
            context=[
                {"role": "developer", "message": "You are a helpful assistant."},
                {"role": "user", "message": "Hello, how are you?"},
            ],
            test=True,
        )

    assert "Error code: 400" in str(e.value)


@pytest.mark.asyncio
async def test_default_tool_call_4o_mini(openai_provider_4o_mini):
    parsed_response = get_saved_response("test_default_tool_call_4o_mini")
    if parsed_response is None:
        response = await openai_provider_4o_mini.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, what's the weather today in Tokyo?"},
            ],
            tools=TOOLS,
            test=True,
        )

        save_response("test_default_tool_call_4o_mini", response)
        parsed_response = get_saved_response("test_default_tool_call_4o_mini")

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["message"]["tool_calls"] is not None
    assert (
        parsed_response["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
        == "get_weather"
    )


@pytest.mark.asyncio
async def test_parallel_tool_call_4o_mini(openai_provider_4o_mini):
    parsed_response = get_saved_response("test_parallel_tool_call_4o_mini")
    if parsed_response is None:
        response = await openai_provider_4o_mini.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": "Hello, get the weather of Melbourne right now and the location of Darcy",
                },
            ],
            tools=TOOLS,
            parallel_tool_calls=True,
            test=True,
        )

        save_response("test_parallel_tool_call_4o_mini", response)
        parsed_response = get_saved_response("test_parallel_tool_call_4o_mini")

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["message"]["tool_calls"] is not None
    assert len(parsed_response["choices"][0]["message"]["tool_calls"]) == 2
    assert (
        parsed_response["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
        == "get_weather"
    )
    assert (
        parsed_response["choices"][0]["message"]["tool_calls"][1]["function"]["name"]
        == "get_location"
    )


@pytest.mark.asyncio
async def test_max_tokens_4o_mini(openai_provider_4o_mini):
    parsed_response = get_saved_response("test_max_tokens_4o_mini")
    if parsed_response is None:
        response = await openai_provider_4o_mini.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, what's the weather today in Tokyo?"},
            ],
            max_completion_tokens=1,
            test=True,
        )

        save_response("test_max_tokens_4o_mini", response)
        parsed_response = get_saved_response("test_max_tokens_4o_mini")

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["finish_reason"] == "length"
    assert parsed_response["choices"][0]["message"]["content"] is not None
    assert len(parsed_response["choices"][0]["message"]["content"].split(" ")) == 1


@pytest.mark.asyncio
async def test_tool_choice_auto_4o_mini(openai_provider_4o_mini):
    parsed_response = get_saved_response("test_tool_choice_auto_4o_mini")
    if parsed_response is None:
        response = await openai_provider_4o_mini.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, what's the weather today in Tokyo?"},
            ],
            tool_choice="auto",
            tools=TOOLS,
            test=True,
        )

        save_response("test_tool_choice_auto_4o_mini", response)
        parsed_response = get_saved_response("test_tool_choice_auto_4o_mini")

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["finish_reason"] == "tool_calls"
    assert parsed_response["choices"][0]["message"]["tool_calls"] is not None
    assert (
        parsed_response["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
        == "get_weather"
    )


@pytest.mark.asyncio
async def test_tool_choice_none_4o_mini(openai_provider_4o_mini):
    parsed_response = get_saved_response("test_tool_choice_none_4o_mini")
    if parsed_response is None:
        response = await openai_provider_4o_mini.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, what's the weather today in Tokyo?"},
            ],
            tool_choice="none",
            test=True,
        )

        save_response("test_tool_choice_none_4o_mini", response)
        parsed_response = get_saved_response("test_tool_choice_none_4o_mini")

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["finish_reason"] == "stop"
    assert parsed_response["choices"][0]["message"]["tool_calls"] is None


@pytest.mark.asyncio
async def test_tool_choice_required_4o_mini(openai_provider_4o_mini):
    parsed_response = get_saved_response("test_tool_choice_required_4o_mini")
    if parsed_response is None:
        response = await openai_provider_4o_mini.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, how's your day going?"},
            ],
            tool_choice="required",
            tools=[TOOLS[0]],
            test=True,
        )

        save_response("test_tool_choice_required_4o_mini", response)
        parsed_response = get_saved_response("test_tool_choice_required_4o_mini")

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["finish_reason"] == "tool_calls"
    assert parsed_response["choices"][0]["message"]["tool_calls"] is not None
    assert (
        parsed_response["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
        == "get_weather"
    )


@pytest.mark.asyncio
async def test_deterministic_response_4o_mini(openai_provider_4o_mini):
    parsed_response = get_saved_response("test_deterministic_response_4o_mini")
    if parsed_response is None:
        response = await openai_provider_4o_mini.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "How's your day going?"},
            ],
            temperature=0.0,
            test=True,
        )

        save_response("test_deterministic_response_4o_mini", response)
        parsed_response = get_saved_response("test_deterministic_response_4o_mini")

    # Get another response with the same prompt
    response = await openai_provider_4o_mini.generate(
        context=[
            {"role": "developer", "content": "You are a helpful assistant."},
            {"role": "user", "content": "How's your day going?"},
        ],
        temperature=0.0,
        test=True,
    )

    # checks
    assert parsed_response is not None
    assert (
        parsed_response["choices"][0]["message"]["content"]
        == response.choices[0].message.content
    )
