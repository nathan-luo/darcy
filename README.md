# LLMgine: Tool Chat Engine

A modular engine for building LLM-powered applications with tool-calling capabilities.

## Overview

This repository contains a customizable engine for working with large language models (LLMs) and function/tool calling. The core components include:

- **Message Bus**: Central event and command system for communication between components
- **Tool Manager**: Handles registration and execution of tools that LLMs can call
- **Context Manager**: Manages conversation history and memory
- **LLM Providers**: Interface with different LLM providers (currently OpenAI)
- **Session Management**: Persistent conversations across application restarts

## Function Chat Demo

The `function_chat.py` program demonstrates a simple chat application with function calling capabilities. It registers several mock tools:

- **Weather**: Get the weather in a specific location
- **Email**: Send an email (mock implementation)
- **Calculator**: Evaluate mathematical expressions

### Prerequisites

1. Python 3.8+
2. OpenAI API key

### Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set your OpenAI API key as an environment variable:
   ```
   export OPENAI_API_KEY=your-api-key-here
   ```

### Running the Demo

Use the provided shell script for convenience:

```bash
./run_function_chat.sh
```

Or run directly with Python:

```bash
python programs/function_chat.py
```

### Session Management

The application includes persistent session management. Sessions are stored in JSON files in the `sessions` directory, allowing conversations to be resumed across application restarts.

**Command Line Options:**

- `--list-sessions`: List all available sessions
- `--session <id>`: Resume a specific session
- `--session-name <name>`: Create a new session with a specific name

**Session Commands:**

During a chat session, you can use:

- `/sessions`: List all available sessions
- `/system <prompt>`: Update the system prompt for the current session
- `/clear`: Clear the conversation history (but keep the session)

**Example Usage:**

```bash
# List all available sessions
./run_function_chat.sh --list-sessions

# Resume a specific session
./run_function_chat.sh --session 550e8400-e29b-41d4-a716-446655440000

# Create a new session with a custom name
./run_function_chat.sh --session-name "Weather Assistant"

# Use GPT-4 model for this session
./run_function_chat.sh --model gpt-4
```

### Other Options

- `--model`: Specify the OpenAI model to use (default: gpt-4o-mini)
- `--api-key`: Provide your OpenAI API key directly
- `--system-prompt`: Set a custom system prompt
- `--log-level`: Set logging level (debug, info, warning, error, critical)
- `--log-dir`: Specify directory for log files
- `--no-console`: Disable console output for events

### Sample Interactions

Try asking questions like:
- "What's the weather like in San Francisco?"
- "Can you calculate 24*7 for me?"
- "Send an email to test@example.com with subject 'Hello' and body 'Testing the function calling capability'"

## Architecture

The application is built around the `ToolChatEngine` which orchestrates:

1. Processing user messages via a command bus
2. Managing context/conversation history
3. Interacting with the LLM provider (OpenAI)
4. Registering and executing tools when called by the LLM

### Bootstrap System

The application uses the `ApplicationBootstrap` system to initialize and configure application components:

1. Sets up logging and observability
2. Initializes the MessageBus
3. Configures and registers event handlers
4. Manages application lifecycle (startup/shutdown)

## Extending

To add your own tools:
1. Create an asynchronous function with proper docstring (description and Args section)
2. Register it with the engine using `await engine.register_tool(your_function)`

Example:
```python
async def my_custom_tool(param1: str, param2: int) -> Dict[str, Any]:
    """Description of what the tool does.

    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2

    Returns:
        Dictionary with results
    """
    # Implementation
    return {"result": "some value"}
```

## Key Features

- **Event-Driven Architecture**: Decouple components using a central `MessageBus`.
- **Command/Event Pattern**: Clearly separate actions (Commands) from notifications (Events).
- **Integrated Observability**: Automatic JSONL logging of all bus events (commands, results, LLM interactions, metrics, traces), with optional console output for metrics and traces, built into the `MessageBus`.
- **Context Management**: Flexible context handling (currently in-memory).
- **LLM Provider Abstraction**: Interface with different LLM providers (e.g., OpenAI).
- **Tool Management**: Define and manage tools/functions for LLMs to use.
- **Async First**: Built on `asyncio` for high performance.

## Core Concepts

### MessageBus

The `MessageBus` is the central nervous system of an LLMgine application. It handles:

1.  **Command Execution**: Receiving `Command` objects, finding the registered handler, executing it, and publishing resulting events (`CommandResultEvent`, `CommandErrorEvent`).
2.  **Event Publishing**: Broadcasting `Event` objects to any registered handlers.
3.  **Integrated Observability**: Automatically logging *all* events passing through it (application events and internal observability events like `MetricEvent`, `TraceEvent`) to a JSONL file. It also handles command execution tracing and optional console logging for metrics/traces based on its configuration.

```python
from llmgine.bus import MessageBus
from llmgine.messages.commands import YourCommand
from llmgine.messages.events import YourEvent

# Initialize the bus with observability configuration
# Log file will be created in 'logs/app_events.jsonl'
# Console output for metrics and traces is enabled by default
message_bus = MessageBus(
    log_dir="logs",
    log_filename="app_events.jsonl",
    enable_console_metrics=True,
    enable_console_traces=True
)

# Start the bus's background processing
await message_bus.start()

# Register handlers (example)
# message_bus.register_command_handler(YourCommand, handle_your_command)
# message_bus.register_event_handler(YourEvent, handle_your_event)

# Execute commands
# result = await message_bus.execute(YourCommand(...))

# Publish events (also happens automatically for command results)
# await message_bus.publish(YourEvent(...))

# --- Observability Events ---
# You can also publish standard observability events directly
from llmgine.observability import Metric, MetricEvent, TraceEvent, SpanContext

# Publish a metric
await message_bus.publish(MetricEvent(metrics=[Metric(name="files_processed", value=10)]))

# Publish a custom trace span (though command traces are automatic)
# trace_id = "custom_trace_1"
# span_id = "custom_span_1"
# span_context = SpanContext(trace_id=trace_id, span_id=span_id)
# await message_bus.publish(TraceEvent(name="Custom Operation Start", span_context=span_context, start_time=datetime.now().isoformat()))
# # ... perform operation ...
# await message_bus.publish(TraceEvent(name="Custom Operation End", span_context=span_context, end_time=datetime.now().isoformat(), status="OK"))

# Stop the bus
# await message_bus.stop()
```

### Commands

Commands represent requests to perform an action. They should be named imperatively (e.g., `ProcessDocumentCommand`). Each command type should have exactly one handler registered with the `MessageBus`.

### Events

Events represent something that has happened in the system. They should be named in the past tense (e.g., `DocumentProcessedEvent`). Multiple handlers can be registered for a single event type. The `MessageBus` automatically logs all events.

### LLMEngine

The `LLMEngine` orchestrates interactions with the LLM, managing context, tools, and communication with the LLM provider. It listens for commands like `PromptCommand` and publishes events like `LLMResponseEvent` and `ToolCallEvent`.

### Observability

Observability (logging, metrics, tracing) is integrated directly into the `MessageBus`.

-   **Logging**: All events published via `message_bus.publish()` are automatically serialized to a JSONL file configured during `MessageBus` initialization. Standard Python logging is used for internal bus/component messages.
-   **Metrics**: Publish `MetricEvent` objects to the `MessageBus`. Console output is configurable.
-   **Tracing**: Command execution spans (`TraceEvent`) are automatically generated and published by the `MessageBus`. You can publish custom `TraceEvent`s as well. Console output is configurable.

## Getting Started

*(Add setup and basic usage instructions here)*

## Project Structure Ideas

```
my_llm_app/
├── main.py                 # Application entry point
├── config.py               # Configuration loading
├── bootstrap.py            # ApplicationBootstrap implementation
├── commands/
│   ├── __init__.py
│   └── process_data.py     # Example: ProcessDataCommand
├── events/
│   ├── __init__.py
│   └── data_processed.py   # Example: DataProcessedEvent
├── handlers/
│   ├── __init__.py
│   └── process_data_handler.py # Example: Handler for ProcessDataCommand
├── services/               # Business logic components
│   └── data_processor.py
├── logs/                   # Default log directory
└── requirements.txt
```

## Contributing

*(Add contribution guidelines here)*

## License

*(Add license information here)*


## Run with

uv run python -m programs.discord.bot
