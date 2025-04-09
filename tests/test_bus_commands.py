"""Tests focusing on command handling and execution in the message bus."""

import asyncio
from dataclasses import dataclass
import time
from typing import Dict, List, Optional, Any

import pytest
import pytest_asyncio

from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event


# Test commands for the test suite
@dataclass
class SimpleCommand(Command):
    """A simple command for testing."""
    value: str


@dataclass
class ParameterizedCommand(Command):
    """A command with multiple parameters for testing."""
    id: str
    count: int
    data: Dict[str, Any]


@dataclass
class ErrorCommand(Command):
    """A command intended to trigger errors."""
    error_type: str
    should_fail: bool = True


@dataclass
class SlowCommand(Command):
    """A command that takes some time to process."""
    delay_seconds: float
    value: str = "slow"


# Event that might be published by command handlers
class CommandProcessedEvent(Event):
    """Event published when a command completes processing."""
    
    def __init__(self, command_type: str, value: Any):
        super().__init__()
        self.command_type = command_type
        self.value = value


class TestBusCommands:
    """Tests focusing on command handling in the message bus."""
    
    @pytest_asyncio.fixture
    async def bus(self):
        """Create and start a MessageBus for testing."""
        bus = MessageBus()
        await bus.start()
        yield bus
        await bus.stop()
    
    @pytest.mark.asyncio
    async def test_register_command_handler(self, bus):
        """Test that command handlers can be registered for specific command types."""
        # Define a simple handler
        handled_commands = []
        
        def handle_simple_command(cmd: SimpleCommand) -> CommandResult:
            handled_commands.append(cmd)
            return CommandResult(success=True, result=f"Processed: {cmd.value}")
        
        # Register the handler
        bus.register_command_handler("global", SimpleCommand, handle_simple_command)
        
        # Execute the command
        result = await bus.execute(SimpleCommand("test_register"))
        
        # Verify handler was called
        assert len(handled_commands) == 1
        assert handled_commands[0].value == "test_register"
        
        # Verify result
        assert result.success is True
        assert result.result == "Processed: test_register"
    
    @pytest.mark.asyncio
    async def test_session_specific_command_handlers(self, bus):
        """Test that command handlers can be registered for specific sessions."""
        # Track commands handled in each session
        session1_commands = []
        session2_commands = []
        global_commands = []
        
        # Define handlers for each session
        def session1_handler(cmd: SimpleCommand) -> CommandResult:
            session1_commands.append(cmd)
            return CommandResult(success=True, result="session1")
            
        def session2_handler(cmd: SimpleCommand) -> CommandResult:
            session2_commands.append(cmd)
            return CommandResult(success=True, result="session2")
            
        def global_handler(cmd: SimpleCommand) -> CommandResult:
            global_commands.append(cmd)
            return CommandResult(success=True, result="global")
        
        # Register the handlers
        bus.register_command_handler("session1", SimpleCommand, session1_handler)
        bus.register_command_handler("session2", SimpleCommand, session2_handler)
        bus.register_command_handler("global", SimpleCommand, global_handler)
        
        # Create commands with different session IDs
        cmd1 = SimpleCommand("command1")
        cmd1.session_id = "session1"
        
        cmd2 = SimpleCommand("command2")
        cmd2.session_id = "session2"
        
        cmd_global = SimpleCommand("command_global")
        # No session ID specified, should use global handler
        
        # Execute commands
        result1 = await bus.execute(cmd1)
        result2 = await bus.execute(cmd2)
        result_global = await bus.execute(cmd_global)
        
        # Verify correct handlers were called
        assert len(session1_commands) == 1
        assert session1_commands[0].value == "command1"
        assert result1.result == "session1"
        
        assert len(session2_commands) == 1
        assert session2_commands[0].value == "command2"
        assert result2.result == "session2"
        
        assert len(global_commands) == 1
        assert global_commands[0].value == "command_global"
        assert result_global.result == "global"
    
    @pytest.mark.asyncio
    async def test_command_fallback_to_global(self, bus):
        """Test that commands fall back to global handlers if no session-specific handler."""
        # Track commands handled
        handled_commands = []
        
        # Define global handler
        def global_handler(cmd: SimpleCommand) -> CommandResult:
            handled_commands.append(cmd)
            return CommandResult(success=True, result="global_fallback")
        
        # Register only global handler
        bus.register_command_handler("global", SimpleCommand, global_handler)
        
        # Create command with session ID that has no specific handler
        cmd = SimpleCommand("fallback_test")
        cmd.session_id = "nonexistent_session"
        
        # Execute command
        result = await bus.execute(cmd)
        
        # Verify global handler was called
        assert len(handled_commands) == 1
        assert handled_commands[0].value == "fallback_test"
        assert result.result == "global_fallback"
    
    @pytest.mark.asyncio
    async def test_sync_async_command_handlers(self, bus):
        """Test both synchronous and asynchronous command handlers."""
        # Results to track handler execution
        sync_called = False
        async_called = False
        
        # Define handlers
        def sync_handler(cmd: SimpleCommand) -> CommandResult:
            nonlocal sync_called
            sync_called = True
            return CommandResult(success=True, result="sync_result")
        
        async def async_handler(cmd: ParameterizedCommand) -> CommandResult:
            nonlocal async_called
            async_called = True
            # Small delay to ensure it's running asynchronously
            await asyncio.sleep(0.01)
            return CommandResult(success=True, result=f"async_result_{cmd.id}")
        
        # Register handlers
        bus.register_command_handler("global", SimpleCommand, sync_handler)
        bus.register_command_handler("global", ParameterizedCommand, async_handler)
        
        # Execute commands
        sync_result = await bus.execute(SimpleCommand("sync_test"))
        async_result = await bus.execute(ParameterizedCommand("123", 42, {"key": "value"}))
        
        # Verify results
        assert sync_called is True
        assert async_called is True
        assert sync_result.result == "sync_result"
        assert async_result.result == "async_result_123"
    
    @pytest.mark.asyncio
    async def test_command_error_handling(self, bus):
        """Test that errors in command handlers are properly handled."""
        # Define an error-throwing handler
        def error_handler(cmd: ErrorCommand) -> CommandResult:
            if cmd.should_fail:
                if cmd.error_type == "exception":
                    raise ValueError("Test exception in handler")
                else:
                    return CommandResult(success=False, error="Manual error")
            return CommandResult(success=True, result="No error")
        
        # Register the handler
        bus.register_command_handler("global", ErrorCommand, error_handler)
        
        # Test exception handling
        exception_result = await bus.execute(ErrorCommand("exception"))
        assert exception_result.success is False
        assert "ValueError: Test exception in handler" in exception_result.error
        
        # Test manual error
        error_result = await bus.execute(ErrorCommand("manual"))
        assert error_result.success is False
        assert error_result.error == "Manual error"
        
        # Test no error
        success_result = await bus.execute(ErrorCommand("none", should_fail=False))
        assert success_result.success is True
        assert success_result.result == "No error"
    
    @pytest.mark.asyncio
    async def test_command_event_publishing(self, bus):
        """Test that command handlers can publish events."""
        # Track events published
        published_events = []
        
        # Create event handler to track published events
        async def event_handler(event: CommandProcessedEvent):
            published_events.append(event)
        
        # Register event handler
        bus.register_event_handler("global", CommandProcessedEvent, event_handler)
        
        # Create command handler that publishes an event
        async def command_handler(cmd: SimpleCommand) -> CommandResult:
            # Publish an event as part of handling the command
            await bus.publish(CommandProcessedEvent("SimpleCommand", cmd.value))
            return CommandResult(success=True, result="Published event")
        
        # Register command handler
        bus.register_command_handler("global", SimpleCommand, command_handler)
        
        # Execute command
        result = await bus.execute(SimpleCommand("event_publisher"))
        
        # Give time for async event processing
        await asyncio.sleep(0.1)
        
        # Verify event was published
        assert len(published_events) == 1
        assert published_events[0].command_type == "SimpleCommand"
        assert published_events[0].value == "event_publisher"
    
    @pytest.mark.asyncio
    async def test_unregister_session_handlers(self, bus):
        """Test that handlers can be unregistered for a specific session."""
        # Track handler calls
        session_calls = []
        
        # Define session handler
        def session_handler(cmd: SimpleCommand) -> CommandResult:
            session_calls.append(cmd.value)
            return CommandResult(success=True, result="session_result")
        
        # Register handler for a specific session
        session_id = "test_session"
        bus.register_command_handler(session_id, SimpleCommand, session_handler)
        
        # First command should work
        cmd1 = SimpleCommand("before_unregister")
        cmd1.session_id = session_id
        result1 = await bus.execute(cmd1)
        
        assert result1.success is True
        assert session_calls == ["before_unregister"]
        
        # Unregister all handlers for the session
        bus.unregister_session_handlers(session_id)
        
        # After unregistering, the command should fail because no handler
        cmd2 = SimpleCommand("after_unregister")
        cmd2.session_id = session_id
        
        with pytest.raises(ValueError):
            await bus.execute(cmd2)
        
        # Verify original handler wasn't called again
        assert session_calls == ["before_unregister"]
    
    @pytest.mark.asyncio
    async def test_concurrent_command_execution(self, bus):
        """Test that multiple commands can be executed concurrently."""
        # Define a slow command handler 
        async def slow_handler(cmd: SlowCommand) -> CommandResult:
            await asyncio.sleep(cmd.delay_seconds)
            return CommandResult(success=True, result=f"Completed {cmd.value}")
        
        # Register handler
        bus.register_command_handler("global", SlowCommand, slow_handler)
        
        # Execute commands concurrently
        start_time = time.time()
        
        cmd1 = SlowCommand(0.2, "cmd1")
        cmd2 = SlowCommand(0.2, "cmd2")
        
        # Execute both commands concurrently
        results = await asyncio.gather(
            bus.execute(cmd1),
            bus.execute(cmd2)
        )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Verify correct results
        assert results[0].success is True
        assert results[0].result == "Completed cmd1"
        assert results[1].success is True
        assert results[1].result == "Completed cmd2"
        
        # If truly concurrent, should take ~0.2 seconds, not ~0.4
        # Allow some buffer for test execution overhead
        assert elapsed < 0.4