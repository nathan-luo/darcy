#!/usr/bin/env python3
"""Simple CLI chatbot using the refactored LLMgine.

This example demonstrates using the LLMgine to create a CLI chatbot
with support for function calling.
"""

import argparse
import asyncio
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
from llmgine.llm import (
    LLMEngine,
    PromptCommand,
    SystemPromptCommand,
    LLMResponseEvent,
    ToolCallEvent,
    ToolResultEvent,
    default_tool_manager,
)
from llmgine.llm.providers.openai import OpenAIProvider
from llmgine.messages.events import Event
from llmgine.observability.events import LogLevel


# Sample tools for the chatbot
def get_current_time() -> str:
    """Get the current time."""
    return datetime.now().strftime("%H:%M:%S")


def get_current_date() -> str:
    """Get the current date."""
    return datetime.now().strftime("%Y-%m-%d")


def calculate(a: float, b: float, operation: str) -> float:
    """Perform a calculation.
    
    Args:
        a: First number
        b: Second number
        operation: Operation to perform (add, subtract, multiply, divide)
        
    Returns:
        The result of the calculation
    """
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")


class SimpleCLI:
    """Simple CLI interface for the chatbot."""
    
    def __init__(self):
        """Initialize the CLI interface."""
        self.conversation_id = "default"
        self.prompt = "You> "
        self.bot_name = "Bot"
        self.exit_commands = ["exit", "quit", "/q", "/exit"]
        self.command_handlers = {
            "/help": self._handle_help,
            "/system": self._handle_system_prompt,
            "/clear": self._handle_clear,
            "/reset": self._handle_reset,
            "/model": self._handle_model,
        }
        self.model = "gpt-3.5-turbo"
        self.history = []
        
    def _handle_help(self, args: str) -> bool:
        """Handle the /help command.
        
        Args:
            args: Command arguments
            
        Returns:
            True to continue, False to exit
        """
        print("\nAvailable commands:")
        print("  /help - Show this help message")
        print("  /system <prompt> - Set the system prompt")
        print("  /clear - Clear the terminal screen")
        print("  /reset - Reset the conversation history")
        print("  /model <model> - Set the model to use")
        print(f"  {', '.join(self.exit_commands)} - Exit the chatbot")
        print()
        return True
        
    def _handle_system_prompt(self, args: str) -> bool:
        """Handle the /system command.
        
        Args:
            args: Command arguments
            
        Returns:
            True to continue, False to exit
        """
        if not args:
            print("Usage: /system <prompt>")
            return True
            
        self.app.system_prompt = args
        print(f"System prompt set to: {args}")
        return True
        
    def _handle_clear(self, args: str) -> bool:
        """Handle the /clear command.
        
        Args:
            args: Command arguments
            
        Returns:
            True to continue, False to exit
        """
        os.system('cls' if os.name == 'nt' else 'clear')
        return True
        
    def _handle_reset(self, args: str) -> bool:
        """Handle the /reset command.
        
        Args:
            args: Command arguments
            
        Returns:
            True to continue, False to exit
        """
        self.app.reset_conversation()
        print("Conversation history has been reset.")
        return True
        
    def _handle_model(self, args: str) -> bool:
        """Handle the /model command.
        
        Args:
            args: Command arguments
            
        Returns:
            True to continue, False to exit
        """
        if not args:
            print(f"Current model: {self.model}")
            return True
            
        self.model = args
        print(f"Model set to: {args}")
        return True
        
    def print_bot_message(self, message: str):
        """Print a message from the bot.
        
        Args:
            message: The message to print
        """
        print(f"\n{self.bot_name}> {message}")
        
    def print_tool_call(self, tool_name: str, args: Dict[str, Any]):
        """Print a tool call.
        
        Args:
            tool_name: The name of the tool
            args: The arguments for the tool
        """
        print(f"\n[Tool Call] {tool_name}({', '.join(f'{k}={v}' for k, v in args.items())})")
        
    def print_tool_result(self, result: Any):
        """Print a tool result.
        
        Args:
            result: The result of the tool call
        """
        print(f"[Tool Result] {result}")
        
    async def run_interactive(self, app: 'ChatbotApp'):
        """Run the interactive CLI.
        
        Args:
            app: The chatbot application
        """
        self.app = app
        
        # Print welcome message
        print("\nWelcome to LLMgine Chatbot!")
        print("Type '/help' for available commands or 'exit' to quit.\n")
        
        # Register event handlers
        app.register_event_handler(LLMResponseEvent, self._handle_llm_response)
        app.register_event_handler(ToolCallEvent, self._handle_tool_call)
        app.register_event_handler(ToolResultEvent, self._handle_tool_result)
        
        # Main interaction loop
        while True:
            try:
                # Get user input
                user_input = input(self.prompt).strip()
                
                # Handle exit commands
                if user_input.lower() in self.exit_commands:
                    print("Goodbye!")
                    break
                    
                # Handle CLI commands
                if user_input.startswith('/'):
                    parts = user_input.split(' ', 1)
                    command = parts[0].lower()
                    args = parts[1] if len(parts) > 1 else ""
                    
                    handler = self.command_handlers.get(command)
                    if handler:
                        continue_loop = handler(args)
                        if not continue_loop:
                            break
                        continue
                
                # Process normal user input
                await app.process_message(user_input, model=self.model)
                
            except KeyboardInterrupt:
                print("\nInterrupted by user. Exiting...")
                break
                
            except Exception as e:
                print(f"\nError: {e}")
                
    async def _handle_llm_response(self, event: LLMResponseEvent):
        """Handle an LLM response event.
        
        Args:
            event: The LLM response event
        """
        if event.response.content:
            self.print_bot_message(event.response.content)
    
    async def _handle_tool_call(self, event: ToolCallEvent):
        """Handle a tool call event.
        
        Args:
            event: The tool call event
        """
        import json
        try:
            args = json.loads(event.tool_call.arguments)
            self.print_tool_call(event.tool_call.name, args)
        except json.JSONDecodeError:
            self.print_tool_call(event.tool_call.name, {"arguments": event.tool_call.arguments})
    
    async def _handle_tool_result(self, event: ToolResultEvent):
        """Handle a tool result event.
        
        Args:
            event: The tool result event
        """
        if event.error:
            self.print_tool_result(f"ERROR: {event.error}")
        else:
            self.print_tool_result(event.result)


class ChatbotApp(ApplicationBootstrap):
    """A simple chatbot application using LLMgine."""
    
    def __init__(self):
        """Initialize the chatbot application."""
        # Create configuration
        config = ApplicationConfig(
            app_name="LLMgine Chatbot",
            log_level=LogLevel.INFO,
            log_dir="logs/chatbot",
            console_logging=True,
            file_logging=True,
            metrics_enabled=True,
            tracing_enabled=True
        )
        
        # Initialize bootstrap with config
        super().__init__(config)
        
        # Initialize engine
        self.llm_engine = LLMEngine(
            message_bus=self.message_bus,
            obs_bus=self.obs_bus,
        )
        
        # Register LLM provider
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            print("Warning: OPENAI_API_KEY environment variable not set.")
            print("Using dummy provider instead.")
        else:
            openai_provider = OpenAIProvider(api_key=openai_api_key)
            self.llm_engine.llm_manager.register_provider("openai", openai_provider)
            self.llm_engine.llm_manager.set_default_provider("openai")
        
        # Set default system prompt
        self.system_prompt = "You are a helpful assistant with access to tools. Be concise and direct in your responses."
        
        # Register tools
        self._register_tools()
    
    def _register_command_handlers(self):
        """Register command handlers for the application.
        
        The engine registers its own handlers internally.
        """
        pass
        
    def _register_event_handlers(self):
        """Register event handlers for the application.
        
        Event handlers will be registered by the CLI interface.
        """
        pass
        
    def _register_tools(self):
        """Register tools for the chatbot."""
        default_tool_manager.register_tool(get_current_time)
        default_tool_manager.register_tool(get_current_date)
        default_tool_manager.register_tool(calculate)
        
    def register_event_handler(self, event_type, handler):
        """Register an event handler.
        
        Args:
            event_type: The type of event to handle
            handler: The handler function
        """
        self.message_bus.register_event_handler(event_type, handler)
        
    async def process_message(self, message: str, model: Optional[str] = None):
        """Process a user message.
        
        Args:
            message: The user message
            model: Optional model to use
        """
        # Create prompt command
        prompt_command = PromptCommand(
            prompt=message,
            use_tools=True,
            conversation_id="default",
            model=model
        )
        
        # Execute the command
        result = await self.message_bus.execute(prompt_command)
        
        # Check for errors
        if not result.success:
            error_msg = result.error or "Unknown error"
            print(f"\nError: {error_msg}")
            
    async def reset_conversation(self):
        """Reset the conversation history."""
        # Set the system prompt again
        system_command = SystemPromptCommand(
            system_prompt=self.system_prompt,
            conversation_id="default"
        )
        await self.message_bus.execute(system_command)


async def main():
    """Run the chatbot application."""
    # Create the app
    app = ChatbotApp()
    await app.bootstrap()
    
    # Set the system prompt
    system_command = SystemPromptCommand(
        system_prompt=app.system_prompt,
        conversation_id="default"
    )
    await app.message_bus.execute(system_command)
    
    try:
        # Create and run the CLI
        cli = SimpleCLI()
        await cli.run_interactive(app)
    finally:
        # Shut down the application
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())