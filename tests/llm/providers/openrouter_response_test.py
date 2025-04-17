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
import icecream as ic

from llmgine.llm.providers.openrouter import OpenRouterProvider
from tests.llm.providers.utils import (
    get_saved_response,
    save_response_chat_completion,
)
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
def openrouter_lambda_provider_deepseek_v3():
    return OpenRouterProvider(
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        model="openai/gpt-4.1",
    )


@pytest.fixture
def openrouter_gemini_provider_20_flash():
    return OpenRouterProvider(
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        model="google/gemini-2.0-flash-001",
        provider="Google",
    )


@pytest.mark.asyncio
async def test_normal_call_deepseek_v3(openrouter_lambda_provider_deepseek_v3):
    parsed_response = get_saved_response(
        "test_normal_call_deepseek_v3", "openrouter_responses"
    )
    if parsed_response is None:
        response = await openrouter_lambda_provider_deepseek_v3.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, how are you?"},
            ],
            temperature=0.5,
            test=True,
        )
        save_response_chat_completion(
            "test_normal_call_deepseek_v3", response, "openrouter_responses"
        )
        parsed_response = get_saved_response(
            "test_normal_call_deepseek_v3", "openrouter_responses"
        )

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["message"]["content"] is not None
    assert parsed_response["choices"][0]["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_error_deepseek_v3(openrouter_lambda_provider_deepseek_v3):
    with pytest.raises(Exception) as e:
        await openrouter_lambda_provider_deepseek_v3.generate(
            context=[
                {"role": "developer", "message": "You are a helpful assistant."},
                {"role": "user", "message": "Hello, how are you?"},
            ],
            test=True,
        )

    assert "Error code" in str(e.value)


@pytest.mark.asyncio
async def test_default_tool_call_deepseek_v3(openrouter_lambda_provider_deepseek_v3):
    # parsed_response = get_saved_response(
    #     "test_default_tool_call_deepseek_v3", "openrouter_responses"
    # )
    parsed_response = None
    if parsed_response is None:
        response = await openrouter_lambda_provider_deepseek_v3.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": "Hello, what's the weather today in Tokyo, use your tools.",
                },
            ],
            tools=TOOLS,
            tool_choice="required",
            test=True,
        )
        print(response)
        save_response_chat_completion(
            "test_default_tool_call_deepseek_v3", response, "openrouter_responses"
        )
        parsed_response = get_saved_response(
            "test_default_tool_call_deepseek_v3", "openrouter_responses"
        )

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["message"]["tool_calls"] is not None
    assert (
        parsed_response["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
        == "get_weather"
    )


@pytest.mark.asyncio
async def test_default_tool_call_gemini_20_flash(
    openrouter_gemini_provider_20_flash,
):
    parsed_response = get_saved_response(
        "test_default_tool_call_gemini_20_flash", "openrouter_responses"
    )
    if parsed_response is None:
        response = await openrouter_gemini_provider_20_flash.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": "Hello, what's the weather today in Tokyo, use your tools.",
                },
            ],
            tools=TOOLS,
            test=True,
        )
        print(response)
        save_response_chat_completion(
            "test_default_tool_call_gemini_20_flash", response, "openrouter_responses"
        )
        parsed_response = get_saved_response(
            "test_default_tool_call_gemini_20_flash", "openrouter_responses"
        )

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["message"]["tool_calls"] is not None
    assert (
        parsed_response["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
        == "get_weather"
    )


@pytest.mark.asyncio
async def test_parallel_tool_call_deepseek_v3(openrouter_lambda_provider_deepseek_v3):
    parsed_response = get_saved_response(
        "test_parallel_tool_call_deepseek_v3", "openrouter_responses"
    )
    if parsed_response is None:
        response = await openrouter_lambda_provider_deepseek_v3.generate(
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

        save_response_chat_completion(
            "test_parallel_tool_call_deepseek_v3", response, "openrouter_responses"
        )
        parsed_response = get_saved_response(
            "test_parallel_tool_call_deepseek_v3", "openrouter_responses"
        )

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
async def test_max_tokens_deepseek_v3(openrouter_lambda_provider_deepseek_v3):
    parsed_response = get_saved_response(
        "test_max_tokens_deepseek_v3", "openrouter_responses"
    )
    if parsed_response is None:
        response = await openrouter_lambda_provider_deepseek_v3.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, what's the weather today in Tokyo?"},
            ],
            max_completion_tokens=1,
            test=True,
        )

        save_response_chat_completion(
            "test_max_tokens_deepseek_v3", response, "openrouter_responses"
        )
        parsed_response = get_saved_response(
            "test_max_tokens_deepseek_v3", "openrouter_responses"
        )

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["finish_reason"] == "length"
    assert parsed_response["choices"][0]["message"]["content"] is not None
    assert len(parsed_response["choices"][0]["message"]["content"].split(" ")) == 1


@pytest.mark.asyncio
async def test_tool_choice_auto_deepseek_v3(openrouter_lambda_provider_deepseek_v3):
    parsed_response = get_saved_response(
        "test_tool_choice_auto_deepseek_v3", "openrouter_responses"
    )
    if parsed_response is None:
        response = await openrouter_lambda_provider_deepseek_v3.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, what's the weather today in Tokyo?"},
            ],
            tool_choice="auto",
            tools=TOOLS,
            test=True,
        )

        save_response_chat_completion(
            "test_tool_choice_auto_deepseek_v3", response, "openrouter_responses"
        )
        parsed_response = get_saved_response(
            "test_tool_choice_auto_deepseek_v3", "openrouter_responses"
        )

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["finish_reason"] == "tool_calls"
    assert parsed_response["choices"][0]["message"]["tool_calls"] is not None
    assert (
        parsed_response["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
        == "get_weather"
    )


@pytest.mark.asyncio
async def test_tool_choice_none_deepseek_v3(openrouter_lambda_provider_deepseek_v3):
    parsed_response = get_saved_response(
        "test_tool_choice_none_deepseek_v3", "openrouter_responses"
    )
    if parsed_response is None:
        response = await openrouter_lambda_provider_deepseek_v3.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, what's the weather today in Tokyo?"},
            ],
            tool_choice="none",
            test=True,
        )

        save_response_chat_completion(
            "test_tool_choice_none_deepseek_v3", response, "openrouter_responses"
        )
        parsed_response = get_saved_response(
            "test_tool_choice_none_deepseek_v3", "openrouter_responses"
        )

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["finish_reason"] == "stop"
    assert parsed_response["choices"][0]["message"]["tool_calls"] is None


@pytest.mark.asyncio
async def test_tool_choice_required_deepseek_v3(openrouter_lambda_provider_deepseek_v3):
    parsed_response = get_saved_response(
        "test_tool_choice_required_deepseek_v3", "openrouter_responses"
    )
    if parsed_response is None:
        response = await openrouter_lambda_provider_deepseek_v3.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, how's your day going?"},
            ],
            tool_choice="required",
            tools=[TOOLS[0]],
            test=True,
        )

        save_response_chat_completion(
            "test_tool_choice_required_deepseek_v3", response, "openrouter_responses"
        )
        parsed_response = get_saved_response(
            "test_tool_choice_required_deepseek_v3", "openrouter_responses"
        )

    # checks
    assert parsed_response is not None
    assert parsed_response["choices"][0]["finish_reason"] == "tool_calls"
    assert parsed_response["choices"][0]["message"]["tool_calls"] is not None
    assert (
        parsed_response["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
        == "get_weather"
    )


@pytest.mark.asyncio
async def test_deterministic_response_deepseek_v3(openrouter_lambda_provider_deepseek_v3):
    parsed_response = get_saved_response(
        "test_deterministic_response_deepseek_v3", "openrouter_responses"
    )
    if parsed_response is None:
        response = await openrouter_lambda_provider_deepseek_v3.generate(
            context=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": "How's your day going?"},
            ],
            temperature=0.0,
            test=True,
        )

        save_response_chat_completion(
            "test_deterministic_response_deepseek_v3", response, "openrouter_responses"
        )
        parsed_response = get_saved_response(
            "test_deterministic_response_deepseek_v3", "openrouter_responses"
        )

    # Get another response with the same prompt
    response = await openrouter_lambda_provider_deepseek_v3.generate(
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
