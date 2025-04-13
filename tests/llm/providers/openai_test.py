import pytest
import os
from llmgine.llm.providers.openai import (
    OpenAIProvider,
)  # Assuming this is the correct path

# Marker for tests requiring OpenAI API key and making real calls
# Run with: pytest -m integration
integration_test = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable",
)


@pytest.mark.integration
def test_openai_provider_real_api_call():
    """
    Tests the OpenAIProvider by making a real API call.
    Requires the OPENAI_API_KEY environment variable to be set.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set, skipping real API call test.")

    # Assuming OpenAIProvider takes api_key in constructor
    # Adjust initialization if needed based on your implementation
    provider = OpenAIProvider(api_key=api_key)

    # Adjust the method call and parameters based on your provider's interface
    # Example: calling a generate method
    prompt = "Translate the following English text to French: 'Hello, world!'"
    try:
        # Replace 'generate' and parameters with actual method/args
        response = provider.generate(
            prompt=prompt, model="gpt-3.5-turbo-instruct", max_tokens=60
        )

        # Basic assertions: check if response is a non-empty string
        assert response is not None
        assert isinstance(response, str)
        assert len(response.strip()) > 0
        print(
            f"OpenAI API Response: {response}"
        )  # Optional: print response for manual verification

    except Exception as e:
        pytest.fail(f"OpenAI API call failed with exception: {e}")


# Add more tests below as needed

