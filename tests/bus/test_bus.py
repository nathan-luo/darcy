import asyncio
import pytest
import pytest_asyncio
from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from dataclasses import dataclass, field
from icecream import ic
from llmgine.messages.events import Event

import os

# os.environ["PYTHONBREAKPOINT"] = "0"
# os.environ["PYTHONBREAKPOINT"] = "IPython.core.debugger.set_trace"


@dataclass
class TestCommand(Command):
    __test__ = False
    test_data: str = field(default_factory=str)


@dataclass
class TestEvent(Event):
    __test__ = False
    test_data: str = field(default_factory=str)
    counter: int = field(default=0)


@pytest_asyncio.fixture
async def bus():
    bus = MessageBus()
    await bus.start()
    yield bus
    await bus.reset()


class EventTracker:
    def __init__(self):
        self.events = []

    def track_event(self, event: Event):
        self.events.append(event)

    def event_function_1(self, event: TestEvent):
        self.events.append("function_1 executed")

    def event_function_2(self, event: TestEvent):
        self.events.append("function_2 executed")

    def event_function_3(self, event: TestEvent):
        self.events.append("function_3 executed")

    def event_function_failure(self, event: TestEvent):
        raise Exception("Test failure")


def command_function(input_data: str) -> str:
    return "(" + input_data + ")"


def command_function_failure(input_data: str):
    raise Exception("Test failure")


def command_handler_success(command: TestCommand):
    test_data = command_function(command.test_data)
    return CommandResult(success=True, result=test_data)


def command_handler_failure(command: TestCommand):
    test_data = command_function_failure(command.test_data)
    return CommandResult(success=True, result=test_data)


def event_handler_success(event: TestEvent):
    test_data = "[" + event.test_data + "] 1"
    ic(f"Event received: {test_data}")


def event_handler_success_2(event: TestEvent):
    test_data = "[" + event.test_data + "] 2"
    ic(f"Event received: {test_data}")


def event_handler_success_3(event: TestEvent):
    test_data = "[" + event.test_data + "] 3"
    ic(f"Event received: {test_data}")


def event_handler_failure(event: TestEvent):
    raise Exception("Test failure")


def test_bus_init_singleton(bus: MessageBus):
    bus1 = bus
    bus2 = MessageBus()
    assert bus1 is bus2


@pytest.mark.asyncio
async def test_bus_start_stop(bus: MessageBus):
    await bus.reset()
    assert bus._event_queue is None
    await bus.start()
    assert bus._event_queue is not None
    await bus.stop()
    assert bus._processing_task is None


@pytest.mark.asyncio
async def test_bus_register_command_handler_success(bus: MessageBus):
    # Register to ROOT
    bus.register_command_handler(TestCommand, command_handler_success)
    assert bus._command_handlers["ROOT"][TestCommand].function == command_handler_success

    # Register to session
    bus.register_command_handler(TestCommand, command_handler_success, "SESSION_1")
    assert (
        bus._command_handlers["SESSION_1"][TestCommand].function
        == command_handler_success
    )


@pytest.mark.asyncio
async def test_bus_register_command_handler_failure(bus: MessageBus):
    # Register to ROOT duplicate
    bus.register_command_handler(TestCommand, command_handler_failure)
    with pytest.raises(ValueError):
        bus.register_command_handler(TestCommand, command_handler_failure)

    # Register to session duplicate
    bus.register_command_handler(TestCommand, command_handler_failure, "SESSION_1")
    with pytest.raises(ValueError):
        bus.register_command_handler(TestCommand, command_handler_failure, "SESSION_1")

    # TODO: wrong types, handler checking


def test_bus_unregister_command_handler_success(bus: MessageBus):
    # Unregister from ROOT
    bus.register_command_handler(TestCommand, command_handler_success)
    bus.unregister_command_handler(TestCommand)
    assert bus._command_handlers["ROOT"] == {}

    # Unregister from session
    bus.register_command_handler(TestCommand, command_handler_success, "SESSION_1")
    bus.unregister_command_handler(TestCommand, "SESSION_1")
    assert bus._command_handlers["SESSION_1"] == {}


def test_bus_unregister_command_handler_failure(bus: MessageBus):
    # Unregister from ROOT non-existent
    with pytest.raises(ValueError):
        bus.unregister_command_handler(TestCommand)

    # Unregister from session non-existent
    ic(bus._command_handlers)
    with pytest.raises(ValueError) as e:
        bus.unregister_command_handler(TestCommand, "SESSION_1")
    assert str(e.value) == "No command handlers to unregister for session SESSION_1"


def test_bus_register_event_handlers(bus: MessageBus):
    # Register to ROOT
    bus.register_event_handler(TestEvent, event_handler_success)
    assert bus._event_handlers["ROOT"][TestEvent][0].function == event_handler_success

    # Register to session
    bus.register_event_handler(TestEvent, event_handler_success, "SESSION_1")
    assert (
        bus._event_handlers["SESSION_1"][TestEvent][0].function == event_handler_success
    )


def test_unregister_event_handlers_success(bus: MessageBus):
    # Unregister from ROOT
    bus.register_event_handler(TestEvent, event_handler_success)
    bus.unregister_event_handlers(TestEvent)
    assert bus._event_handlers["ROOT"] == {}

    # Unregister from session
    bus.register_event_handler(TestEvent, event_handler_success, "SESSION_1")
    bus.unregister_event_handlers(TestEvent, "SESSION_1")
    assert bus._event_handlers["SESSION_1"] == {}


def test_unregister_event_handlers_failure(bus: MessageBus):
    # Unregister from ROOT
    bus.register_event_handler(TestEvent, event_handler_success)
    bus.unregister_event_handlers(TestEvent)
    assert bus._event_handlers["ROOT"] == {}


@pytest.mark.asyncio
async def test_execute_command_success(bus: MessageBus):
    # ROOT success
    bus.register_command_handler(TestCommand, command_handler_success)
    command = TestCommand(test_data="test")
    result = await bus.execute(command)
    assert result.success
    assert result.result == "(test)"

    # Session
    bus.register_command_handler(TestCommand, command_handler_success, "SESSION_1")
    command = TestCommand(test_data="test", session_id="SESSION_1")
    result = await bus.execute(command)
    assert result.success
    assert result.result == "(test)"


@pytest.mark.asyncio
async def test_execute_command_failure(bus: MessageBus):
    # ROOT failure
    bus.register_command_handler(TestCommand, command_handler_failure)
    command = TestCommand(test_data="test")
    result = await bus.execute(command)
    assert not result.success
    assert result.error == "Exception: Test failure"

    # # Session failure
    bus.register_command_handler(TestCommand, command_handler_failure, "SESSION_1")
    command = TestCommand(test_data="test", session_id="SESSION_1")
    result = await bus.execute(command)
    assert not result.success
    assert result.error == "Exception: Test failure"


@pytest.mark.asyncio
async def test_publish_event_global_success(bus: MessageBus):
    tracker = EventTracker()
    bus.register_event_handler(TestEvent, tracker.event_function_1)
    bus.register_event_handler(TestEvent, tracker.event_function_2)
    bus.register_event_handler(TestEvent, tracker.event_function_3)
    event = TestEvent(test_data="test")
    await bus.publish(event)
    await asyncio.sleep(0.1)
    assert len(tracker.events) == 3
    assert tracker.events[0] == "function_1 executed"
    assert tracker.events[1] == "function_2 executed"
    assert tracker.events[2] == "function_3 executed"


@pytest.mark.asyncio
async def test_publish_event_session_success(bus: MessageBus):
    tracker = EventTracker()
    bus.register_event_handler(TestEvent, tracker.event_function_1, "SESSION_1")
    bus.register_event_handler(TestEvent, tracker.event_function_2, "SESSION_1")
    bus.register_event_handler(TestEvent, tracker.event_function_3, "SESSION_1")
    event = TestEvent(test_data="test", session_id="SESSION_1")
    await bus.publish(event)
    await asyncio.sleep(0.1)
    assert len(tracker.events) == 3
    assert tracker.events[0] == "function_1 executed"
    assert tracker.events[1] == "function_2 executed"
    assert tracker.events[2] == "function_3 executed"


@pytest.mark.asyncio
async def test_publish_event_session_global_inheritance_success(bus: MessageBus):
    tracker = EventTracker()
    bus.register_event_handler(TestEvent, tracker.event_function_1, "GLOBAL")
    bus.register_event_handler(TestEvent, tracker.event_function_2, "SESSION_1")
    bus.register_event_handler(TestEvent, tracker.event_function_3, "SESSION_1")
    event = TestEvent(test_data="test", session_id="SESSION_1")
    await bus.publish(event)
    await asyncio.sleep(0.1)
    assert len(tracker.events) == 3
    assert tracker.events[0] == "function_2 executed"
    assert tracker.events[1] == "function_3 executed"
    assert tracker.events[2] == "function_1 executed"


@pytest.mark.asyncio
async def test_publish_event_session_global_root_inheritance_success(bus: MessageBus):
    tracker = EventTracker()
    bus.register_event_handler(TestEvent, tracker.event_function_1, "ROOT")
    bus.register_event_handler(TestEvent, tracker.event_function_2, "GLOBAL")
    event = TestEvent(test_data="test", session_id="SESSION_1")
    await bus.publish(event)
    await asyncio.sleep(0.1)
    assert len(tracker.events) == 2
    assert tracker.events[0] == "function_1 executed"
    assert tracker.events[1] == "function_2 executed"


@pytest.mark.asyncio
async def test_publish_event_session_failure_surpressed_exception(bus: MessageBus):
    tracker = EventTracker()
    bus.register_event_handler(TestEvent, tracker.event_function_failure)
    event = TestEvent(test_data="test", session_id="SESSION_1")
    await bus.publish(event)
    await asyncio.sleep(0.1)
    assert str(bus.event_handler_errors[0]) == "Test failure"


@pytest.mark.asyncio
async def test_publish_event_session_failure_raises_exception(bus: MessageBus):
    tracker = EventTracker()
    bus.register_event_handler(TestEvent, tracker.event_function_failure)
    bus.unsupress_event_errors()
    event = TestEvent(test_data="test", session_id="SESSION_1")
    with pytest.raises(Exception) as e:
        await bus._handle_event(event)
    assert str(e.value) == "Test failure"
