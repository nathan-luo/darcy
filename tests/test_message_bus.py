"""Tests for the message bus system."""

import asyncio
from dataclasses import dataclass

import pytest
import pytest_asyncio

from llmgine.bus import FakeMessageBus, MessageBus
from llmgine.messages import Command, CommandResult, Event


# Sample command and event classes for testing
@dataclass
class TestCommand(Command):
    """Test command for unit tests."""
    value: str


@dataclass
class AnotherTestCommand(Command):
    """Another test command for unit tests."""
    value: int


class TestEvent(Event):
    """Test event for unit tests."""

    def __init__(self, value: str):
        super().__init__()
        self.value = value


class AnotherTestEvent(Event):
    """Another test event for unit tests."""

    def __init__(self, value: int):
        super().__init__()
        self.value = value


# Tests for the real MessageBus
class TestMessageBus:
    """Tests for the MessageBus implementation."""

    @pytest_asyncio.fixture
    async def bus(self):
        """Create and start a MessageBus for testing."""
        bus = MessageBus()
        await bus.start()
        yield bus
        await bus.stop()

    @pytest.mark.asyncio
    async def test_command_execution(self, bus):
        """Test that commands can be executed with handlers."""
        # Setup
        received = []

        async def handle_command(cmd: TestCommand) -> CommandResult:
            received.append(cmd.value)
            return CommandResult(success=True, result=f"processed-{cmd.value}")

        bus.register_async_command_handler(TestCommand, handle_command)

        # Execute
        result = await bus.execute(TestCommand("test"))

        # Assert
        assert result.success is True
        assert result.result == "processed-test"
        assert received == ["test"]

    @pytest.mark.asyncio
    async def test_event_publishing(self, bus):
        """Test that events can be published and handled."""
        # Setup
        received = []

        async def handle_event(event: TestEvent):
            received.append(event.value)

        bus.register_async_event_handler(TestEvent, handle_event)

        # Execute
        await bus.publish(TestEvent("test_event"))

        # Allow event to be processed asynchronously
        await asyncio.sleep(0.1)

        # Assert
        assert received == ["test_event"]

    @pytest.mark.asyncio
    async def test_multiple_event_handlers(self, bus):
        """Test that multiple handlers for the same event type all get called."""
        # Setup
        received1 = []
        received2 = []

        async def handle_event1(event: TestEvent):
            received1.append(event.value)

        async def handle_event2(event: TestEvent):
            received2.append(event.value)

        bus.register_async_event_handler(TestEvent, handle_event1)
        bus.register_async_event_handler(TestEvent, handle_event2)

        # Execute
        await bus.publish(TestEvent("test_multiple"))

        # Allow events to be processed asynchronously
        await asyncio.sleep(0.1)

        # Assert
        assert received1 == ["test_multiple"]
        assert received2 == ["test_multiple"]

    @pytest.mark.asyncio
    async def test_synchronous_handlers(self, bus):
        """Test that synchronous handlers work correctly."""
        # Setup
        command_received = []
        event_received = []

        def handle_command(cmd: TestCommand) -> CommandResult:
            command_received.append(cmd.value)
            return CommandResult(success=True, result=f"sync-{cmd.value}")

        def handle_event(event: TestEvent):
            event_received.append(event.value)

        bus.register_command_handler(TestCommand, handle_command)
        bus.register_event_handler(TestEvent, handle_event)

        # Execute
        cmd_result = await bus.execute(TestCommand("sync_test"))
        await bus.publish(TestEvent("sync_event"))

        # Allow events to be processed asynchronously
        await asyncio.sleep(0.1)

        # Assert
        assert cmd_result.success is True
        assert cmd_result.result == "sync-sync_test"
        assert command_received == ["sync_test"]
        assert event_received == ["sync_event"]

    @pytest.mark.asyncio
    async def test_no_handler_for_command(self, bus):
        """Test that executing a command with no handler raises an error."""
        with pytest.raises(ValueError):
            await bus.execute(AnotherTestCommand(42))

    @pytest.mark.asyncio
    async def test_error_in_command_handler(self, bus):
        """Test that errors in command handlers are handled properly."""
        async def failing_handler(cmd: TestCommand) -> CommandResult:
            raise RuntimeError("Test error")

        bus.register_async_command_handler(TestCommand, failing_handler)

        result = await bus.execute(TestCommand("will_fail"))

        assert result.success is False
        assert "Test error" in result.error


# Tests for the FakeMessageBus
class TestFakeMessageBus:
    """Tests for the FakeMessageBus implementation used in testing."""

    @pytest.fixture
    def fake_bus(self):
        """Create a FakeMessageBus for testing."""
        return FakeMessageBus()

    @pytest.mark.asyncio
    async def test_fake_command_execution(self, fake_bus):
        """Test that the fake bus records executed commands."""
        # Execute
        result = await fake_bus.execute(TestCommand("fake_test"))

        # Assert
        assert len(fake_bus.executed_commands) == 1
        assert isinstance(fake_bus.executed_commands[0], TestCommand)
        assert fake_bus.executed_commands[0].value == "fake_test"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_fake_event_publishing(self, fake_bus):
        """Test that the fake bus records published events."""
        # Execute
        event = TestEvent("fake_event")
        await fake_bus.publish(event)

        # Assert
        assert len(fake_bus.published_events) == 1
        assert fake_bus.published_events[0] is event

    @pytest.mark.asyncio
    async def test_fake_command_handler(self, fake_bus):
        """Test that registered command handlers are called in the fake bus."""
        # Setup
        received = []

        def handle_command(cmd: TestCommand) -> CommandResult:
            received.append(cmd.value)
            return CommandResult(success=True, result=f"fake-{cmd.value}")

        fake_bus.register_command_handler(TestCommand, handle_command)

        # Execute
        result = await fake_bus.execute(TestCommand("fake_handler_test"))

        # Assert
        assert received == ["fake_handler_test"]
        assert result.success is True
        assert result.result == "fake-fake_handler_test"

    @pytest.mark.asyncio
    async def test_fake_event_handler(self, fake_bus):
        """Test that registered event handlers are called in the fake bus."""
        # Setup
        received = []

        def handle_event(event: TestEvent):
            received.append(event.value)

        fake_bus.register_event_handler(TestEvent, handle_event)

        # Execute
        await fake_bus.publish(TestEvent("fake_event_handler"))

        # Assert
        assert received == ["fake_event_handler"]
