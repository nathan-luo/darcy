#!/usr/bin/env python3
"""Example application using the bootstrap pattern."""

import asyncio
import logging
from dataclasses import dataclass

from llmgine.bootstrap import ApplicationConfig, CommandBootstrap
from llmgine.bus import MessageBus
from llmgine.llm.context import InMemoryContextManager
from llmgine.llm.engine import LLMEngine
from llmgine.llm.engine.messages import (
    ClearHistoryCommand,
    PromptCommand,
    SystemPromptCommand,
    ToolCallEvent,
)
from llmgine.llm.providers import DefaultLLMManager, DummyProvider
from llmgine.llm.tools import ToolManager
from llmgine.ui.cli.tools import calculator, get_current_time


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@dataclass
class ExampleConfig(ApplicationConfig):
    """Configuration for the example application."""
    
    system_prompt: str = """
    You are a specialized assistant focused on calculations and time.
    """


class CustomEngine:
    """Custom LLM engine implementation."""
    
    def __init__(self, message_bus: MessageBus):
        """Initialize the custom engine.
        
        This engine creates its own internal managers rather than having them
        passed in as dependencies.
        
        Args:
            message_bus: The message bus for communication
        """
        self.message_bus = message_bus
        
        # Create internal managers - each engine implementation creates its own
        self.tool_manager = ToolManager()
        self.llm_manager = DefaultLLMManager()
        self.context_manager = InMemoryContextManager()
        
        # Register tools
        self.tool_manager.register_tool(calculator)
        self.tool_manager.register_tool(get_current_time)
        logger.info(f"Registered {len(self.tool_manager.tools)} tools")
        
        # Register LLM providers
        self.llm_manager.register_provider("dummy", DummyProvider())
        logger.info("Registered dummy LLM provider")
    
    async def handle_prompt(self, command: PromptCommand):
        """Handle a user prompt."""
        prompt = command.prompt
        conversation_id = command.conversation_id
        
        # Add user message to context
        user_message = {"role": "user", "content": prompt}
        self.context_manager.add_message(conversation_id, user_message)
        
        # Generate response
        context = self.context_manager.get_context(conversation_id)
        response = await self.llm_manager.generate(prompt=prompt, context=context)
        
        # Add assistant response to context
        assistant_message = {"role": "assistant", "content": response.content}
        self.context_manager.add_message(conversation_id, assistant_message)
        
        return response.content
    
    async def handle_system_prompt(self, command: SystemPromptCommand):
        """Handle setting a system prompt."""
        system_prompt = command.system_prompt
        conversation_id = command.conversation_id
        
        # Get context and replace system message
        context = self.context_manager.get_context(conversation_id)
        context = [msg for msg in context if msg.get("role") != "system"]
        
        # Add new system message
        system_message = {"role": "system", "content": system_prompt}
        self.context_manager.clear_context(conversation_id)
        self.context_manager.add_message(conversation_id, system_message)
        
        # Add back other messages
        for message in context:
            self.context_manager.add_message(conversation_id, message)
        
        return "System prompt set successfully"


class ExampleBootstrap(CommandBootstrap[ExampleConfig]):
    """Bootstrap for registering command handlers with the message bus."""
    
    def __init__(self, config: ExampleConfig):
        """Initialize the bootstrap.
        
        Args:
            config: Example configuration
        """
        # Create message bus and engine
        self.message_bus = MessageBus()
        super().__init__(self.message_bus, config)
        
        # Create engine - it creates its own managers
        self.engine = CustomEngine(self.message_bus)
    
    def _register_command_handlers(self) -> None:
        """Register command handlers from the engine with the message bus."""
        # Connect command types to engine methods
        self.register_command_handler(
            PromptCommand, self.engine.handle_prompt
        )
        self.register_command_handler(
            SystemPromptCommand, self.engine.handle_system_prompt
        )


class ExampleApplication:
    """Example application."""
    
    def __init__(self, bootstrap: ExampleBootstrap):
        """Initialize the application.
        
        Args:
            bootstrap: The application bootstrap
        """
        self.bootstrap = bootstrap

    async def start(self) -> None:
        """Start the application."""
        await self.bootstrap.bootstrap()
        
        # Set system prompt if provided
        if self.bootstrap.config.system_prompt:
            await self.bootstrap.message_bus.execute(
                SystemPromptCommand(self.bootstrap.config.system_prompt)
            )

    async def stop(self) -> None:
        """Stop the application."""
        await self.bootstrap.shutdown()

    async def run(self) -> None:
        """Run the example application."""
        await self.start()
        
        try:
            logger.info("Example application running")
            
            # Send a test prompt
            logger.info("Sending test prompt...")
            result = await self.bootstrap.message_bus.execute(
                PromptCommand("What is 2+2?")
            )
            
            # Display the result
            logger.info(f"Response: {result.result}")
            
            # Send another prompt that uses a tool
            logger.info("Sending prompt that should use calculator tool...")
            result = await self.bootstrap.message_bus.execute(
                PromptCommand("Calculate 10*5")
            )
            
            # Display the result
            logger.info(f"Response: {result.result}")
            
            logger.info("Example complete. Shutting down...")
                
        except Exception as e:
            logger.exception(f"Error running example application: {e}")
        finally:
            await self.stop()


if __name__ == "__main__":
    # Create configuration
    config = ExampleConfig()
    
    # Create and run the application
    bootstrap = ExampleBootstrap(config)
    app = ExampleApplication(bootstrap)
    asyncio.run(app.run())