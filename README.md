# LLMgine: A Pattern-Based Library for LLM Applications

[![Build status](https://img.shields.io/github/actions/workflow/status/nathan-luo/llmgine/main.yml?branch=main)](https://github.com/nathan-luo/llmgine/actions/workflows/main.yml?query=branch%3Amain)
[![License](https://img.shields.io/github/license/nathan-luo/llmgine)](https://img.shields.io/github/license/nathan-luo/llmgine)

LLMgine is a pattern-based approach to building LLM applications. It provides small, composable patterns rather than a monolithic framework, allowing developers to craft customized solutions with flexibility and control.

## Core Features

- **Dual Bus Architecture**: ObservabilityBus and MessageBus provide the backbone for all operations
- **Modular Components**: Clean separation of concerns with well-defined interfaces
- **Event-Driven Design**: Decoupled communication through commands and events
- **Comprehensive Observability**: Built-in logging, metrics, and tracing
- **Tool Integration**: Easy registration and execution of custom tools
- **Rich CLI Interface**: Beautiful terminal-based chat interface using Rich

## Installation

```bash
# Clone the repository
git clone https://github.com/nathan-luo/llmgine.git
cd llmgine

# Install dependencies
make install
```

## Quick Start

Run the chatbot application:

```bash
uv run python programs/chatbot.py
```

Try the bus architecture example:

```bash
uv run python examples/bus_example.py
```

## Core Architecture

LLMgine is built around two primary buses that serve as the foundation for all functionality:

### ObservabilityBus 

The ObservabilityBus handles all logging, metrics, and tracing:

```python
from llmgine.observability import ObservabilityBus
from llmgine.observability.events import LogLevel

# Create and start the observability bus
obs_bus = ObservabilityBus()
await obs_bus.start()

# Log messages with structured context
obs_bus.log(LogLevel.INFO, "Application started", {"version": "1.0.0"})

# Record metrics
obs_bus.metric("request_latency", 150, unit="ms", tags={"endpoint": "/chat"})

# Create traces for distributed tracing
span = obs_bus.start_trace("process_request", {"user_id": "user123"})
# ... do work ...
obs_bus.end_trace(span, status="success")
```

### MessageBus

The MessageBus handles commands and events, with automatic integration with the ObservabilityBus:

```python
from llmgine.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

# Define a command
@dataclass
class GreetCommand(Command):
    name: str

# Define an event
@dataclass
class UserGreetedEvent(Event):
    name: str
    greeting: str

# Create the message bus (automatically connects to ObservabilityBus)
message_bus = MessageBus()
await message_bus.start()

# Register handlers
message_bus.register_command_handler(
    GreetCommand, 
    lambda cmd: CommandResult(command_id=cmd.id, success=True, result=f"Hello, {cmd.name}!")
)

# Execute commands (automatically logs and emits events)
result = await message_bus.execute(GreetCommand(name="World"))
print(result.result)  # "Hello, World!"

# Publish events
await message_bus.publish(UserGreetedEvent(name="World", greeting="Hello"))
```

### Application Bootstrap

The ApplicationBootstrap brings everything together:

```python
from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig

# Create a custom application
class MyApp(ApplicationBootstrap):
    def _register_command_handlers(self):
        self.register_command_handler(GreetCommand, self.handle_greet)
    
    def handle_greet(self, cmd: GreetCommand) -> CommandResult:
        return CommandResult(command_id=cmd.id, success=True, result=f"Hello, {cmd.name}!")

# Initialize and run
async def main():
    app = MyApp()
    await app.bootstrap()
    
    result = await app.message_bus.execute(GreetCommand(name="World"))
    print(result.result)
    
    await app.shutdown()
```

## Tool Integration

The Tools module is fully integrated with the message bus architecture:

```python
from llmgine.llm.tools import ToolManager
from llmgine.bootstrap import ApplicationBootstrap

class MyApp(ApplicationBootstrap):
    def __init__(self):
        super().__init__()
        self.tool_manager = ToolManager(message_bus=self.message_bus)
        
        # Register a tool
        def calculator(expression: str) -> float:
            """Calculate the result of a mathematical expression."""
            return eval(expression)
            
        self.tool_manager.register_tool(calculator)
```

## Architecture Principles

LLMgine follows these design principles:

1. **Dual Bus Architecture**: ObservabilityBus and MessageBus provide the foundation
2. **Event-Driven Design**: Asynchronous communication with minimal coupling
3. **Domain-Driven Design**: Clear separation through commands and events
4. **Observability-First**: Complete visibility into all system operations
5. **Ports and Adapters**: Flexible interfaces for different implementations

## Development

Set up the development environment:

```bash
# Install dependencies
make install

# Run tests
make test

# Run linting checks
make check
```

## Documentation

For more detailed documentation, see the [docs](docs/) directory, including:

- [Event-Driven Architecture](docs/architecture/event_driven.md)
- [Module Documentation](docs/modules.md)

## License

This project is licensed under the MIT License - see the LICENSE file for details.