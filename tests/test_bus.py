from pytest import fixture
from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from dataclasses import dataclass, field

@dataclass
class TestCommand(Command):
    test_data: str = field(default_factory=str)

@fixture
def bus():
    yield MessageBus()
    del(bus)

def test_command_handler_success(command: TestCommand):
    test_data = command.test_data
    return CommandResult(success=True, data=command.test_data)
    
def test_bus_init_singleton(bus: MessageBus):
    bus1 = bus
    bus2 = MessageBus()
    assert bus1 is bus2

def test_bus_start_stop(bus: MessageBus):
    assert bus._event_queue is None
    bus.start()
    assert bus._event_queue is not None
    bus.stop()
    assert bus._event_queue is None

def test_bus_register_command_handler(bus: MessageBus):

    # Register to global
    bus.register_command_handler(TestCommand, test_command_handler_success)
    assert bus._command_handlers["GLOBAL"][TestCommand] == test_command_handler_success

    # Register to session
    bus.register_command_handler("SESSION_1", TestCommand, test_command_handler_success)
    assert bus._command_handlers["SESSION_1"][TestCommand] == test_command_handler_success

def test_
    


def test_bus_register_event_handler():
    bus = MessageBus()