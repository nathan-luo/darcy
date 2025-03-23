"""CLI interface using Rich for the LLMgine chatbot."""

import asyncio
import logging
from typing import Any, Dict, List

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.syntax import Syntax

from llmgine.bus import MessageBus
from llmgine.llm.engine import LLMResponseEvent, PromptCommand
from llmgine.messages.commands import Command
from llmgine.messages.events import Event
from llmgine.llm.tools import ToolCallEvent, ToolResultEvent

logger = logging.getLogger(__name__)


class UIEvent(Event):
    """Base class for UI events."""
    pass


class MessageDisplayedEvent(UIEvent):
    """Event emitted when a message is displayed in the UI."""

    def __init__(self, role: str, content: str):
        super().__init__()
        self.role = role
        self.content = content


class UserInputReceivedEvent(UIEvent):
    """Event emitted when user input is received."""

    def __init__(self, input_text: str):
        super().__init__()
        self.input_text = input_text


class ExitCommand(Command):
    """Command to exit the application."""
    pass


class ClearHistoryCommand(Command):
    """Command to clear the conversation history."""
    pass


class CLIInterface:
    """Rich CLI interface for the chatbot."""

    def __init__(self, message_bus: MessageBus):
        """Initialize the CLI interface.
        
        Args:
            message_bus: The message bus for command and event handling
        """
        self.message_bus = message_bus
        self.console = Console()
        self.messages: List[Dict[str, Any]] = []
        self.running = False
        self.spinner = None

        # Register event handlers
        self.message_bus.register_async_event_handler(
            LLMResponseEvent, self._handle_llm_response)
        self.message_bus.register_async_event_handler(
            ToolCallEvent, self._handle_tool_call)
        self.message_bus.register_async_event_handler(
            ToolResultEvent, self._handle_tool_result)

    def print_message(self, content: str, role: str, style: str) -> None:
        """Print a message to the console.
        
        Args:
            content: The message content
            role: The role (user, assistant, system, tool)
            style: The style to use for the panel border
        """
        # Convert to markdown for better rendering
        if role.lower() not in ("tool", "system"):
            content_md = Markdown(content)
        else:
            # For tool results, use syntax highlighting if it looks like JSON
            if content.strip().startswith("{") and content.strip().endswith("}"):
                try:
                    # Try to format as JSON
                    content_md = Syntax(content, "json", theme="monokai")
                except Exception:
                    content_md = content
            else:
                content_md = content

        # Create a panel with the content
        title = role.capitalize()
        panel = Panel(content_md, title=title, border_style=style)

        # Print the panel
        self.console.print(panel)

        # Store in message history for context
        self.messages.append({
            "role": role,
            "content": content,
            "style": style
        })

        # Emit event
        asyncio.create_task(
            self.message_bus.publish(MessageDisplayedEvent(role, content))
        )

    def print_system_message(self, content: str) -> None:
        """Print a system message.
        
        Args:
            content: The message content
        """
        self.print_message(content, "System", "cyan")

    async def _handle_llm_response(self, event: LLMResponseEvent) -> None:
        """Handle an LLM response event.
        
        Args:
            event: The LLM response event
        """
        # Clear spinner if active
        if self.spinner:
            self.spinner = None

        self.print_message(event.response, "Assistant", "green")

    async def _handle_tool_call(self, event: ToolCallEvent) -> None:
        """Handle a tool call event.
        
        Args:
            event: The tool call event
        """
        # Format arguments as JSON
        args_str = "\n" + "\n".join(
            f"  {k}: {v}" for k, v in event.arguments.items()
        )

        self.print_message(
            f"Calling tool: {event.tool_name}{args_str}",
            "Tool Call",
            "yellow"
        )

        # Show spinner while waiting for tool result
        self.spinner = Spinner("dots", text=f"Executing {event.tool_name}...", style="yellow")
        spinner_live = Live(self.spinner, console=self.console, refresh_per_second=10, transient=True)
        spinner_live.start()
        self.spinner = spinner_live

    async def _handle_tool_result(self, event: ToolResultEvent) -> None:
        """Handle a tool result event.
        
        Args:
            event: The tool result event
        """
        # Clear spinner if active
        if self.spinner:
            self.spinner.stop()
            self.spinner = None

        if event.error:
            self.print_message(
                f"Error: {event.error}",
                f"Tool Error: {event.tool_name}",
                "red"
            )
        else:
            self.print_message(
                str(event.result),
                f"Tool Result: {event.tool_name}",
                "bright_yellow"
            )

    async def run(self) -> None:
        """Run the CLI interface main loop."""
        self.running = True

        # Print welcome message
        self.print_system_message(
            "Welcome to LLMgine Chatbot! Type /help for commands, or /exit to quit."
        )

        while self.running:
            try:
                # Get user input
                user_input = Prompt.ask("[bold blue]You[/bold blue]")

                # Emit user input event
                await self.message_bus.publish(UserInputReceivedEvent(user_input))

                # Handle commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue

                # Display user message
                self.print_message(user_input, "User", "blue")

                # Show thinking spinner
                thinking_spinner = Spinner("dots", text="Thinking...", style="yellow")
                with Live(thinking_spinner, console=self.console, refresh_per_second=10, transient=True):
                    # Send prompt command
                    command = PromptCommand(user_input)
                    await self.message_bus.execute(command)

            except KeyboardInterrupt:
                self.print_system_message("Interrupted.")
            except Exception as e:
                logger.exception(f"Error in CLI interface: {e}")
                self.print_message(f"Error: {e!s}", "Error", "red")

    async def _handle_command(self, command: str) -> None:
        """Handle a command input.
        
        Args:
            command: The command text including the slash
        """
        cmd = command.lower().split()[0]

        if cmd == "/exit":
            self.print_system_message("Exiting...")
            self.running = False
            return

        elif cmd == "/clear":
            # Send clear history command
            await self.message_bus.execute(ClearHistoryCommand())
            self.messages = []
            self.console.clear()
            self.print_system_message("Conversation history cleared.")
            return

        elif cmd == "/help":
            help_text = """
            Available commands:
            /exit - Exit the application
            /clear - Clear conversation history
            /help - Show this help message
            """
            self.print_system_message(help_text)
            return

        else:
            self.print_message(f"Unknown command: {cmd}", "Error", "red")
            return
