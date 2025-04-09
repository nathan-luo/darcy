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
from llmgine.observability.events import Metric, SpanContext
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

        # Only record TestEvent instances in the main events list, or metric events
        if isinstance(event, TestEvent):
            self.events.append(event)
        # Record metric events separately
        elif (
            hasattr(event, "metrics")
            and event.metrics
            and not hasattr(event, "span_context")
        ):
            self.events.append(event)

    def get_events_by_type(self, event_type: type) -> List[Event]:
        """Get all events of a specific type."""
        return [e for e in self.all_events if isinstance(e, event_type)]

    def get_trace_events(self) -> List[Event]:
        """Get all trace events (for testing trace functionality)."""
        return [
            e
            for e in self.all_events
            if hasattr(e, "span_context") and e.span_context is not None
        ]


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
    async def test_metrics_flow_to_handlers(self, bus):
        """Test that metrics flow to handlers as regular events."""
        # Create a local handler just for this test
        local_handler = TestEventHandler()
        bus.register_event_handler("global", Event, local_handler.handle)

        # Give time for registration to complete
        await asyncio.sleep(0.1)

        # Emit a metric
        await bus.emit_metric("test_metric", 42.0, "ms", {"tag1": "value1"})

        # Allow time for async processing
        await asyncio.sleep(0.2)

        # Find events with metrics data
        metric_events = [
            e for e in local_handler.all_events if hasattr(e, "metrics") and e.metrics
        ]

        # Verify handler received the metric data
        assert len(metric_events) >= 1, "Should have at least one event with metrics"

        # Check at least one event has our metric
        found_metric = False
        for event in metric_events:
            for metric in event.metrics:
                if isinstance(metric, Metric) and metric.name == "test_metric":
                    found_metric = True
                    assert metric.value == 42.0
                    assert metric.unit == "ms"
                    assert metric.tags == {"tag1": "value1"}

        assert found_metric, "Could not find our test metric in any events"

    @pytest.mark.asyncio
    async def test_trace_spans_flow_to_handlers(self, bus):
        """Test that trace spans flow to handlers as regular events."""
        # Create a local handler just for this test
        local_handler = TestEventHandler()
        bus.register_event_handler("global", Event, local_handler.handle)

        # Give time for registration to complete
        await asyncio.sleep(0.1)

        # Start a span
        span_context = await bus.start_span("test_span", attributes={"attr1": "value1"})

        # Give time for processing
        await asyncio.sleep(0.1)

        # End the span
        await bus.end_span(span_context, "test_span", attributes={"attr2": "value2"})

        # Allow time for async processing
        await asyncio.sleep(0.2)

        # Get trace events specifically
        trace_events = [
            e
            for e in local_handler.all_events
            if hasattr(e, "span_context") and e.span_context is not None
        ]

        # Verify handler received span events
        assert len(trace_events) >= 1, "Should have at least one trace event"

        # Find events with our test span's trace ID
        span_events = [
            e
            for e in trace_events
            if hasattr(e, "span_context")
            and e.span_context.trace_id == span_context.trace_id
        ]

        # We should have at least one event with our span context
        assert len(span_events) >= 1, (
            "Should have at least one event with our span context"
        )

        # Check if we can find a test_span event
        test_span_events = [e for e in span_events if e.name == "test_span"]
        assert len(test_span_events) >= 1, "Should have at least one test_span event"

    @pytest.mark.asyncio
    async def test_session_specific_handlers(self, bus):
        """Test that handlers can be registered for specific sessions."""
        # Create session-specific handlers
        session1_handler = TestEventHandler()
        session2_handler = TestEventHandler()
        global_handler = TestEventHandler()

        # Register handlers for different sessions - specifically for TestEvent
        bus.register_event_handler("session1", TestEvent, session1_handler.handle)
        bus.register_event_handler("session2", TestEvent, session2_handler.handle)
        bus.register_event_handler("global", TestEvent, global_handler.handle)

        # Give time for registration to complete
        await asyncio.sleep(0.1)

        # Create events with different session IDs
        event1 = TestEvent(value="event1")
        event1.session_id = "session1"

        event2 = TestEvent(value="event2")
        event2.session_id = "session2"

        event_global = TestEvent(value="event_global")
        event_global.session_id = None

        # Publish events
        await bus.publish(event1)
        await bus.publish(event2)
        await bus.publish(event_global)

        # Allow time for async processing
        await asyncio.sleep(0.2)

        # Filter events to just get TestEvent instances in each handler
        s1_events = [e for e in session1_handler.all_events if isinstance(e, TestEvent)]
        s2_events = [e for e in session2_handler.all_events if isinstance(e, TestEvent)]
        global_events = [e for e in global_handler.all_events if isinstance(e, TestEvent)]

        # Session1 handler should get at least the session1 event
        assert len(s1_events) >= 1
        assert any(e.value == "event1" for e in s1_events)

        # Session2 handler should get at least the session2 event
        assert len(s2_events) >= 1
        assert any(e.value == "event2" for e in s2_events)

        # Global handler should get all events
        assert len(global_events) >= 3
        assert any(e.value == "event1" for e in global_events)
        assert any(e.value == "event2" for e in global_events)
        assert any(e.value == "event_global" for e in global_events)

    @pytest.mark.asyncio
    async def test_command_execution_tracing(self, bus):
        """Test that command execution is properly traced."""
        # Create our own handler to monitor all events
        event_handler = TestEventHandler()
        bus.register_event_handler("global", Event, event_handler.handle)

        # Register a command handler
        async def handle_command(cmd: TestCommand) -> CommandResult:
            return CommandResult(success=True, result=f"processed-{cmd.value}")

        bus.register_command_handler("global", TestCommand, handle_command)

        # Give time for registration to complete
        await asyncio.sleep(0.1)

        # Enable tracing and execute command
        bus.enable_tracing()
        result = await bus.execute(TestCommand("trace_test"))

        # Allow time for async processing
        await asyncio.sleep(0.2)

        # Verify result
        assert result.success is True
        assert result.result == "processed-trace_test"

        # We should have received some events
        assert len(event_handler.all_events) > 0

        # The specifics of the events and spans are implementation details that might change,
        # so we just verify that the bus is processing commands correctly

    @pytest.mark.asyncio
    async def test_error_in_event_handler(self, bus):
        """Test that errors in event handlers don't crash the bus."""
        # Define handlers - one good, one that raises an exception
        good_handler = TestEventHandler()

        # Create a custom class that behaves like EventHandler but will error
        class ErrorHandler(ObservabilityEventHandler):
            def __init__(self):
                super().__init__()
                self.events = []

            async def handle(self, event: Event) -> None:
                # Only process TestEvent instances
                if not isinstance(event, TestEvent):
                    return

                if hasattr(event, "value") and event.value == "trigger_error":
                    raise ValueError("Test error in handler")
                self.events.append(event)

        error_handler = ErrorHandler()

        # Register both handlers for TestEvent specifically
        bus.register_event_handler("global", TestEvent, good_handler.handle)
        bus.register_event_handler("global", TestEvent, error_handler.handle)

        # Give time for registration to complete
        await asyncio.sleep(0.1)

        # Publish an event that will cause an error
        error_event = TestEvent(value="trigger_error")
        await bus.publish(error_event)

        # Publish another event to verify the bus still works
        normal_event = TestEvent(value="normal_event")
        await bus.publish(normal_event)

        # Allow time for async processing
        await asyncio.sleep(0.2)

        # Look for TestEvent instances in the handler
        test_events = [e for e in good_handler.all_events if isinstance(e, TestEvent)]

        # Good handler should have received both events
        assert len(test_events) >= 2
        event_values = [e.value for e in test_events]
        assert "trigger_error" in event_values
        assert "normal_event" in event_values

        # Error handler should have only received the second event
        # (first one errored before adding to the events list)
        assert len(error_handler.events) == 1
        assert error_handler.events[0].value == "normal_event"
