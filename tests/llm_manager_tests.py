import os
import pytest
from dotenv import load_dotenv
from llmgine.llm.providers.response import OpenAIManager
from llmgine.llm.providers.response import DefaultLLMResponse

pytestmark = pytest.mark.asyncio  # All tests here are async

load_dotenv()

@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_TESTS"),
    reason="Set RUN_LIVE_TESTS=1 to run live OpenAI tests"
)
async def test_openai_manager_with_real_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    assert api_key, "OPENAI_API_KEY environment variable is not set"

    manager = OpenAIManager(api_key=api_key)
    response: DefaultLLMResponse = await manager.generate(context=[{"role": "user", "content": "What is the capital of France?"}])
    print(response.content)
    # ✅ Basic validations
    assert isinstance(response.content, str), "Expected content to be a string"
    assert "Paris" in response.content, "Expected content to mention Paris"
    assert response.usage.total_tokens > 0, "Expected non-zero token usage"
    assert response.finish_reason == "stop", "Expected finish_reason to be 'stop'"


