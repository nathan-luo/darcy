from llmgine.bus.bus import MessageBus
import pytest
import asyncio
import logging


def test_bus_singleton():
    bus1 = MessageBus()
    bus2 = MessageBus()
    assert bus1 is bus2


@pytest.mark.asyncio
async def test_bus_start_stop(caplog):
    caplog.set_level(logging.INFO)
    bus = MessageBus()

    # Test start and stop
    await bus.start()
    assert bus._processing_task is not None
    await bus.stop()
    assert bus._processing_task is None

    # Test start and stop again
    await bus.start()
    assert bus._processing_task is not None

    # Test start when already running
    await bus.start()
    assert caplog.records[-1].message == "MessageBus already running"
    await bus.stop()

    # Test stop when already stopped
    await bus.stop()
    assert caplog.records[-1].message == "MessageBus already stopped or never started"
