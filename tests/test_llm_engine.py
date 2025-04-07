"""Tests for the LLM Engine module."""

import pytest
import pytest_asyncio

from llmgine.bus import FakeMessageBus
from llmgine.llm.context import InMemoryContextManager
from llmgine.llm.engine import LLMEngine, LLMResponseEvent, PromptCommand
from llmgine.llm.engine.messages import ClearHistoryCommand, SystemPromptCommand
from llmgine.llm.providers import DefaultLLMManager, DummyProvider
from llmgine.llm.tools import ToolCallEvent, ToolManager


class TestLLMEngine:
    """Tests for the LLM engine module."""

    @pytest_asyncio.fixture
    async def fake_bus(self):
        """Create a fake message bus for testing."""
        bus = FakeMessageBus()
        return bus

    @pytest_asyncio.fixture
    async def llm_manager(self):
        """Create an LLM manager with a dummy provider."""
        manager = DefaultLLMManager()
        dummy_provider = DummyProvider()
        manager.register_provider("dummy", dummy_provider)
        return manager

    # No longer need an LLM router fixture

    @pytest_asyncio.fixture
    async def context_manager(self):
        """Create a context manager."""
        return InMemoryContextManager(max_context_length=10)

    @pytest_asyncio.fixture
    async def tool_manager(self):
        """Create a tool manager with test tools."""
        manager = ToolManager()

        # Register test tools
        def echo(message: str) -> str:
            """Echo a message back."""
            return f"Echo: {message}"

        def calculator(expression: str) -> float:
            """Calculate a mathematical expression."""
            return eval(expression)

        manager.register_tool(echo)
        manager.register_tool(calculator)

        return manager

    @pytest_asyncio.fixture
    async def engine(self, fake_bus, llm_manager, context_manager, tool_manager):
        """Create an LLM engine for testing."""
        return LLMEngine(fake_bus, llm_manager, context_manager, tool_manager)

    @pytest.mark.asyncio
    async def test_system_prompt(self, engine, fake_bus):
        """Test setting a system prompt."""
        # Set system prompt
        command = SystemPromptCommand("You are a helpful assistant.")
        result = await fake_bus.execute(command)

        # Check result
        assert result.success

        # Check conversation context
        context = engine.context_manager.get_context("default")
        assert len(context) == 1
        assert context[0]["role"] == "system"
        assert context[0]["content"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_clear_history(self, engine, fake_bus):
        """Test clearing conversation history."""
        # Add some history
        engine.context_manager.add_message("default", {"role": "system", "content": "System prompt"})
        engine.context_manager.add_message("default", {"role": "user", "content": "Hello"})

        # Clear history
        command = ClearHistoryCommand()
        result = await fake_bus.execute(command)

        # Check result
        assert result.success

        # Check that context is empty
        context = engine.context_manager.get_context("default")
        assert len(context) == 0

    @pytest.mark.asyncio
    async def test_handle_prompt(self, engine, fake_bus):
        """Test handling a prompt command."""
        # Execute prompt command
        command = PromptCommand("Hello, how are you?")
        result = await fake_bus.execute(command)

        # Check result
        assert result.success
        assert "dummy response" in result.result.lower()

        # Check conversation context
        context = engine.context_manager.get_context("default")
        assert len(context) == 2
        assert context[0]["role"] == "user"
        assert context[0]["content"] == "Hello, how are you?"
        assert context[1]["role"] == "assistant"

        # Check that response event was published
        assert len(fake_bus.published_events) == 1
        assert isinstance(fake_bus.published_events[0], LLMResponseEvent)
        assert fake_bus.published_events[0].prompt == "Hello, how are you?"

    @pytest.mark.asyncio
    async def test_handle_tool_call(self, engine, fake_bus):
        """Test handling a tool call event directly."""
        # Create a tool call event
        event = ToolCallEvent("echo", {"message": "Hello, world!"})

        # Execute the event
        result = await fake_bus.execute(event)

        # Check result
        assert result.success
        assert result.result == "Echo: Hello, world!"
