"""Tests for the event logger."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from llmgine.bus import FakeMessageBus
from llmgine.llm.engine import LLMResponseEvent
from llmgine.observability.logging.event_logger import EventLogger
from llmgine.llm.tools import ToolCallEvent, ToolResultEvent
from llmgine.ui.cli.interface import MessageDisplayedEvent, UserInputReceivedEvent


class TestEventLogger:
    """Tests for the event logger."""

    @pytest_asyncio.fixture
    async def fake_bus(self):
        """Create a fake message bus for testing."""
        return FakeMessageBus()

    @pytest_asyncio.fixture
    async def temp_dir(self):
        """Create a temporary directory for logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest_asyncio.fixture
    async def event_logger(self, fake_bus, temp_dir):
        """Create an event logger for testing."""
        logger = EventLogger(fake_bus, temp_dir)
        return logger

    @pytest.mark.asyncio
    async def test_log_file_creation(self, event_logger, temp_dir):
        """Test that a log file is created."""
        # Check that a log file was created
        log_files = list(Path(temp_dir).glob("*.jsonl"))
        assert len(log_files) == 1
        assert log_files[0].name.startswith("llmgine_")
        assert log_files[0].name.endswith(".jsonl")

    @pytest.mark.asyncio
    async def test_logging_llm_response(self, event_logger, fake_bus):
        """Test logging LLM response events."""
        # Create and publish event
        event = LLMResponseEvent("Test prompt", "Test response")
        await fake_bus.publish(event)

        # Check that event was logged in memory
        events = event_logger.get_events(LLMResponseEvent)
        assert len(events) == 1
        assert events[0]["event_type"] == "LLMResponseEvent"
        assert events[0]["prompt"] == "Test prompt"
        assert events[0]["response"] == "Test response"

    @pytest.mark.asyncio
    async def test_logging_tool_events(self, event_logger, fake_bus):
        """Test logging tool-related events."""
        # Create and publish tool call event
        tool_call = ToolCallEvent("test_tool", {"arg1": "value1"})
        await fake_bus.publish(tool_call)

        # Create and publish tool result event
        tool_result = ToolResultEvent("test_tool", {"arg1": "value1"}, "Test result")
        await fake_bus.publish(tool_result)

        # Check that events were logged in memory
        call_events = event_logger.get_events(ToolCallEvent)
        assert len(call_events) == 1
        assert call_events[0]["event_type"] == "ToolCallEvent"
        assert call_events[0]["tool_name"] == "test_tool"
        assert call_events[0]["arguments"] == {"arg1": "value1"}

        result_events = event_logger.get_events(ToolResultEvent)
        assert len(result_events) == 1
        assert result_events[0]["event_type"] == "ToolResultEvent"
        assert result_events[0]["tool_name"] == "test_tool"
        assert result_events[0]["arguments"] == {"arg1": "value1"}
        assert result_events[0]["result"] == "Test result"

    @pytest.mark.asyncio
    async def test_logging_ui_events(self, event_logger, fake_bus):
        """Test logging UI-related events."""
        # Create and publish UI events
        msg_event = MessageDisplayedEvent("user", "Hello")
        await fake_bus.publish(msg_event)

        input_event = UserInputReceivedEvent("Test input")
        await fake_bus.publish(input_event)

        # Check that events were logged in memory
        msg_events = event_logger.get_events(MessageDisplayedEvent)
        assert len(msg_events) == 1
        assert msg_events[0]["event_type"] == "MessageDisplayedEvent"
        assert msg_events[0]["role"] == "user"
        assert msg_events[0]["content"] == "Hello"

        input_events = event_logger.get_events(UserInputReceivedEvent)
        assert len(input_events) == 1
        assert input_events[0]["event_type"] == "UserInputReceivedEvent"
        assert input_events[0]["input_text"] == "Test input"

    @pytest.mark.asyncio
    async def test_export_events(self, event_logger, fake_bus, temp_dir):
        """Test exporting events to a file."""
        # Create and publish some events
        events = [
            LLMResponseEvent("prompt1", "response1"),
            ToolCallEvent("tool1", {"arg": "val"}),
            MessageDisplayedEvent("user", "message")
        ]

        for event in events:
            await fake_bus.publish(event)

        # Export events
        export_path = os.path.join(temp_dir, "export.json")
        event_logger.export_events(export_path)

        # Check that export file exists
        assert os.path.exists(export_path)

        # Check file contents
        with open(export_path) as f:
            exported = json.load(f)

        assert len(exported) == 3
        assert exported[0]["event_type"] == "LLMResponseEvent"
        assert exported[1]["event_type"] == "ToolCallEvent"
        assert exported[2]["event_type"] == "MessageDisplayedEvent"
