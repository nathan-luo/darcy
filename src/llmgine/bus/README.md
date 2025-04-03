# Message Bus and Sessions

This package provides a message bus implementation for handling commands and events in the application.

## Message Bus

The MessageBus is a central communication mechanism in the application, providing a way for components to communicate without direct dependencies.

The bus follows these patterns:
- **Command Bus**: Commands represent operations to be performed and are handled by exactly one handler
- **Event Bus**: Events represent things that have happened and can be processed by multiple listeners
- **Observability**: All operations are traced for debugging and monitoring

## Sessions

Sessions allow grouping related operations together:
- Each session has a unique ID
- Commands and events can be associated with a session
- When a session ends, all its handlers are automatically unregistered

## Usage Example

Here's how to use sessions:

```python
from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
import asyncio

# Define an event
class MyEvent(Event):
    def __init__(self, message: str):
        super().__init__()
        self.message = message

# Define a command
class MyCommand(Command):
    def __init__(self, data: str):
        super().__init__()
        self.data = data

# Define event handler
def handle_my_event(event: MyEvent) -> None:
    print(f"Handling event: {event.message}")
    
# Define command handler  
def handle_my_command(command: MyCommand) -> CommandResult:
    print(f"Executing command: {command.data}")
    return CommandResult(success=True, original_command=command)

async def main():
    # Get the message bus
    bus = MessageBus()
    
    # Start a session using the context manager
    with bus.create_session() as session:
        # Register handlers with this session
        session.register_event_handler(MyEvent, handle_my_event)
        session.register_command_handler(MyCommand, handle_my_command)
        
        # Execute a command in this session
        command = MyCommand("Hello from command")
        result = await session.execute_with_session(command)
        
        # Publish an event in this session
        event = MyEvent("Hello from event")
        event.session_id = session.session_id  # Set session ID
        await bus.publish(event)
        
        # When the session exits:
        # 1. All handlers registered with this session are unregistered
        # 2. A SessionEndEvent is published
    
    # After session ends, the handlers are no longer active

if __name__ == "__main__":
    asyncio.run(main())
```

## Advantages of the Session Pattern

- **Cleanup**: Automatic cleanup of handlers when a session ends
- **Context**: Operations can be grouped and traced together
- **Isolation**: Different sessions can operate independently
- **Tracing**: All operations within a session can be traced together 