"""Tests focusing on event publishing and handling in the message bus."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest
import pytest_asyncio

from llmgine.bus.bus import MessageBus
from llmgine.messages.events import Event


# Test event types
@dataclass
class SimpleEvent(Event):
    """A simple event for testing."""
    value: str = ""
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class DataEvent(Event):
    """An event with structured data for testing."""
    name: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class HierarchicalBaseEvent(Event):
    """Base event for testing inheritance-based handler registration."""
    category: str = "base"


@dataclass
class HierarchicalChildEvent(HierarchicalBaseEvent):
    """Child event inheriting from HierarchicalBaseEvent."""
    subcategory: str = "child"


@dataclass
class HierarchicalGrandchildEvent(HierarchicalChildEvent):
    """Grandchild event inheriting from HierarchicalChildEvent."""
    detail: str = "grandchild"


# Handler helper for tracking event calls
class EventRecorder:
    """Helper class to record events received by handlers."""
    
    def __init__(self, name="default"):
        self.name = name
        self.events: List[Event] = []
        self.last_processed: Optional[float] = None
    
    async def handle_event(self, event: Event):
        """Record the event and when it was processed."""
        self.events.append(event)
        self.last_processed = time.time()
    
    async def handle_with_delay(self, event: Event, delay: float = 0.1):
        """Handle event with a delay to simulate processing time."""
        await asyncio.sleep(delay)
        await self.handle_event(event)
    
    async def handle_with_error(self, event: Event):
        """Handler that raises an exception."""
        self.events.append(event)  # Still record it before raising
        raise ValueError(f"Test error processing event: {type(event).__name__}")
    
    def get_events_by_type(self, event_type: type) -> List[Event]:
        """Get all events of a specific type."""
        return [e for e in self.events if isinstance(e, event_type)]
    
    def clear(self):
        """Clear recorded events."""
        self.events.clear()
        self.last_processed = None


class TestBusEvents:
    """Tests focusing on event handling in the message bus."""
    
    @pytest_asyncio.fixture
    async def bus(self):
        """Create and start a MessageBus for testing."""
        bus = MessageBus()
        await bus.start()
        yield bus
        await bus.stop()
    
    @pytest.mark.asyncio
    async def test_publish_simple_event(self, bus):
        """Test that a simple event can be published and handled."""
        # Create recorder and register handler
        recorder = EventRecorder()
        bus.register_event_handler("global", SimpleEvent, recorder.handle_event)
        
        # Publish event
        event = SimpleEvent("test_publish")
        await bus.publish(event)
        
        # Allow time for async processing
        await asyncio.sleep(0.1)
        
        # Verify event was handled
        assert len(recorder.events) == 1
        assert recorder.events[0].value == "test_publish"
    
    @pytest.mark.asyncio
    async def test_multiple_handlers_for_event(self, bus):
        """Test that multiple handlers can be registered for the same event type."""
        # Create recorders and register handlers
        recorder1 = EventRecorder("recorder1")
        recorder2 = EventRecorder("recorder2")
        recorder3 = EventRecorder("recorder3")
        
        bus.register_event_handler("global", SimpleEvent, recorder1.handle_event)
        bus.register_event_handler("global", SimpleEvent, recorder2.handle_event)
        bus.register_event_handler("global", SimpleEvent, recorder3.handle_event)
        
        # Publish event
        event = SimpleEvent("multiple_handlers")
        await bus.publish(event)
        
        # Allow time for async processing
        await asyncio.sleep(0.1)
        
        # Verify all handlers received the event
        assert len(recorder1.events) == 1
        assert len(recorder2.events) == 1
        assert len(recorder3.events) == 1
        
        # Verify the event content
        assert recorder1.events[0].value == "multiple_handlers"
        assert recorder2.events[0].value == "multiple_handlers"
        assert recorder3.events[0].value == "multiple_handlers"
    
    @pytest.mark.asyncio
    async def test_session_specific_handlers(self, bus):
        """Test that handlers can be registered for specific sessions."""
        # Create recorders for different sessions
        global_recorder = EventRecorder("global")
        session1_recorder = EventRecorder("session1")
        session2_recorder = EventRecorder("session2")
        
        # Register handlers for different sessions
        bus.register_event_handler("global", Event, global_recorder.handle_event)
        bus.register_event_handler("session1", Event, session1_recorder.handle_event)
        bus.register_event_handler("session2", Event, session2_recorder.handle_event)
        
        # Create events with different session IDs
        event1 = SimpleEvent("event1")
        event1.session_id = "session1"
        
        event2 = SimpleEvent("event2")
        event2.session_id = "session2"
        
        event_no_session = SimpleEvent("no_session")
        # No session_id set
        
        # Publish events
        await bus.publish(event1)
        await bus.publish(event2)
        await bus.publish(event_no_session)
        
        # Allow time for async processing
        await asyncio.sleep(0.1)
        
        # Verify correct handlers received events
        # Session1 handler should receive only session1 event
        assert len(session1_recorder.events) == 1
        assert session1_recorder.events[0].value == "event1"
        
        # Session2 handler should receive only session2 event
        assert len(session2_recorder.events) == 1
        assert session2_recorder.events[0].value == "event2"
        
        # Global handler should receive all events
        assert len(global_recorder.events) == 3
        values = [e.value for e in global_recorder.events]
        assert "event1" in values
        assert "event2" in values
        assert "no_session" in values
    
    @pytest.mark.asyncio
    async def test_event_inheritance_handling(self, bus):
        """Test that handlers registered for base event types receive subclass events."""
        # Create recorders for different levels of the hierarchy
        base_recorder = EventRecorder("base")
        child_recorder = EventRecorder("child")
        grandchild_recorder = EventRecorder("grandchild")
        
        # Register handlers for different classes in the hierarchy
        bus.register_event_handler("global", HierarchicalBaseEvent, base_recorder.handle_event)
        bus.register_event_handler("global", HierarchicalChildEvent, child_recorder.handle_event)
        bus.register_event_handler("global", HierarchicalGrandchildEvent, grandchild_recorder.handle_event)
        
        # Create and publish events of each type
        base_event = HierarchicalBaseEvent(category="test_base")
        child_event = HierarchicalChildEvent(category="test_child", subcategory="test_sub")
        grandchild_event = HierarchicalGrandchildEvent(
            category="test_grand", subcategory="test_grand_sub", detail="test_detail"
        )
        
        await bus.publish(base_event)
        await bus.publish(child_event)
        await bus.publish(grandchild_event)
        
        # Allow time for async processing
        await asyncio.sleep(0.1)
        
        # Verify handlers received appropriate events
        
        # Base recorder should receive all events (base, child, grandchild)
        assert len(base_recorder.events) == 3
        assert len(base_recorder.get_events_by_type(HierarchicalBaseEvent)) == 3
        
        # Child recorder should receive child and grandchild events
        assert len(child_recorder.events) == 2
        assert len(child_recorder.get_events_by_type(HierarchicalChildEvent)) == 2
        
        # Grandchild recorder should receive only grandchild events
        assert len(grandchild_recorder.events) == 1
        assert len(grandchild_recorder.get_events_by_type(HierarchicalGrandchildEvent)) == 1
    
    @pytest.mark.asyncio
    async def test_error_in_event_handler(self, bus):
        """Test that errors in event handlers are caught and don't prevent other handlers."""
        # Create recorders - one normal, one that errors
        normal_recorder = EventRecorder("normal")
        error_recorder = EventRecorder("error")
        
        # Register handlers
        bus.register_event_handler("global", SimpleEvent, normal_recorder.handle_event)
        bus.register_event_handler("global", SimpleEvent, error_recorder.handle_with_error)
        
        # Publish event
        event = SimpleEvent("error_test")
        await bus.publish(event)
        
        # Allow time for async processing
        await asyncio.sleep(0.1)
        
        # Verify both handlers processed the event
        assert len(normal_recorder.events) == 1
        assert normal_recorder.events[0].value == "error_test"
        
        assert len(error_recorder.events) == 1
        assert error_recorder.events[0].value == "error_test"
        
        # Publish another event to verify the bus is still operational
        event2 = SimpleEvent("after_error")
        await bus.publish(event2)
        
        # Allow time for async processing
        await asyncio.sleep(0.1)
        
        # Verify both handlers received the second event
        assert len(normal_recorder.events) == 2
        assert normal_recorder.events[1].value == "after_error"
        
        assert len(error_recorder.events) == 2
        assert error_recorder.events[1].value == "after_error"
    
    @pytest.mark.asyncio
    async def test_concurrent_event_handling(self, bus):
        """Test that events are processed concurrently by multiple handlers."""
        # Create recorders with different processing times
        fast_recorder = EventRecorder("fast")
        slow_recorder = EventRecorder("slow")
        
        # Register handlers with different delays
        bus.register_event_handler(
            "global", SimpleEvent, 
            lambda e: fast_recorder.handle_with_delay(e, delay=0.05)
        )
        bus.register_event_handler(
            "global", SimpleEvent, 
            lambda e: slow_recorder.handle_with_delay(e, delay=0.2)
        )
        
        # Publish event
        start_time = time.time()
        await bus.publish(SimpleEvent("concurrent_test"))
        
        # Wait for both handlers to complete
        await asyncio.sleep(0.25)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Verify both handlers received the event
        assert len(fast_recorder.events) == 1
        assert len(slow_recorder.events) == 1
        
        # The fast handler should have completed significantly before the slow one
        # Since handlers run concurrently, the fast one should finish in ~0.05s
        # Both should be done in ~0.2s, not 0.25s (sum of times if sequential)
        assert fast_recorder.last_processed is not None
        assert slow_recorder.last_processed is not None
        assert fast_recorder.last_processed < slow_recorder.last_processed
        
        # Total time should be closer to the slower handler time (with some buffer)
        # This verifies handlers run concurrently, not sequentially
        assert elapsed < 0.3  # 0.2s for slowest + some overhead, not 0.25s
    
    @pytest.mark.asyncio
    async def test_metadata_propagation(self, bus):
        """Test that metadata is properly propagated to events."""
        # Create recorder
        recorder = EventRecorder()
        
        # Register handler
        bus.register_event_handler("global", SimpleEvent, recorder.handle_event)
        
        # Create event with metadata
        event = SimpleEvent("metadata_test")
        event.metadata["test_key"] = "test_value"
        event.metadata["number"] = 42
        
        # Publish event
        await bus.publish(event)
        
        # Allow time for async processing
        await asyncio.sleep(0.1)
        
        # Verify metadata was preserved
        assert len(recorder.events) == 1
        received = recorder.events[0]
        assert received.metadata["test_key"] == "test_value"
        assert received.metadata["number"] == 42
    
    @pytest.mark.asyncio
    async def test_unregister_session_handlers(self, bus):
        """Test that handlers can be unregistered for a session."""
        # Create recorders
        session_recorder = EventRecorder("session")
        global_recorder = EventRecorder("global")
        
        # Register handlers
        session_id = "test_session_unregister"
        bus.register_event_handler(session_id, SimpleEvent, session_recorder.handle_event)
        bus.register_event_handler("global", SimpleEvent, global_recorder.handle_event)
        
        # Publish first event
        event1 = SimpleEvent("before_unregister")
        event1.session_id = session_id
        await bus.publish(event1)
        
        # Allow time for async processing
        await asyncio.sleep(0.1)
        
        # Verify both handlers received it
        assert len(session_recorder.events) == 1
        assert len(global_recorder.events) == 1
        
        # Unregister session handlers
        bus.unregister_session_handlers(session_id)
        
        # Publish second event
        event2 = SimpleEvent("after_unregister")
        event2.session_id = session_id
        await bus.publish(event2)
        
        # Allow time for async processing
        await asyncio.sleep(0.1)
        
        # Verify only global handler received the second event
        assert len(session_recorder.events) == 1  # Still just 1 from before
        assert len(global_recorder.events) == 2  # Now has 2
    
    @pytest.mark.asyncio
    async def test_complex_data_event(self, bus):
        """Test that events with complex nested data can be published and handled."""
        # Create recorder
        recorder = EventRecorder()
        
        # Register handler
        bus.register_event_handler("global", DataEvent, recorder.handle_event)
        
        # Create event with complex data
        complex_data = {
            "nested": {
                "array": [1, 2, 3],
                "dict": {"key": "value"}
            },
            "mixed": [{"a": 1}, {"b": 2}],
            "numbers": [1.0, 2.5, 3.333]
        }
        
        event = DataEvent(
            name="complex_test",
            data=complex_data,
            tags=["test", "complex", "nested"]
        )
        
        # Publish event
        await bus.publish(event)
        
        # Allow time for async processing
        await asyncio.sleep(0.1)
        
        # Verify event was received with all data intact
        assert len(recorder.events) == 1
        received = recorder.events[0]
        
        # Check event properties
        assert received.name == "complex_test"
        assert received.tags == ["test", "complex", "nested"]
        
        # Check nested data was preserved
        assert received.data["nested"]["array"] == [1, 2, 3]
        assert received.data["nested"]["dict"]["key"] == "value"
        assert received.data["mixed"][0]["a"] == 1
        assert received.data["mixed"][1]["b"] == 2
        assert received.data["numbers"] == [1.0, 2.5, 3.333]