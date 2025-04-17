"""Fake implementations of the message bus for use in testing."""

from typing import Dict, List, Type

from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event


class FakeMessageBus:
    """A fake message bus implementation for testing.

    This class implements the same interface as the real MessageBus
    but without the asynchronous behavior, making it easier to use in tests.

    This is implemented as a singleton, so only one instance can exist.

    Attributes:
        published_events: A list of events that have been published
        executed_commands: A list of commands that have been executed
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of FakeMessageBus.

        Returns:
            FakeMessageBus: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize the FakeMessageBus.

        If an instance already exists, raises an exception.
        """
        if FakeMessageBus._instance is not None:
            raise RuntimeError(
                "FakeMessageBus is a singleton - use get_instance() instead"
            )

        self.published_events: List[Event] = []
        self.executed_commands: List[Command] = []
        self._command_handlers: Dict[Type[Command], callable] = {}
        self._event_handlers: Dict[Type[Event], List[callable]] = {}
        FakeMessageBus._instance = self

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance.

        This is useful for testing when you want to start with a fresh instance.
        """
        cls._instance = None

    async def start(self):
        """Start the fake message bus (no-op)."""
        pass

    async def stop(self):
        """Stop the fake message bus (no-op)."""
        pass

    def register_command_handler(self, command_type, handler):
        """Register a command handler for testing."""
        self._command_handlers[command_type] = handler

    def register_async_command_handler(self, command_type, handler):
        """Register an async command handler for testing."""
        self._command_handlers[command_type] = handler

    def register_event_handler(self, event_type, handler):
        """Register an event handler for testing."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def register_async_event_handler(self, event_type, handler):
        """Register an async event handler for testing."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def execute(self, command):
        """Execute a command in the fake bus.

        Records the command and returns a successful result.
        If a handler is registered, it will be called.
        """
        self.executed_commands.append(command)

        if type(command) in self._command_handlers:
            handler = self._command_handlers[type(command)]
            result = handler(command)
            # Handle both sync and async handlers
            if hasattr(result, "__await__"):
                return await result
            return result

        # Default success result
        return CommandResult(success=True)

    async def publish(self, event):
        """Publish an event to the fake bus.

        Records the event and calls any registered handlers.
        """
        self.published_events.append(event)

        event_type = type(event)
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                result = handler(event)
                # Handle both sync and async handlers
                if hasattr(result, "__await__"):
                    await result
