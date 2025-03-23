"""Tests for the CLI interface."""

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from llmgine.bus import FakeMessageBus
from llmgine.llm.engine import LLMResponseEvent
from llmgine.llm.tools import ToolCallEvent, ToolResultEvent
from llmgine.ui.cli.interface import CLIInterface


class TestCLIInterface:
    """Tests for the CLI interface."""

    @pytest_asyncio.fixture
    async def fake_bus(self):
        """Create a fake message bus for testing."""
        return FakeMessageBus()

    @pytest_asyncio.fixture
    async def cli(self, fake_bus):
        """Create a CLI interface for testing with mocked console."""
        with patch("llmgine.ui.cli.interface.Console") as mock_console:
            # Create mock console instance
            console_instance = MagicMock()
            mock_console.return_value = console_instance

            # Create CLI interface
            cli = CLIInterface(fake_bus)

            # Patch prompt to avoid blocking on input
            with patch("llmgine.ui.cli.interface.Prompt"):
                yield cli

    @pytest.mark.asyncio
    async def test_llm_response_handler(self, cli, fake_bus):
        """Test handling LLM response events."""
        # Create and publish event
        event = LLMResponseEvent("Test prompt", "Test response")
        await fake_bus.publish(event)

        # Check that message was printed
        cli.console.print.assert_called()

        # Check that message was stored
        assert len(cli.messages) == 1
        assert cli.messages[0]["role"] == "Assistant"
        assert cli.messages[0]["content"] == "Test response"
        assert cli.messages[0]["style"] == "green"

    @pytest.mark.asyncio
    async def test_tool_call_handler(self, cli, fake_bus):
        """Test handling tool call events."""
        # Create and publish event
        event = ToolCallEvent("test_tool", {"arg1": "value1"})
        await fake_bus.publish(event)

        # Check that message was printed
        cli.console.print.assert_called()

        # Check that message was stored
        assert len(cli.messages) == 1
        assert cli.messages[0]["role"] == "Tool Call"
        assert "test_tool" in cli.messages[0]["content"]
        assert cli.messages[0]["style"] == "yellow"

    @pytest.mark.asyncio
    async def test_tool_result_handler(self, cli, fake_bus):
        """Test handling tool result events."""
        # Create and publish successful result
        event = ToolResultEvent("test_tool", {"arg1": "value1"}, "Test result")
        await fake_bus.publish(event)

        # Check that message was printed
        cli.console.print.assert_called()

        # Check that message was stored
        assert len(cli.messages) == 1
        assert cli.messages[0]["role"] == "Tool Result: test_tool"
        assert cli.messages[0]["content"] == "Test result"
        assert cli.messages[0]["style"] == "bright_yellow"

        # Reset mocks and messages
        cli.console.print.reset_mock()
        cli.messages.clear()

        # Create and publish error result
        error_event = ToolResultEvent(
            "test_tool", {"arg1": "value1"}, None, error="Test error"
        )
        await fake_bus.publish(error_event)

        # Check that message was printed
        cli.console.print.assert_called()

        # Check that message was stored
        assert len(cli.messages) == 1
        assert cli.messages[0]["role"] == "Tool Error: test_tool"
        assert "Test error" in cli.messages[0]["content"]
        assert cli.messages[0]["style"] == "red"

    @pytest.mark.asyncio
    async def test_print_message(self, cli):
        """Test printing messages."""
        # Print a message
        cli.print_message("Test content", "Test Role", "blue")

        # Check that console.print was called
        cli.console.print.assert_called_once()

        # Check that message was stored
        assert len(cli.messages) == 1
        assert cli.messages[0]["role"] == "Test Role"
        assert cli.messages[0]["content"] == "Test content"
        assert cli.messages[0]["style"] == "blue"

    @pytest.mark.asyncio
    async def test_system_message(self, cli):
        """Test printing system messages."""
        # Print a system message
        cli.print_system_message("Test system message")

        # Check that console.print was called
        cli.console.print.assert_called_once()

        # Check that message was stored
        assert len(cli.messages) == 1
        assert cli.messages[0]["role"] == "System"
        assert cli.messages[0]["content"] == "Test system message"
        assert cli.messages[0]["style"] == "cyan"
