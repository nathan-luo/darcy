# LLMgine Modules

This document provides an overview of the key modules in the LLMgine framework and how they can be used to build LLM-powered applications.

## Message Bus

The Message Bus is the central communication mechanism in LLMgine, providing a way for components to communicate without direct dependencies. It follows the Command and Event patterns from Domain-Driven Design.

### Components

- **Commands**: Represent requests to do something (imperative)
- **Events**: Represent facts that have happened (past tense)
- **Command Bus**: Routes commands to their appropriate handlers
- **Event Bus**: Distributes events to interested subscribers

### Example Usage

```python
import asyncio
from dataclasses import dataclass

from llmgine.bus import MessageBus
from llmgine.messages import Command, CommandResult, Event


# Define a command
@dataclass
class GenerateResponse(Command):
    prompt: str
    model_name: str = "gpt-4"


# Define an event
class ResponseGenerated(Event):
    def __init__(self, prompt: str, response: str, model_name: str):
        super().__init__()
        self.prompt = prompt
        self.response = response
        self.model_name = model_name


# Create an async command handler
async def handle_generate_response(cmd: GenerateResponse) -> CommandResult:
    # In a real app, this would call an LLM API
    response = f"Mock response to: {cmd.prompt}"
    
    # Return a successful result with the response
    return CommandResult(success=True, result=response)


# Create an event handler
async def log_generated_response(event: ResponseGenerated):
    print(f"Model {event.model_name} generated response for prompt: {event.prompt}")
    print(f"Response: {event.response}")


async def main():
    # Create and start the message bus
    bus = MessageBus()
    await bus.start()
    
    try:
        # Register handlers
        bus.register_async_command_handler(GenerateResponse, handle_generate_response)
        bus.register_async_event_handler(ResponseGenerated, log_generated_response)
        
        # Execute a command
        command = GenerateResponse(prompt="Tell me a joke")
        result = await bus.execute(command)
        
        if result.success:
            # Publish an event
            event = ResponseGenerated(
                prompt=command.prompt,
                response=result.result,
                model_name=command.model_name
            )
            await bus.publish(event)
    finally:
        # Always stop the bus when done
        await bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

This example demonstrates the core flow of the message bus:

1. Define command and event classes to represent your domain
2. Implement handlers for commands and events
3. Register the handlers with the message bus
4. Execute commands to perform actions
5. Publish events to notify the system of changes

The Message Bus makes it easy to create a loosely-coupled system where components can communicate without direct dependencies.

## Other Modules

::: llmgine.foo