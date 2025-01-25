from typing import Dict, Callable
import json
from pathlib import Path


class CommandRegistry:
    def __init__(self, chat_instance):
        self.chat = chat_instance
        self.commands: Dict[str, Callable] = {
            '/exit': self._handle_exit,
            '/clear': self._handle_clear,
            '/help': self._handle_help,
            '/model': self._handle_model,
            '/mode': self._handle_mode,
            '/system': self._handle_system,
            '/tools': self._handle_tools,
            '/history': self._handle_history,
            '/export': self._handle_export,
            '/load': self._handle_load,
        }

    def handle_command(self, command_input: str) -> bool:
        """Handle a command and return True if handled, False otherwise"""
        parts = command_input.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if command in self.commands:
            self.commands[command](*args)
            return True
        return False

    def _handle_exit(self, *args):
        """Handle the exit command"""
        self.chat.cli.print_info("Goodbye! 👋")
        raise KeyboardInterrupt

    def _handle_clear(self, *args):
        """Handle the clear command"""
        self.chat.engine.store.clear()
        self.chat.cli.clear_messages()
        self.chat.cli.print_info("Chat history cleared! 🧹")

    def _handle_help(self, *args):
        """Handle the help command"""
        self.chat.cli.redraw()

    def _handle_model(self, *args):
        """Handle the model switch command"""
        if not args:
            self.chat.cli.print_error("Please specify a model name")
            return
        try:
            self.chat.engine.model_name = args[0]
            self.chat.cli.print_success(f"Switched to model: {args[0]}")
        except Exception as e:
            self.chat.cli.print_error(f"Error switching model: {str(e)}")

    def _handle_mode(self, *args):
        """Handle the mode switch command"""
        if not args:
            self.chat.cli.print_error("Please specify a mode (normal, minimal, chain, linear_chain)")
            return
        try:
            self.chat.engine._initialize_mode(args[0])
            self.chat.cli.print_success(f"Switched to mode: {args[0]}")
        except Exception as e:
            self.chat.cli.print_error(f"Error switching mode: {str(e)}")

    def _handle_system(self, *args):
        """Handle the system prompt change command"""
        if not args:
            self.chat.cli.print_error("Please specify a system prompt file path")
            return
        try:
            path = Path(args[0])
            if not path.exists():
                self.chat.cli.print_error(f"File not found: {path}")
                return
            with open(path, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
            self.chat.engine.store.set_system_prompt(system_prompt)
            self.chat.cli.print_success(f"Loaded system prompt from: {path}")
        except Exception as e:
            self.chat.cli.print_error(f"Error loading system prompt: {str(e)}")

    def _handle_tools(self, *args):
        """Handle the tools list command"""
        tools = self.chat.engine.tool_manager.tools
        tool_list = "\n".join([f"- {t.funct.__name__}: {t.function_description}" for t in tools])
        self.chat.cli.print_message(f"Available tools:\n\n{tool_list}", "Tools", "cyan")

    def _handle_history(self, *args):
        """Handle the history display command"""
        messages = self.chat.engine.store.retrieve()
        for msg in messages:
            if msg.get("role") == "user":
                self.chat.cli.print_message(msg.get("content"), "User", "blue")
            elif msg.get("role") == "assistant":
                self.chat.cli.print_message(msg.get("content"), "Assistant", "green")
            elif msg.get("role") == "tool":
                self.chat.cli.print_message(
                    msg.get("content")[:500],
                    msg.get("name", "Tool"),
                    "yellow"
                )

    def _handle_export(self, *args):
        """Handle the export command"""
        try:
            export_path = Path("chat_history.json")
            if args:
                export_path = Path(args[0])

            history = self.chat.engine.store.retrieve()
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)

            self.chat.cli.print_success(f"Chat history exported to: {export_path}")
        except Exception as e:
            self.chat.cli.print_error(f"Error exporting chat history: {str(e)}")

    def _handle_load(self, *args):
        """Handle the load command"""
        if not args:
            self.chat.cli.print_error("Please specify a chat history file path")
            return
        try:
            path = Path(args[0])
            if not path.exists():
                self.chat.cli.print_error(f"File not found: {path}")
                return

            with open(path, 'r', encoding='utf-8') as f:
                history = json.load(f)

            self.chat.engine.store.clear()
            for msg in history:
                if msg.get("role") == "system":
                    self.chat.engine.store.set_system_prompt(msg.get("content"))
                else:
                    self.chat.engine.store.chat_history.append(msg)

            self.chat.cli.print_success(f"Loaded chat history from: {path}")
        except Exception as e:
            self.chat.cli.print_error(f"Error loading chat history: {str(e)}")
