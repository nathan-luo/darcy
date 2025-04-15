import asyncio
import logging

import pytest

from llmgine.bus.bus import MessageBus
from llmgine.bus.session import BusSession
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.observability.handlers.base import ObservabilityEventHandler

class FakeCommand(Command):
    pass

class FakeEvent(Event):
    pass

class FakeAsyncCommand(Command):
    pass

class FakeHandler:
    def __init__(self):
        self.called = False
        self.last_arg = None
    def __call__(self, arg):
        self.called = True
        self.last_arg = arg
        return CommandResult(success=True, original_command=arg)

class FakeAsyncHandler:
    def __init__(self):
        self.called = False
        self.last_arg = None
    async def __call__(self, arg):
        self.called = True
        self.last_arg = arg
        return CommandResult(success=True, original_command=arg)

class FakeEventHandler:
    def __init__(self):
        self.called = False
        self.last_arg = None
    def __call__(self, arg):
        self.called = True
        self.last_arg = arg

class FakeAsyncEventHandler:
    def __init__(self):
        self.called = False
        self.last_arg = None
    async def __call__(self, arg):
        self.called = True
        self.last_arg = arg

class DummyObservabilityHandler(ObservabilityEventHandler):
    def __init__(self):
        super().__init__()
        self.seen = []
    async def handle(self, event):
        self.seen.append(event)

@pytest.mark.asyncio
async def test_command_handler_registration_and_execution():
    bus = MessageBus()
    await bus.start()
    handler = FakeHandler()
    bus.register_command_handler("global", FakeCommand, handler)
    cmd = FakeCommand()
    result = await bus.execute(cmd)
    assert handler.called
    assert result.success
    bus.unregister_command_handler(FakeCommand, "global")
    await bus.stop()

@pytest.mark.asyncio
async def test_async_command_handler_registration_and_execution():
    bus = MessageBus()
    await bus.start()
    handler = FakeAsyncHandler()
    bus.register_command_handler("global", FakeAsyncCommand, handler)
    cmd = FakeAsyncCommand()
    result = await bus.execute(cmd)
    assert handler.called
    assert result.success
    bus.unregister_command_handler(FakeAsyncCommand, "global")
    await bus.stop()

@pytest.mark.asyncio
async def test_event_handler_registration_and_publish():
    bus = MessageBus()
    await bus.start()
    handler = FakeEventHandler()
    bus.register_event_handler("global", FakeEvent, handler)
    evt = FakeEvent()
    await bus.publish(evt)
    # Let the event loop process the event
    await asyncio.sleep(0.05)
    assert handler.called
    bus.unregister_event_handler(FakeEvent, "global")
    await bus.stop()

@pytest.mark.asyncio
async def test_async_event_handler_registration_and_publish():
    bus = MessageBus()
    await bus.start()
    handler = FakeAsyncEventHandler()
    bus.register_event_handler("global", FakeEvent, handler)
    evt = FakeEvent()
    await bus.publish(evt)
    await asyncio.sleep(0.05)
    assert handler.called
    bus.unregister_event_handler(FakeEvent, "global")
    await bus.stop()

@pytest.mark.asyncio
async def test_unregister_session_handlers():
    bus = MessageBus()
    await bus.start()
    handler = FakeHandler()
    bus.register_command_handler("mysession", FakeCommand, handler)
    bus.unregister_session_handlers("mysession")
    with pytest.raises(ValueError):
        await bus.execute(FakeCommand(session_id="mysession"))
    await bus.stop()

@pytest.mark.asyncio
async def test_unregister_command_and_event_handler():
    bus = MessageBus()
    await bus.start()
    handler = FakeHandler()
    bus.register_command_handler("global", FakeCommand, handler)
    bus.unregister_command_handler(FakeCommand, "global")
    with pytest.raises(ValueError):
        await bus.execute(FakeCommand())
    evt_handler = FakeEventHandler()
    bus.register_event_handler("global", FakeEvent, evt_handler)
    bus.unregister_event_handler(FakeEvent, "global")
    await bus.publish(FakeEvent())  # Should not call handler
    await asyncio.sleep(0.05)
    assert not evt_handler.called
    await bus.stop()

@pytest.mark.asyncio
async def test_execute_no_handler():
    bus = MessageBus()
    await bus.start()
    with pytest.raises(ValueError):
        await bus.execute(FakeCommand())
    await bus.stop()

@pytest.mark.asyncio
async def test_publish_event_session_metadata():
    bus = MessageBus()
    await bus.start()
    handler = FakeEventHandler()
    bus.register_event_handler("global", FakeEvent, handler)
    evt = FakeEvent()
    evt.metadata = {}
    await bus.publish(evt)
    await asyncio.sleep(0.05)
    assert handler.called
    assert "session_id" in evt.metadata
    bus.unregister_event_handler(FakeEvent, "global")
    await bus.stop()

@pytest.mark.asyncio
async def test_create_session():
    bus = MessageBus()
    session = bus.create_session()
    assert isinstance(session, BusSession)
    assert session.session_id is not None

@pytest.mark.asyncio
async def test_register_observability_handler():
    bus = MessageBus()
    await bus.start()
    obs_handler = DummyObservabilityHandler()
    bus.register_observability_handler(obs_handler)
    evt = FakeEvent()
    await bus.publish(evt)
    await asyncio.sleep(0.05)
    assert obs_handler.seen
    await bus.stop()

# Singleton and start/stop tests remain as is

def test_bus_singleton():
    bus1 = MessageBus()
    bus2 = MessageBus()
    assert bus1 is bus2

@pytest.mark.asyncio
async def test_bus_start_stop(caplog):
    caplog.set_level(logging.INFO)
    bus = MessageBus()
    await bus.start()
    assert bus._processing_task is not None
    await bus.stop()
    assert bus._processing_task is None
    await bus.start()
    assert bus._processing_task is not None
    await bus.start()
    assert caplog.records[-1].message == "MessageBus already running"
    await bus.stop()
    await bus.stop()
    assert caplog.records[-1].message == "MessageBus already stopped or never started"
