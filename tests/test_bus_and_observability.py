"""Tests for the message bus system with observability handlers.

This test suite tests the interaction between the MessageBus and observability components,
ensuring that events flow correctly to all subscribed handlers.
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
import tempfile
from typing import Any, Dict, List, Optional

import pytest
import pytest_asyncio

from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.observability.handlers.base import ObservabilityEventHandler
from llmgine.observability.handlers.console import ConsoleEventHandler
from llmgine.observability.handlers.file import FileEventHandler


# Sample command and event classes for testing
class TestCommand(Command):
    """Test command for unit tests."""

    value: str = ""


class TestEvent(Event):
    """Test event for unit tests."""

    value: str = ""
    other_data: Dict[str, Any] = field(default_factory=dict)


# Custom event handler for testing
class TestEventHandler(ObservabilityEventHandler):
    """A test event handler that records all events it receives."""

    def __init__(self):
        super().__init__()
        self.events: List[Event] = []
        self.all_events: List[Event] = []  # All events including internal ones

    async def handle(self, event: Event) -> None:
        """Record the event in the events list."""
        self.all_events.append(event)

        # Only record TestEvent instances in the main events list
        if isinstance(event, TestEvent):
            self.events.append(event)

    def get_events_by_type(self, event_type: type) -> List[Event]:
        """Get all events of a specific type."""
        return [e for e in self.all_events if isinstance(e, event_type)]


class TestBusAndObservability:
    """Tests for bus and observability integration."""

    @pytest_asyncio.fixture
    async def bus(self):
        """Create and start a MessageBus for testing."""
        bus = MessageBus()
        await bus.start()
        yield bus
        await bus.stop()

    @pytest_asyncio.fixture
    async def test_handler(self, bus):
        """Create a test event handler and register it with the bus."""
        handler = TestEventHandler()

        # Register the handler for all Event types (using global session for simplicity)
        bus.register_event_handler("global", Event, handler.handle)

        # Wait a bit for the registration to be processed
        await asyncio.sleep(0.1)

        yield handler

    @pytest.mark.asyncio
    async def test_bus_initialization(self):
        """Test that the bus can be initialized and stopped correctly."""
        bus = MessageBus()
        assert bus._initialized is True

        await bus.start()
        assert bus._processing_task is not None

        await bus.stop()
        assert bus._processing_task is None

    @pytest.mark.asyncio
    async def test_register_observability_handlers(self, bus):
        """Test registering multiple observability handlers."""
        # Create handlers
        console_handler = ConsoleEventHandler()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_handler = FileEventHandler(log_dir=temp_dir)
            test_handler = TestEventHandler()

            # Register handlers for all Events, not just TestEvent
            bus.register_event_handler("global", Event, console_handler.handle)
            bus.register_event_handler("global", Event, file_handler.handle)
            bus.register_event_handler("global", Event, test_handler.handle)

            # Publish an event
            event = TestEvent(value="test_event")
            event.metadata["key"] = "value"  # Add some metadata to verify
            await bus.publish(event)

            # Allow time for async processing
            await asyncio.sleep(0.1)

            # Verify test handler received the event
            assert len(test_handler.events) == 1
            assert test_handler.events[0].value == "test_event"

            # Verify file was created (we can't check console output easily)
            log_files = os.listdir(temp_dir)
            assert len(log_files) == 1
            log_path = os.path.join(temp_dir, log_files[0])

            # Check that the file exists and contains some content
            assert os.path.exists(log_path)
            assert os.path.getsize(log_path) > 0

            # Just verify a file was created with content
            # We can't reliably test the exact format of the serialized event
            # since that's implementation-dependent
            with open(log_path, "r") as f:
                log_content = f.read()
                # Verify it contains some basic information we expect
                assert "TestEvent" in log_content
                assert log_content.strip()  # Not empty

    @pytest.mark.asyncio
    async def test_event_publishing_to_handlers(self, bus):
        """Test that regular events are correctly sent to all handlers."""
        # Create a local handler just for this test
        local_handler = TestEventHandler()
        bus.register_event_handler("global", TestEvent, local_handler.handle)

        # Publish an event
        event = TestEvent(value="handler_test")
        await bus.publish(event)

        # Allow time for async processing
        await asyncio.sleep(0.1)

        # Verify handler received the event
        assert len(local_handler.events) == 1
        assert local_handler.events[0].value == "handler_test"

    @pytest.mark.asyncio
    async def test_session_specific_handlers(self, bus):
        """Test that session-specific handlers only receive events for their session."""
        # Create handlers for different sessions
        global_handler = TestEventHandler()
        session1_handler = TestEventHandler()
        session2_handler = TestEventHandler()

        # Register handlers
        bus.register_event_handler("global", TestEvent, global_handler.handle)
        bus.register_event_handler("session1", TestEvent, session1_handler.handle)
        bus.register_event_handler("session2", TestEvent, session2_handler.handle)

        # Publish events with different session IDs
        global_event = TestEvent(value="global_event")  # No session
        session1_event = TestEvent(value="session1_event")
        session1_event.session_id = "session1"
        session2_event = TestEvent(value="session2_event")
        session2_event.session_id = "session2"

        await bus.publish(global_event)
        await bus.publish(session1_event)
        await bus.publish(session2_event)

        # Allow time for async processing
        await asyncio.sleep(0.2)

        # Global handler should receive all events
        assert len(global_handler.events) == 3
        assert any(e.value == "global_event" for e in global_handler.events)
        assert any(e.value == "session1_event" for e in global_handler.events)
        assert any(e.value == "session2_event" for e in global_handler.events)

        # Session-specific handlers should only receive events for their session
        # and global events
        assert len(session1_handler.events) == 2
        assert any(e.value == "global_event" for e in session1_handler.events)
        assert any(e.value == "session1_event" for e in session1_handler.events)
        assert not any(e.value == "session2_event" for e in session1_handler.events)

        assert len(session2_handler.events) == 2
        assert any(e.value == "global_event" for e in session2_handler.events)
        assert not any(e.value == "session1_event" for e in session2_handler.events)
        assert any(e.value == "session2_event" for e in session2_handler.events)

    @pytest.mark.asyncio
    async def test_command_execution(self, bus):
        """Test that commands can be executed and results returned."""

        # Register a command handler
        async def handle_command(cmd: TestCommand) -> CommandResult:
            # Just echo back the command value with "result_" prefix
            return CommandResult(
                success=True,
                original_command=cmd,
                result=f"result_{cmd.value}",
            )

        bus.register_command_handler("global", TestCommand, handle_command)

        # Execute a command
        command = TestCommand(value="test_command")
        result = await bus.execute(command)

        # Verify the result
        assert result.success is True
        assert result.result == "result_test_command"

    @pytest.mark.asyncio
    async def test_error_in_event_handler(self, bus):
        """Test that errors in event handlers don't crash the system."""

        # Create a handler that raises an exception
        class ErrorHandler(ObservabilityEventHandler):
            def __init__(self):
                super().__init__()
                self.handled_count = 0

            async def handle(self, event: Event) -> None:
                # Only process TestEvent instances
                if isinstance(event, TestEvent):
                    self.handled_count += 1
                    raise RuntimeError("Test error")

        # Create a working handler to verify events still flow
        working_handler = TestEventHandler()

        # Register both handlers
        error_handler = ErrorHandler()
        bus.register_event_handler("global", TestEvent, error_handler.handle)
        bus.register_event_handler("global", TestEvent, working_handler.handle)

        # Publish an event
        event = TestEvent(value="error_test")
        await bus.publish(event)

        # Allow time for async processing
        await asyncio.sleep(0.1)

        # Verify the error handler was called (it should increment counter before error)
        assert error_handler.handled_count == 1

        # Verify the working handler still received the event
        assert len(working_handler.events) == 1
        assert working_handler.events[0].value == "error_test"
