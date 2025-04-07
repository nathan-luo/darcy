<file_tree>
📁 Context
├── 📁 src
│   ├── 📄 __init__.py
│   ├── 📁 framework
│   │   ├── 📄 __init__.py
│   │   ├── 📄 exceptions.py
│   │   ├── 📄 telemetry.py
│   │   ├── 📁 chat
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 chat.py
│   │   │   ├── 📄 cli.py
│   │   │   └── 📄 commands.py
│   │   ├── 📁 clients
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 anthropic_client.py
│   │   │   ├── 📄 model_manager.py
│   │   │   ├── 📄 model_registry.py
│   │   │   ├── 📄 openai_client.py
│   │   │   ├── 📄 openrouter_client.py
│   │   │   └── 📄 response.py
│   │   ├── 📁 core
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 agent.py
│   │   │   ├── 📄 chatroom.py
│   │   │   ├── 📄 engine.py
│   │   │   ├── 📄 observer.py
│   │   │   ├── 📄 store.py
│   │   │   ├── 📄 stream_manager.py
│   │   │   └── 📄 streaming.py
│   │   ├── 📁 observability
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 local.py
│   │   │   └── 📄 log_parser.py
│   │   ├── 📁 prompts
│   │   │   ├── 📄 __init__.py
│   │   │   └── 📄 prompts.py
│   │   ├── 📁 tool_calling
│   │   │   ├── 📄 __init__.py
│   │   │   └── 📄 tool_calling.py
│   │   ├── 📁 types
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 block.py
│   │   │   ├── 📄 callbacks.py
│   │   │   ├── 📄 client.py
│   │   │   ├── 📄 client_interface.py
│   │   │   ├── 📄 clients.py
│   │   │   ├── 📄 engine.py
│   │   │   ├── 📄 engine_types.py
│   │   │   ├── 📄 events.py
│   │   │   ├── 📄 model_register.py
│   │   │   ├── 📄 models.py
│   │   │   ├── 📄 openrouter_providers.py
│   │   │   └── 📄 utils.py
│   │   ├── 📁 utils
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 callbacks.py
│   │   │   ├── 📄 client_model_lookup.py
│   │   │   ├── 📄 runtime.py
│   │   │   └── 📄 singleton.py
│   │   └── 📁 workflow
│   │       ├── 📄 __init__.py
│   │       ├── 📄 blocks.py
│   │       ├── 📄 utils.py
│   │       └── 📄 workflow.py
│   └── 📁 interfaces
│       ├── 📄 __init__.py
│       ├── 📁 abstract
│       │   ├── 📄 __init__.py
│       │   └── 📄 abstract_interface.py
│       └── 📁 cli
│           ├── 📄 __init__.py
│           ├── 📄 chat.py
│           ├── 📄 cli.py
│           ├── 📄 observer.py
│           └── 📄 test_cli.py
└── 📁 tools
    ├── 📄 __init__.py
    ├── 📄 calculator.py
    ├── 📄 core.py
    ├── 📄 notion.py
    ├── 📄 notion_abstract.py
    ├── 📄 pwsh.py
    ├── 📄 test.py
    └── 📁 core
        ├── 📄 __init__.py
        └── 📄 terminal.py
</file_tree>

<file path="src\__init__.py">

</file>

<file path="src\framework\__init__.py">

</file>

<file path="src\framework\chat\__init__.py">

</file>

<file path="src\framework\chat\chat.py">
from rich.traceback import install
from loguru import logger

from framework.chat.cli import RichCLI
from framework.chat.commands import CommandHandler
from framework.types.application_events import ApplicationEvent
from framework.types.models import ModelInstance
from framework.types.events import EngineObserverEventType
from framework.core.observer import Observer


class ChatObserver(Observer):
    """Observer for chat events"""

    def __init__(self, cli):
        self.cli = cli
        self.loading = None

    def update(self, event: ApplicationEvent):
        """Handle various event types"""
        if event.event_type == EngineObserverEventType.RESPONSE:
            if "content" in event:
                if hasattr(event["content"], "choices") and event["content"].choices:
                    # Extract content from OpenAI response
                    content = event["content"].choices[0].message.content
                else:
                    # Fallback for other response types
                    content = str(event["content"])
                self.cli.print_message(content, "Assistant", "green")

        elif event["type"] == EngineObserverEventType.FUNCTION_CALL:
            self.cli.print_tool_call(event["name"], event["parameters"])

        elif event["type"] == EngineObserverEventType.FUNCTION_RESULT:
            self.cli.print_message(event["content"]["content"], event["name"], "yellow")

        elif event["type"] == EngineObserverEventType.STATUS_UPDATE:
            if not self.loading:
                self.loading = self.cli.show_loading(event["message"])
                self.loading.__enter__()
            elif event["message"] == "done":
                if self.loading:
                    self.loading.__exit__(None, None, None)
                    self.loading = None
            else:
                self.loading.update_status(event["message"])

    def get_input(self, event: dict) -> str:
        """Handle input requests"""
        if event["type"] == EngineObserverEventType.GET_CONFIRMATION:
            return "yes" if self.cli.get_confirmation(event["message"]) else "no"
        return self.cli.get_input(event["message"])


class Chat:
    """Main chat interface"""

    def __init__(self, engine):
        # Initialize rich console and install traceback handler
        install(
            show_locals=True, width=120, extra_lines=3, theme="monokai", word_wrap=True
        )

        # Initialize components
        self.cli = RichCLI()
        self.engine = engine
        self.model_instance = engine.model
        self.observer = ChatObserver(self.cli)
        self.engine.subscribe(self.observer)
        self.command_handler = CommandHandler(self)

        # Configure logging
        logger.remove()
        logger.add("outputs/logs/chat.log", rotation="10 MB", level="INFO")
        logger.info("Starting Chat Interface")

    def set_model(self, model_instance: ModelInstance):
        """Update the model configuration"""
        self.model_instance = model_instance
        self.engine.change_model(model_instance)
        logger.info(f"Switched to model: {model_instance.model.name}")

    def run(self):
        """Run the chat interface"""
        self.cli.print_info(
            f"Welcome! Using {self.model_instance.model.name} model. "
            "Type /help for available commands."
        )

        while True:
            # Get user input
            user_input = self.cli.get_input()

            # Handle commands
            if user_input.startswith("/"):
                if self.command_handler.handle_command(user_input):
                    continue

            # Process regular message
            self.cli.print_message(user_input, "You", "blue")

            # Execute message
            response = self.engine.execute(user_input)
            self.engine.subject.notify(
                {"type": EngineObserverEventType.STATUS_UPDATE, "message": "done"}
            )

            # Update display
            self.cli.redraw()

</file>

<file path="src\framework\chat\cli.py">
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.spinner import Spinner
from dataclasses import dataclass
from framework.utils.singleton import singleton


@dataclass
class LoadingContext:
    """Context manager for loading spinner"""

    live_context: Live
    spinner: Spinner

    def __enter__(self):
        """Enter the context manager"""
        self.live_context.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager"""
        return self.live_context.__exit__(exc_type, exc_val, exc_tb)

    def update_status(self, status: str):
        """Update the loading spinner status"""
        self.spinner.text = status


@singleton
class RichCLI:
    def __init__(self):
        self.console = Console()
        self.messages = []
        self.layout = Layout()
        self._setup_layout()

    def _setup_layout(self):
        """Initialize the layout structure"""
        self.layout.split(
            Layout(name="chat", ratio=2),
            Layout(name="tools", ratio=1),
        )

    def get_input(self, prompt: str = "You: ") -> str:
        """Get user input with optional custom prompt"""
        try:
            return Prompt.ask(prompt)
        except (KeyboardInterrupt, EOFError):
            return ""

    def get_confirmation(self, message: str) -> bool:
        """Get yes/no confirmation from user"""
        try:
            # If message is a dict, format it nicely
            if isinstance(message, dict):
                formatted_message = (
                    f"\nFunction: {message.get('function', 'Unknown')}\n"
                )
                if "parameters" in message:
                    formatted_message += "Parameters:\n"
                    for key, value in message["parameters"].items():
                        formatted_message += f"  {key}: {value}\n"
                message = formatted_message

            return Confirm.ask(f"{message}\nDo you want to proceed?")
        except (KeyboardInterrupt, EOFError):
            return False

    def print_message(self, content: str, author: str, style: str = "default"):
        """Print a message with author attribution"""
        if not content:
            return

        panel = Panel(
            Markdown(content), title=f"[{style}]{author}[/{style}]", border_style=style
        )
        self.messages.append({"panel": panel, "type": "message"})
        self.redraw()

    def print_tool_call(self, name: str, args: dict, style: str = "yellow"):
        """Print a tool call with its arguments"""
        content = f"Function: {name}\nArguments: {args}"
        panel = Panel(content, title="Tool Call", border_style=style)
        self.messages.append({"panel": panel, "type": "tool"})
        self.redraw()

    def print_reasoning(self, content: str, style: str = "cyan"):
        """Print reasoning content"""
        if not content:
            return

        panel = Panel(Markdown(content), title="Reasoning", border_style=style)
        self.messages.append({"panel": panel, "type": "reasoning"})
        self.redraw()

    def print_error(self, message: str):
        """Print an error message"""
        self.print_message(message, "Error", "red")

    def print_success(self, message: str):
        """Print a success message"""
        self.print_message(message, "Success", "green")

    def print_info(self, message: str):
        """Print an info message"""
        self.print_message(message, "Info", "blue")

    def clear_messages(self):
        """Clear all messages"""
        self.messages.clear()
        self.redraw()

    def show_loading(self, initial_status: str = "Processing...") -> LoadingContext:
        """Show a loading spinner with status"""
        spinner = Spinner("dots", text=initial_status, style="yellow")
        live = Live(
            spinner, console=self.console, refresh_per_second=10, transient=True
        )
        return LoadingContext(live_context=live, spinner=spinner)

    def redraw(self):
        """Redraw the entire display"""
        self.console.clear()
        for message in self.messages:
            self.console.print(message["panel"])

    def print_streaming_content(
        self,
        content: str,
        reasoning: Optional[str] = None,
        tool_calls: Optional[list] = None,
    ):
        """Handle streaming content display"""
        if reasoning:
            self.print_reasoning(reasoning)
        if content:
            self.print_message(content, "Assistant", "green")
        if tool_calls:
            for call in tool_calls:
                self.print_tool_call(
                    call.get("name", "Unknown"), call.get("arguments", {})
                )

</file>

<file path="src\framework\chat\commands.py">
from typing import Dict, Callable
from pathlib import Path
import json

from framework.clients.model_registry import ModelRegistry
from framework.types.models import ModelInstanceRequest
from framework.clients.model_manager import ModelManager


class CommandHandler:
    """Handles chat commands with improved model management"""

    def __init__(self, chat_instance):
        self.chat = chat_instance
        self.model_registry = ModelRegistry()
        self.model_manager = ModelManager()
        self.commands: Dict[str, Callable] = {
            "/exit": self._handle_exit,
            "/clear": self._handle_clear,
            "/help": self._handle_help,
            "/model": self._handle_model,
            "/system": self._handle_system,
            "/tools": self._handle_tools,
            "/history": self._handle_history,
            "/export": self._handle_export,
            "/load": self._handle_load,
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
        raise KeyboardInterrupt

    def _handle_clear(self, *args):
        """Handle the clear command"""
        self.chat.engine.store.clear()
        self.chat.cli.clear_messages()
        self.chat.cli.print_info("Chat history cleared! 🧹")

    def _handle_help(self, *args):
        """Handle the help command"""
        help_text = """
Available commands:
- /exit: Exit the program
- /clear: Clear chat history
- /help: Show this menu
- /model <name>: Switch to a different model
- /system <path>: Load new system prompt
- /tools: List available tools
- /history: Show chat history
- /export: Export chat history
- /load: Load chat history

Type your message to begin...
"""
        self.chat.cli.print_info(help_text)

    def _handle_model(self, *args):
        """Handle the model switch command with improved model instance handling"""
        if not args:
            # List available models with their default providers
            models = self.model_registry.list_models()
            model_info = []
            for model_name in models:
                model = self.model_registry.get_model(model_name)
                model_info.append(
                    f"- {model_name} (Default Provider: {model.default_provider.name})"
                )

            self.chat.cli.print_message(
                "Available models:\n" + "\n".join(model_info), "Models", "cyan"
            )
            return

        model_name = args[0]
        # Create model instance request
        request = ModelInstanceRequest(
            model_name=model_name,
        )

        # Get new model instance
        model_instance = self.model_manager.get_model_instance(request)

        # Update chat with new model instance
        self.chat.set_model(model_instance)

        self.chat.cli.print_success(
            f"Switched to model: {str(model_instance.provider.type)}"
        )

    def _handle_system(self, *args):
        """Handle the system prompt change command"""
        if not args:
            self.chat.cli.print_error("Please specify a system prompt file path")
            return

        path = Path(args[0])
        if not path.exists():
            raise FileNotFoundError(f"System prompt file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            system_prompt = f.read()

        self.chat.engine.store.set_system_prompt(system_prompt)
        self.chat.cli.print_success(f"Loaded system prompt from: {path}")

    def _handle_tools(self, *args):
        """Handle the tools list command"""
        tools = getattr(self.chat.engine, "tools", None)
        if not tools:
            self.chat.cli.print_info("No tools available in current engine mode")
            return

        tool_list = "\n".join(
            [
                f"- {t.__name__}: {getattr(t, 'description', 'No description')}"
                for t in tools
            ]
        )
        self.chat.cli.print_message(f"Available tools:\n\n{tool_list}", "Tools", "cyan")

    def _handle_history(self, *args):
        """Handle the history display command"""
        history = self.chat.engine.store.retrieve()
        for msg in history:
            if msg.get("role") == "user":
                self.chat.cli.print_message(msg.get("content"), "User", "blue")
            elif msg.get("role") == "assistant":
                self.chat.cli.print_message(msg.get("content"), "Assistant", "green")
            elif msg.get("role") == "tool":
                self.chat.cli.print_message(
                    msg.get("content"), msg.get("name", "Tool"), "yellow"
                )

    def _handle_export(self, *args):
        """Handle the export command"""
        export_path = Path("chat_history.json")
        if args:
            export_path = Path(args[0])

        history = self.chat.engine.store.retrieve()
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        self.chat.cli.print_success(f"Chat history exported to: {export_path}")

    def _handle_load(self, *args):
        """Handle the load command"""
        if not args:
            raise ValueError("Please specify a chat history file path")

        path = Path(args[0])
        if not path.exists():
            raise FileNotFoundError(f"Chat history file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)

        self.chat.engine.store.clear()
        for msg in history:
            if msg.get("role") == "system":
                self.chat.engine.store.set_system_prompt(msg.get("content"))
            else:
                self.chat.engine.store.chat_history.append(msg)

        self.chat.cli.print_success(f"Loaded chat history from: {path}")

</file>

<file path="src\framework\clients\__init__.py">
from .openai_client import ClientOpenAI

__all__ = ["ClientOpenAI"]
</file>

<file path="src\framework\clients\anthropic_client.py">
# import anthropic
# from .response import ResponseWrapperAnthropic
#
# class ClientAnthropic:
#     def __init__(self, api_key):
#         self.client = anthropic.Anthropic(api_key=api_key)
#
#     def convert_to_anthorpic(self, context):
#         if context == None:
#             return [], None
#         elif context[0]["role"] == "system":
#             return context[1:], context[0].content
#         else:
#             return context, None
#
#
#     def create_completion(self, model_name, context):
#         context, system = self.convert_to_anthorpic(context)
#         system = system or ""
#         response = self.client.messages.create(model=model_name,
#                                                    system=system,
#                                                    messages=context,
#                                                    temperature=1,
#                                                    max_tokens=8000)
#         return ResponseWrapperAnthropic(response)
</file>

<file path="src\framework\clients\model_manager.py">
from typing import Union
import os

from framework.clients.model_registry import ModelRegistry
from framework.clients.openai_client import ClientOpenAI
from framework.clients.openrouter_client import ClientOpenRouter
from framework.types.clients import ClientType, ClientKeyMap
from framework.utils.singleton import singleton
from framework.types.models import (
    ModelInstanceRequest,
    ClientSetupConfig,
    ModelInstance,
    Model,
)

from dotenv import load_dotenv

load_dotenv(".env")


@singleton
class ModelManager:
    """Manages client instances and model configurations"""

    def __init__(self):
        self.active_clients = []
        self.registry = ModelRegistry()
        self._initialize_client_factories()

    def _initialize_client_factories(self):
        self._client_factories = {
            ClientType.OPENAI: self._create_openai_client,
            ClientType.OPENROUTER: self._create_openrouter_client,
            ClientType.GEMINI_API: self._create_gemini_api_client,
            ClientType.GEMINI_VERTEX: self._create_gemini_vertex_client,
            ClientType.DEEPSEEK: self._create_deepseek_client,
        }

    def _create_openai_client(self, config: ClientSetupConfig) -> ClientOpenAI:
        """Create an OpenAI client"""
        return ClientOpenAI.create_openai(config.api_key)

    def _create_openrouter_client(self, config: ClientSetupConfig) -> ClientOpenRouter:
        """Create an OpenRouter client"""
        return ClientOpenAI.create_openrouter(config.api_key)

    def _create_gemini_vertex_client(self, config: ClientSetupConfig) -> ClientOpenAI:
        """Create a Google client"""
        if not config.project_id or not config.location:
            raise ValueError("project_id and location required for Google client")
        return ClientOpenAI.create_gemini_vertex(config.project_id, config.location)

    def _create_gemini_api_client(self, config: ClientSetupConfig) -> ClientOpenAI:
        """Create a Gemini API client"""
        return ClientOpenAI.create_gemini(config.api_key)

    def _create_deepseek_client(self, config: ClientSetupConfig) -> ClientOpenAI:
        """Create a DeepSeek client"""
        return ClientOpenAI.create_deepseek(config.api_key)

    def get_or_create_client(
        self, config: ClientSetupConfig
    ) -> Union[ClientOpenAI, ClientOpenRouter]:
        """Get an existing client or create a new one"""
        # Check if client already exists in runtime
        if self.active_clients:
            for client in self.active_clients:
                if client.type == config.client:
                    return client

        # Create new client
        factory = self._client_factories.get(config.client)
        if not factory:
            raise ValueError(f"Unsupported provider: {config.client}")

        # noinspection PyArgumentList
        client = factory(config)

        self.active_clients.append(client)
        return client

    def get_client_for_model(
        self, client_type: ClientType
    ) -> Union[ClientOpenAI, ClientOpenRouter]:
        if client_type == ClientType.GEMINI_VERTEX:
            client_config = ClientSetupConfig(
                client=client_type,
                project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
                location=os.getenv("GOOGLE_CLOUD_LOCATION"),
            )
        else:
            client_config = ClientSetupConfig(
                client=client_type,
                api_key=os.getenv(f"{ClientKeyMap[client_type]}"),
            )

        return self.get_or_create_client(client_config)

    def get_model_instance(self, model_request: ModelInstanceRequest) -> ModelInstance:
        """Create a ModelInstance based on the provided request.

        Args:
            model_request: Configuration for the requested model instance

        Returns:
            ModelInstance configured according to the request and defaults
        """
        # Get base model info
        model = self.registry.get_model(model_request.model_name)

        # Determine provider
        provider = self._get_provider(model_request, model)

        # Get provider-specific model name
        provider_model_name = self.registry.get_provider_model_name(
            model, provider.type
        )

        # Handle OpenRouter specific configuration
        openrouter_providers = None
        if provider.type == ClientType.OPENROUTER:
            openrouter_providers = (
                model_request.openrouter_provider or model.openrouter_providers
            )
        return ModelInstance(
            model=model,
            provider=provider,
            provider_model_name=provider_model_name,
            openrouter_provider=openrouter_providers,
            model_extras=model_request.model_extras,
        )

    def _get_provider(
        self, model_request: ModelInstanceRequest, model: Model
    ) -> Union[ClientOpenAI, ClientOpenRouter]:
        """Determine the appropriate provider based on request and model defaults."""
        provider_type = model_request.provider or model.default_provider
        return self.get_client_for_model(provider_type)

</file>

<file path="src\framework\clients\model_registry.py">
from typing import Dict, Optional, List

from framework.types.models import Model
from framework.types.clients import ClientType
from framework.types.model_register import ModelRegister


class ModelRegistry:
    """Central registry of all available models and their configurations"""

    def __init__(self):
        self._models = ModelRegister

    def get_model(self, model_name: str) -> Model:
        """Get information about a specific model"""
        if model_name not in self._models:
            raise ValueError(f"Unknown model: {model_name}")
        return self._models[model_name]

    def get_provider_model_name(self, model_info: Model, provider: ClientType) -> str:
        """Get the provider-specific model name"""
        # Simply use the provider_model_names mapping
        return model_info.provider_name_map.get(provider)

    def list_models(self, provider: Optional[ClientType] = None) -> List[str]:
        """List all available models, optionally filtered by provider"""
        if provider:
            return [
                name
                for name, info in self._models.items()
                if provider in info.allowed_providers
            ]
        return list(self._models.keys())

</file>

<file path="src\framework\clients\openai_client.py">
from __future__ import annotations

from collections import defaultdict

from framework.clients.response import (
    ResponseWrapperOpenAI,
    StreamedResponseWrapperOpenAI,
)
from typing import Optional, List, Dict, Any, Callable

from ..types.application_events import (
    StreamingApplicationEvent,
    StreamingEventTypes,
    StreamingChunkTypes,
)
from ..types.clients import ClientType
from ..types.models import ModelInstance, ToolConfig
from pydantic import BaseModel

from ..types.utils import dummy_function


class ClientOpenAI:
    def __init__(
        self,
        client,
        client_type: ClientType,
    ):
        # Store the client as an instance attribute
        self.client = client
        self.type = client_type
        self.reasoning_effort = None
        self.client_defaults = {}

    @classmethod
    def create_gemini_vertex(cls, project, location):
        import vertexai
        import openai
        from google.auth import default
        from google.auth.transport import requests as transport_requests

        # Initialize Vertex AI
        vertexai.init(project=project, location=location)

        # Obtain credentials
        credentials, _ = default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        auth_request = transport_requests.Request()
        credentials.refresh(auth_request)

        # Initialize OpenAI client
        base_url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/endpoints/openapi"
        client = openai.OpenAI(
            base_url=base_url,
            api_key=credentials.token,  # Use the refreshed token
        )
        # Return an instance of OpenAIWrapper with the initialized client
        return cls(client, ClientType.GEMINI_VERTEX)

    @classmethod
    def create_gemini(cls, api_key: str):
        import openai

        client = openai.OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1alpha/openai/",
            api_key=api_key,
        )
        return cls(client, ClientType.GEMINI_API)

    @classmethod
    def create_openai(cls, api_key):
        import openai

        client = openai.OpenAI(api_key=api_key)
        return cls(client, ClientType.OPENAI)

    @classmethod
    def create_deepseek(cls, api_key: str):
        import openai

        client = openai.OpenAI(base_url="https://api.deepseek.com", api_key=api_key)
        return cls(client, ClientType.DEEPSEEK)

    def create_completion_legacy_v2(self, model_name, context):
        response = self.client.chat.completions.create(
            model=model_name,
            messages=context,
            temperature=1,
            max_tokens=8000,
        )
        return ResponseWrapperOpenAI(response)

    @classmethod
    def create_openrouter(cls, api_key: str):
        import openai

        client = openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        return cls(client, ClientType.OPENROUTER)

    def create_completion(
        self,
        model: ModelInstance,
        context: List[Dict[str, Any]],
        tool_config: Optional[ToolConfig] = None,
        schema: Optional[Dict | BaseModel] = None,
        **kwargs,
    ):
        payload = {
            "model": model.provider_model_name,
            "messages": context,
            "tools": tool_config.tools if tool_config else None,
            "parallel_tool_calls": tool_config.parallel_tool_calls
            if tool_config
            else None,
            "tool_choice": tool_config.tool_choice if tool_config else None,
            "response_format": schema if schema else None,
        }
        if model.model_extras:
            payload.update(model.model_extras)
        if kwargs:
            payload.update(kwargs)
        match model.provider.type:
            case ClientType.OPENROUTER:
                payload["extra_body"] = {}
                payload["extra_body"]["include_reasoning"] = True
                if model.openrouter_provider:
                    payload["extra_body"]["providers"] = {
                        "order": model.provider_model_name,
                        "allow_fallbacks": False,
                    }
        # remove None values from payload
        payload = {k: v for k, v in payload.items() if v is not None}

        response = self.client.chat.completions.create(**payload)
        return ResponseWrapperOpenAI(response, self.type)

    def stream_emit(
        self, emitters: List[Callable] | Callable, event: StreamingApplicationEvent
    ):
        emitters_list = emitters if isinstance(emitters, list) else [emitters]
        for emitter in emitters_list:
            emitter(event)

    def stream_completion(
        self,
        model: ModelInstance,
        context: List[Dict[str, Any]],
        emitters: Optional[List[Callable] | Callable] = dummy_function,
        tool_config: Optional[ToolConfig] = None,
        schema: Optional[Dict | BaseModel] = None,
        **kwargs,
    ):
        payload = {
            "model": model.provider_model_name,
            "messages": context,
            "tools": tool_config.tools if tool_config else None,
            "parallel_tool_calls": tool_config.parallel_tool_calls
            if tool_config
            else None,
            "tool_choice": tool_config.tool_choice if tool_config else None,
            "response_format": schema if schema else None,
            "stream_options": {"include_usage": True},
        }
        if model.model_extras:
            payload.update(model.model_extras)
        if kwargs:
            payload.update(kwargs)
        match model.provider.type:
            case ClientType.OPENROUTER:
                payload["extra_body"] = {}
                payload["extra_body"]["include_reasoning"] = True
                if model.openrouter_provider:
                    payload["extra_body"]["providers"] = {
                        "order": model.provider_model_name,
                        "allow_fallbacks": False,
                    }
        # remove None values from payload
        payload = {k: v for k, v in payload.items() if v is not None}

        chunks = []
        buffer_store = defaultdict(str)

        self.stream_emit(
            emitters, StreamingApplicationEvent(StreamingEventTypes.STARTED)
        )
        with self.client.beta.chat.completions.stream(**payload) as stream:
            for event in stream:
                chunks.append(event)
                match event.type:
                    case "chunk":
                        try:
                            reasoning = event.chunk.choices[0].delta.reasoning
                            if reasoning:
                                buffer_store["reasoning"] += reasoning
                                self.stream_emit(
                                    emitters,
                                    StreamingApplicationEvent(
                                        StreamingEventTypes.CHUNK,
                                        StreamingChunkTypes.REASONING,
                                        {"delta": reasoning, "full": buffer_store},
                                    ),
                                )
                        except (AttributeError, IndexError):
                            pass
                    case "content.delta":
                        buffer_store["content"] += event.delta
                        self.stream_emit(
                            emitters,
                            StreamingApplicationEvent(
                                StreamingEventTypes.CHUNK,
                                StreamingChunkTypes.TEXT,
                                {"delta": event.delta, "full": buffer_store},
                            ),
                        )
                    case "tool_calls.function.arguments.delta":
                        buffer_store["tool_call"] += event.arguments_delta
                        self.stream_emit(
                            emitters,
                            StreamingApplicationEvent(
                                StreamingEventTypes.CHUNK,
                                StreamingChunkTypes.TOOL,
                                {"delta": event.arguments_delta, "full": buffer_store},
                            ),
                        )
        self.stream_emit(
            emitters, StreamingApplicationEvent(StreamingEventTypes.COMPLETED)
        )
        response = stream.get_final_completion()
        return ResponseWrapperOpenAI(response, model.provider.type, chunks)

    def create_completion_legacy(
        self,
        model_name: str,
        context: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        parallel_tool_calls: bool = True,
        tool_choice: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        show_reasoning: bool = True,
    ):
        kwargs = {
            "model": model_name,
            "messages": context,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "extra_body": {},
        }

        if self.reasoning_effort:
            if model_name != "o1-mini-2024-09-12":
                kwargs["reasoning_effort"] = self.reasoning_effort
            kwargs["messages"].pop(0)  # System prompt not supported
            kwargs.pop("max_tokens")
            kwargs.pop("temperature")

        if tools:
            kwargs["tools"] = tools
            kwargs["parallel_tool_calls"] = parallel_tool_calls

        response = self.client.chat.completions.create(**kwargs)

        return ResponseWrapperOpenAI(response, self.reasoning_api_format)

    def create_streaming_completion(
        self,
        model_name: str,
        context: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        parallel_tool_calls: bool = True,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        kwargs = {
            "model": model_name,
            "messages": context,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
            "extra_body": {},
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["parallel_tool_calls"] = parallel_tool_calls

        response = self.client.chat.completions.create(**kwargs)

        return StreamedResponseWrapperOpenAI(response, self.reasoning_api_format)

</file>

<file path="src\framework\clients\openrouter_client.py">
from typing import List, Dict, Any, Optional, Union

from framework.clients.response import ResponseWrapperOpenAI, StreamedResponseWrapperOpenAI
from framework.types.clients import OpenAIReasoningAPIFormat, ClientType
from framework.types.openrouter_providers import OpenRouterProvider

class ClientOpenRouter:

    def __init__(self, api_key: str):
        import openai
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key)
        self.provider_model_store: Dict[str, List[OpenRouterProvider]] = {}
        self.type = ClientType.OPENROUTER

    def set_model_providers(self, model: str,
                            providers: Union[OpenRouterProvider, List[OpenRouterProvider]],
                            ):
        self.provider_model_store[model] = providers if isinstance(providers, list) else [providers]

    def create_completion(self,
                          model_name: str,
                          context: List[Dict[str, Any]],
                          tools: Optional[List[Dict[str, Any]]] = None,
                          parallel_tool_calls: bool = True,
                          max_tokens: int = 4096,
                          temperature: float = 0.7,
                          show_reasoning: bool = True):

        kwargs = {"model": model_name,
                  "messages": context,
                  "temperature": temperature,
                  "max_tokens": max_tokens,
                  "extra_body": {}}

        if show_reasoning:
            kwargs["extra_body"]["include_reasoning"] = show_reasoning

        if model_name in self.provider_model_store and self.provider_model_store[model_name]:
            kwargs["extra_body"]["providers"] = {
                "order": self.provider_model_store[model_name],
                "allow_fallbacks": False
            }

        if not kwargs["extra_body"]:  # If extra_body is empty
            del kwargs["extra_body"]

        if tools:
            kwargs["tools"] = tools
            kwargs["parallel_tool_calls"] = parallel_tool_calls

        response = self.client.chat.completions.create(**kwargs)

        return ResponseWrapperOpenAI(response)

    def create_streaming_completion(self,
                                    model_name: str,
                                    context: List[Dict[str, Any]],
                                    tools: Optional[List[Dict[str, Any]]] = None,
                                    parallel_tool_calls: bool = True,
                                    max_tokens: int = 4096,
                                    temperature: float = 0.7,
                                    show_reasoning: bool = True,
                                    ):

        kwargs = {"model": model_name,
                  "messages": context,
                  "temperature": temperature,
                  "max_tokens": max_tokens,
                  "stream": True,
                  "stream_options": {"include_usage": True},
                  "extra_body": {}}

        if show_reasoning:
            kwargs["extra_body"]["include_reasoning"] = show_reasoning

        if model_name in self.provider_model_store and self.provider_model_store[model_name]:
            kwargs["extra_body"]["providers"] = {
                "order": self.provider_model_store[model_name],
                "allow_fallbacks": False
            }

        if not kwargs["extra_body"]:  # If extra_body is empty
            del kwargs["extra_body"]

        if tools:
            kwargs["tools"] = tools
            kwargs["parallel_tool_calls"] = parallel_tool_calls

        response = self.client.chat.completions.create(**kwargs)

        return StreamedResponseWrapperOpenAI(response, OpenAIReasoningAPIFormat.OPENROUTER)

</file>

<file path="src\framework\clients\response.py">
from typing import List, Any, Optional
from abc import ABC, abstractmethod
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from pydantic import BaseModel
from dataclasses import dataclass, field
from enum import Enum, auto
import openai

from framework.types.clients import OpenAIReasoningAPIFormat, ClientType


class StreamedResponseStatus(Enum):
    CREATED = auto()
    REASONING = auto()
    GENERATING = auto()
    TOOL_CALLING = auto()
    COMPLETED_WITH_CONTENT = auto()
    COMPLETED_WITH_TOOL_CALLS = auto()
    INTERRUPTED = auto()
    FAILED = auto()


@dataclass
class ResponseTokenStats:
    prompt_tokens: int = 0
    reasoning_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    time_till_first_token: float = 0.0  # not implemented
    tokens_per_second: float = 0.0  # not implemented
    total_time_taken: float = 0.0  # not implemented

    def calculate_total_tokens(self):
        self.total_tokens = self.reasoning_tokens + self.completion_tokens


class ResponseWrapper(ABC):
    @property
    @abstractmethod
    def full(self) -> Any:
        pass

    @property
    @abstractmethod
    def stop_reason(self) -> str:
        pass

    @property
    def reasoning(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def content(self) -> str:
        pass

    @property
    @abstractmethod
    def tool_calls(self) -> List[str]:
        pass

    @property
    def tool_calls_raw(self) -> List[ChatCompletionMessageToolCall]:
        raise NotImplementedError

    @property
    @abstractmethod
    def usage(self) -> ResponseTokenStats:
        pass

    @property
    @abstractmethod
    def to_json(self) -> str:
        pass


class ResponseWrapperOpenAI(ResponseWrapper):
    def __init__(
        self,
        response: BaseModel,
        client_type: ClientType = None,
        chunks: Optional[List[BaseModel]] = None,
    ):
        self.raw = response
        self.chunks_store = chunks if chunks else []
        # Reasoning mapping based on client type
        if client_type is None:
            self.get_reasoning_content = lambda x: None
        elif client_type == ClientType.OPENROUTER:
            self.get_reasoning_content = (
                lambda x: x.choices[0].message.reasoning
                if hasattr(x.choices[0].message, "reasoning")
                else None
            )
        elif client_type == ClientType.DEEPSEEK:
            self.get_reasoning_content = (
                lambda x: x.choices[0].message.reasoning_content
                if hasattr(x.choices[0], "reasoning_content")
                else None
            )

    @property
    def full(self) -> BaseModel:
        return self.raw

    @property
    def chunks(self) -> List[BaseModel]:
        return self.chunks_store

    @property
    def reasoning(self) -> str:
        return self.get_reasoning_content(self.raw)

    @property
    def content(self) -> str:
        return (
            self.raw.choices[0].message.content
            if self.raw.choices[0].message.content
            else ""
        )

    @property
    def tool_calls(self) -> List[ChatCompletionMessageToolCall]:
        message = self.raw.choices[0].message
        return message.tool_calls if hasattr(message, "tool_calls") else []

    @property
    def stop_reason(self) -> str:
        return self.raw.choices[0].finish_reason

    @property
    def usage(self) -> ResponseTokenStats:
        return self.raw.usage

    @property
    def to_json(self) -> str:
        return self.raw.to_json()


@dataclass
class StreamedResponseWrapperOpenAI:
    # parameters
    response: Any  # Stream of ChatCompletionChunks
    reasoning_api_format: Optional[OpenAIReasoningAPIFormat] = None

    # internal state
    response_reasoning: str = field(default="", init=False)
    response_content: str = field(default="", init=False)
    response_tool_stream: str = field(default="", init=False)
    response_tool_calls: List[ChatCompletionMessageToolCall] = field(
        default_factory=list, init=False
    )
    response_tool_calls_raw: List[ChatCompletionMessageToolCall] = field(
        default_factory=list, init=False
    )
    chunks: List[BaseModel] = field(default_factory=list, init=False)
    usage: ResponseTokenStats = field(default_factory=ResponseTokenStats, init=False)
    status: StreamedResponseStatus = field(
        default=StreamedResponseStatus.CREATED, init=False
    )

    def __post_init__(self):
        """Initialize the iterator and reasoning content handler"""
        self.iter = self.response.__iter__()

        # Set up reasoning content handler based on API format
        if self.reasoning_api_format is None:
            self.get_reasoning_content = lambda x: None
        elif self.reasoning_api_format == OpenAIReasoningAPIFormat.OPENROUTER:
            self.get_reasoning_content = (
                lambda x: x.choices[0].delta.reasoning
                if hasattr(x.choices[0].delta, "reasoning")
                else None
            )
        elif self.reasoning_api_format == OpenAIReasoningAPIFormat.DEEPSEEK:
            self.get_reasoning_content = (
                lambda x: x.choices[0].delta.reasoning_content
                if hasattr(x.choices[0].delta, "reasoning_content")
                else None
            )
        else:
            raise ValueError(
                f"Invalid reasoning API format: {self.reasoning_api_format}"
            )

    def __iter__(self):
        """Make the class iterable"""
        return self

    def __next__(self) -> BaseModel:
        """Process the next chunk in the stream"""
        try:
            chunk = next(self.iter)
            self.chunks.append(chunk)

            delta = chunk.choices[0].delta

            # Handle tool calls
            if hasattr(delta, "tool_calls") and delta.tool_calls:
                self.response_tool_calls_raw.extend(delta.tool_calls)

            # Handle reasoning content if present
            reasoning_content = self.get_reasoning_content(chunk)
            if reasoning_content:
                self.response_reasoning += reasoning_content
                self.status = StreamedResponseStatus.REASONING

            # Handle regular content
            if hasattr(delta, "content") and delta.content:
                self.response_content += delta.content
                self.status = StreamedResponseStatus.GENERATING

            # Handle completion
            if chunk.choices[0].finish_reason:
                if self.response_tool_calls:
                    self.status = StreamedResponseStatus.COMPLETED_WITH_TOOL_CALLS
                else:
                    self.status = StreamedResponseStatus.COMPLETED_WITH_CONTENT

            return chunk

        except (StopIteration, IndexError):
            # Update usage statistics if available
            if self.chunks and hasattr(self.chunks[-1], "usage"):
                self.usage = self.chunks[-1].usage
            raise StopIteration

        except openai.APIError:
            self.status = StreamedResponseStatus.FAILED
            raise

        except Exception:
            self.status = StreamedResponseStatus.INTERRUPTED
            raise

    @property
    def stop_reason(self) -> str:
        """Get the stop reason from the last chunk"""
        if not self.chunks:
            return ""
        try:
            stop_reason = self.chunks[-2].choices[0].finish_reason
            return stop_reason
        except IndexError:
            raise ValueError("No stop reason available")

    @property
    def content(self) -> str:
        """Get accumulated content"""
        return self.response_content

    @property
    def reasoning(self) -> str:
        """Get accumulated reasoning content"""
        return self.response_reasoning

    @property
    def tool_calls(self) -> List[ChatCompletionMessageToolCall]:
        """Get accumulated tool calls"""
        return self.response_tool_calls

    @property
    def tokens_input(self) -> int:
        """Get input token count"""
        return self.usage.prompt_tokens

    @property
    def tokens_output(self) -> int:
        """Get output token count"""
        return self.usage.completion_tokens

    @property
    def full(self) -> Any:
        """Get full response data"""
        return self

    @property
    def to_json(self) -> str:
        """Convert response to JSON string"""
        # Implement this based on your needs
        return "JSON serialization not implemented"

</file>

<file path="src\framework\core\__init__.py">

</file>

<file path="src\framework\core\agent.py">
from framework.tool_calling.tool_calling import openai_function_wrapper
from framework.types.model_register import LLMInit
from framework.core.engine import AgentEngine
from framework.types.callbacks import StatusCallback


class BasicAgent:
    def __init__(self, config: LLMInit, callback: StatusCallback):
        """_summary_

        Args:
            config (LLMInit): _description_
            callback (StatusCallback): _description_
        """
        self.callback = callback
        self.config = config
        self.engine = AgentEngine(
            client=config.client,
            model_name=config.model_name,
            system_prompt=config.system_prompt,
            tools=config.tools,
            callback=callback,
        )

    def self_tools(self):
        # 1
        @openai_function_wrapper(
            function_description="Add an prompt to your own the prompt queue.",
            parameter_descriptions={"prompt": "prompt in string format"},
        )
        def self_prompt(prompt: str) -> str:
            self.queue_prompt("(self-prompted) " + prompt)
            return f"Prompt added to queue: {prompt}"

        # 2
        @openai_function_wrapper(
            function_description="There's enough information about the \
                requirement of the task. By executing this function, \
                you will proceed to the plannig step.",
            parameter_descriptions={},
        )
        def finish_task_definition():
            self.engine.state = "planning"
            return "Task definition finished."

        # 3
        @openai_function_wrapper(
            function_description="The user has approved your plan. \
                By executing this function, you will proceed to\
                the exeuction step.",
            parameter_descriptions={},
        )
        def finish_planning():
            self.engine.state = "execution"
            return "Planning finished."

        # 4
        @openai_function_wrapper(
            function_description="You need help/additional input/approval from the user. \
                By executing this function, you will proceed to the \
                user input step.",
            parameter_descriptions={},
        )
        def get_user_input():
            self.engine.state = "user_input"
            return "User input started."

        # 5
        @openai_function_wrapper(
            function_description="The user has provided the required input. \
                By executing this function, you will proceed back to the  \
                execution step.",
            parameter_descriptions={},
        )
        def finish_user_input():
            self.engine.state = "execution"
            return "User input finished."

</file>

<file path="src\framework\core\chatroom.py">
# This file is used to define the chatroom class

from .engine import

</file>

<file path="src\framework\core\engine.py">
from framework.core.observer import EngineSubject, Observer
from framework.types.engine import Engine
from framework.types.events import EngineObserverEventType
from framework.types.models import Model, ModelInstance


class SinglePassEngine(Engine):
    def __init__(self, model: ModelInstance, streaming: bool = False):
        self.model: ModelInstance = model
        self.subject: EngineSubject = EngineSubject()
        self.streaming: bool = streaming
        self._create_completion = (
            self.model.provider.create_completion
            if not streaming
            else self.model.provider.stream_completion
        )

    def subscribe(self, observer: Observer):
        self.subject.register(observer)

    def toggle_streaming(self, streaming: bool):
        self.streaming = streaming
        self._create_completion = (
            self.model.provider.stream_completion
            if streaming
            else self.model.provider.create_completion
        )

    def update_completion_function(self):
        self._create_completion = (
            self.model.provider.stream_completion
            if self.streaming
            else self.model.provider.create_completion
        )

    def change_model(self, model: Model):
        self.model = model
        self.update_completion_function()

    def execute(self, prompt: str, **kwargs):
        self.subject.notify(
            {
                "type": EngineObserverEventType.STATUS_UPDATE,
                "message": "Getting LLM Response...",
            }
        )
        if self.streaming:
            kwargs["emitters"] = self.subject.notify
        response = self._create_completion(
            model=self.model, context=[{"role": "user", "content": prompt}], **kwargs
        )
        self.subject.notify(
            {"type": EngineObserverEventType.RESPONSE, "content": response.full}
        )
        return response

</file>

<file path="src\framework\core\observer.py">
from abc import ABC, abstractmethod
from typing import Any

class Observer(ABC):
    @abstractmethod
    def update(self, event):
        pass

    @abstractmethod
    def get_input(self, message: Any) -> str:
        pass

class EngineSubject:
    def __init__(self):
        self._observers = []

    def register(self, observer: Observer):
        self._observers.append(observer)

    def notify(self, event: Any):
        for observer in self._observers:
            observer.update(event)

    def get_input(self, event: Any) -> str:
        for observer in self._observers:
            if observer.get_input:
                return observer.get_input(event)
        raise ValueError("No observer can handle input.")

class DummieEngineSubject:
    def __init__(self):
        pass

    def register(self):
        pass

    def notify(self, event: Any):
        pass

    def get_input(self, event: Any):
        return "Dummie Engine Response"

</file>

<file path="src\framework\core\store.py">
from framework.clients.response import ResponseWrapper, ResponseWrapperOpenAI, StreamedResponseWrapperOpenAI
from typing import Dict, Any, List, Optional, Union
from loguru import logger
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function

def surround_with_thinking(text):
    return f"<thinking>{text}</thinking>"

class ContextStore:
    def __init__(self, system_prompt: Optional[str] = None):
        self.response_log: List[Any] = [] # need to define type
        self.chat_history: List[Any] = []
        self.system: str
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = ""
        
    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt

    def store_response(self, response: Union[ResponseWrapperOpenAI, StreamedResponseWrapperOpenAI], role: str):
        self.response_log.append(response)
        if isinstance(response, StreamedResponseWrapperOpenAI):
            if response.response_reasoning:
                self.chat_history.append({"role": role, "content": surround_with_thinking(response.response_reasoning)
                                     + "\n" + response.response_content})
            else:
                self.chat_history.append({"role": role, "content": response.response_content})
        else:
            self.chat_history.append({"role": role, "content": response.content})

    def store_string(self, string: str, role: str):
        self.response_log.append([role, string])
        self.chat_history.append({"role": role, "content": string})

    def store_tool_response(self, response: ResponseWrapper):
        """Store a tool response in the chat history"""
        self.response_log.append(response)
        if isinstance(response, StreamedResponseWrapperOpenAI):
            calls = []
            call = {
                'id': "",
                'type': "",
                'function': "",
                'arguments': ""
            }
            current_id = None
            for delta in response.response_tool_calls_raw:
                if delta.id and (delta.id != current_id and current_id):
                    # there is a new tool call
                    if (not call['id'] or
                            not call['type'] or
                            not call['function'] or
                            not call['arguments']):
                        raise ValueError("Tool call is missing required fields")
                    calls.append(ChatCompletionMessageToolCall(
                        id=call['id'],
                        type=call['type'],
                        function=Function(name=call['function'],
                                          arguments=call['arguments'])
                    ))
                    call = {
                        'id': "",
                        'type': "",
                        'function': "",
                        'arguments': ""
                    }
                    current_id = delta.id
                    call['id'] = delta.id
                if delta.id and not current_id:
                    current_id = delta.id
                    call['id'] = delta.id
                if delta.type:
                    call['type'] = delta.type
                if delta.function:
                    if delta.function.name:
                        call['function'] = delta.function.name
                    if delta.function.arguments:
                        call['arguments'] += delta.function.arguments
                if delta == response.response_tool_calls_raw[-1]:
                    # last tool call
                    if (not call['id'] or
                            not call['type'] or
                            not call['function'] or
                            not call['arguments']):
                        continue
                    calls.append(ChatCompletionMessageToolCall(
                        id=call['id'],
                        type=call['type'],
                        function=Function(name=call['function'],
                                          arguments=call['arguments'])))
            response.response_tool_calls = calls
            self.chat_history.append({
                "role": "assistant",
                "tool_calls": response.response_tool_calls
            })
        else:
            self.chat_history.append(response.full.choices[0].message)
            for tool_call in response.full.choices[0].message.tool_calls:
                logger.info(f"Tool call: {tool_call}")
    
    def store_function_call_result(self, result: Dict):
        """Store function call result in the chat history
        
        Args:
            result: Dictionary containing role, tool_call_id, name, and result
        """
        self.response_log.append(result)
        self.chat_history.append(result)

    def retrieve(self):
        result = self.chat_history.copy()
        result.insert(0, {"role": "system", "content": self.system_prompt})
        return result
        
    def clear(self):
        self.response_log = []
        self.chat_history = []
        self.system_prompt = ""



class BasicChatContextStore:
    def __init__(self, system_prompt: Optional[str] = None):
        self.response_log: List[Any] = [] # need to define type
        self.chat_history: List[Dict[str, str]] = []
        self.system: str
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = ""
        
    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt

    def store_response(self, response: ResponseWrapper, role: str):
        self.response_log.append(response)
        self.chat_history.append({"role": role, "content": response.content})

    def store_string(self, string: str, role: str):
        self.response_log.append([role, string])
        self.chat_history.append({"role": role, "content": string})
        
    def retrieve(self):
        result = self.chat_history.copy()
        if self.system_prompt != "":
            result.insert(0, {"role": "system", "content": self.system_prompt})
        return result
        
    def clear(self):
        self.response_log = []
        self.chat_history = []
        self.system_prompt = ""

</file>

<file path="src\framework\core\stream_manager.py">
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from typing import List, Optional
import asyncio
from dataclasses import dataclass
from framework.core.streaming import StreamingEngine, StreamingClientOpenAI


@dataclass
class ToolCall:
    name: str
    arguments: str
    result: Optional[str] = None


class StreamDisplay:
    """Manages the display of streaming content and tool calls"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.layout = Layout()
        self.setup_layout()
        self.content = ""
        self.tool_calls: List[ToolCall] = []
        self.live: Optional[Live] = None

    def setup_layout(self):
        """Set up the display layout"""
        self.layout.split(
            Layout(name="main", ratio=2),
            Layout(name="tools", ratio=1),
        )

    def create_main_panel(self) -> Panel:
        """Create the main content panel"""
        return Panel(
            Text(self.content),
            title="LLM Response",
            border_style="blue"
        )

    def create_tools_panel(self) -> Panel:
        """Create the tools panel"""
        if not self.tool_calls:
            return Panel(
                "",
                title="Tool Calls",
                border_style="yellow"
            )

        tool_text = ""
        for i, tool in enumerate(self.tool_calls):
            tool_text += f"Tool {i + 1}: {tool.name}\n"
            tool_text += f"Args: {tool.arguments}\n"
            if tool.result:
                tool_text += f"Result: {tool.result}\n"
            tool_text += "\n"

        return Panel(
            Text(tool_text.strip()),
            title="Tool Calls",
            border_style="yellow"
        )

    def update_display(self):
        """Update the live display"""
        self.layout["main"].update(self.create_main_panel())
        self.layout["tools"].update(self.create_tools_panel())

        if self.live:
            self.live.update(self.layout)

    def stream_content(self, content: str):
        """Add new streaming content"""
        self.content += content
        self.update_display()

    def add_tool_call(self, name: str, arguments: str):
        """Add a new tool call"""
        self.tool_calls.append(ToolCall(name=name, arguments=arguments))
        self.update_display()

    def update_tool_result(self, index: int, result: str):
        """Update the result of a tool call"""
        if 0 <= index < len(self.tool_calls):
            self.tool_calls[index].result = result
            self.update_display()

    async def start_streaming(self, generator):
        """Start streaming from a generator"""
        try:
            with Live(self.layout, console=self.console, refresh_per_second=10) as live:
                self.live = live

                async for chunk in generator:
                    self.stream_content(chunk)
                    await asyncio.sleep(0.05)  # Adjust for smooth updates

        finally:
            self.live = None

    def clear(self):
        """Clear the display"""
        self.content = ""
        self.tool_calls = []
        self.update_display()


class StreamManager:
    """Manages the streaming experience"""

    def __init__(self, engine, display: Optional[StreamDisplay] = None):
        self.engine = engine
        self.display = display or StreamDisplay()

    async def process_prompt(self, prompt: str):
        """Process a prompt and display streaming results"""
        # Clear previous display
        self.display.clear()

        # Start streaming
        await self.display.start_streaming(self.engine.stream_response(prompt))

    def add_tool_result(self, tool_index: int, result: str):
        """Add a tool result to the display"""
        self.display.update_tool_result(tool_index, result)


# Example usage:
async def main():
    # Initialize your streaming engine
    import dotenv
    dotenv.load_dotenv()
    import os

    client = StreamingClientOpenAI(os.getenv("OPENAI_API_KEY"))

    engine = StreamingEngine(client, "gpt-4o-mini", [], "You are a helpful assistant.")

    # Create display manager
    manager = StreamManager(engine)

    # Process a prompt
    await manager.process_prompt("Tell me about streaming LLMs")

    # Add tool results if needed
    manager.add_tool_result(0, "Tool execution result")


if __name__ == "__main__":
    asyncio.run(main())

</file>

<file path="src\framework\core\streaming.py">
from typing import AsyncGenerator, Generator, Optional, Dict, Any
from openai.types.chat import ChatCompletionChunk, ChatCompletion
from framework.clients.response import ResponseWrapper
from framework.core.store import ContextStore
from framework.core.observer import EngineSubject, Observer
from framework.clients.openai_client import ClientOpenAI


class StreamingResponseWrapper(ResponseWrapper):
    """Wrapper for streaming responses"""

    def __init__(self, response: ChatCompletionChunk):
        self.data = response

    @property
    def full(self) -> ChatCompletionChunk:
        return self.data

    @property
    def content(self) -> str:
        return self.data.choices[0].delta.content or ""

    @property
    def tool_calls(self) -> list:
        if hasattr(self.data.choices[0].delta, 'tool_calls'):
            return self.data.choices[0].delta.tool_calls
        return []

    @property
    def stop_reason(self) -> Optional[str]:
        return self.data.choices[0].finish_reason

    @property
    def tokens_input(self) -> int:
        # Not available in streaming response
        return 0

    @property
    def tokens_output(self) -> int:
        # Not available in streaming response
        return 0

    @property
    def to_json(self) -> str:
        return self.data.model_dump_json()


class StreamingClientOpenAI(ClientOpenAI):
    """Extension of OpenAI client with streaming capabilities"""

    async def create_streaming_completion(
            self,
            model_name: str,
            context: list,
            tools: Optional[list] = None,
    ) -> AsyncGenerator[StreamingResponseWrapper, None]:
        """Create a streaming completion"""
        kwargs = {
            "model": model_name,
            "messages": context,
            "temperature": 1,
            "max_tokens": 8000,
            "top_p": 1,
            "stream": True
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        async for chunk in await self.client.chat.completions.create(**kwargs):
            yield StreamingResponseWrapper(chunk)


class StreamingEngine:
    """Engine that supports streaming LLM responses"""

    def __init__(
            self,
            client: StreamingClientOpenAI,
            model_name: str,
            tools: Optional[list] = None,
            system_prompt: Optional[str] = None,
    ):
        self.client = client
        self.model_name = model_name
        self.tools = tools or []
        self.store = ContextStore()
        self.subject = EngineSubject()

        if system_prompt:
            self.store.set_system_prompt(system_prompt)

    def subscribe(self, observer: Observer):
        """Add an observer to the engine"""
        self.subject.register(observer)

    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream a response for a given prompt"""
        # Store user prompt
        self.store.store_string(prompt, "user")

        # Initialize accumulated response
        accumulated_response = ""
        accumulated_tool_calls = []
        current_tool_call = None

        # Notify observers that streaming is starting
        self.subject.notify({
            "type": "stream_start",
            "message": "Starting response stream..."
        })

        try:
            # Get streaming response
            async for chunk in await self.client.create_streaming_completion(
                    self.model_name,
                    self.store.retrieve(),
                    tools=self.tools
            ):
                # Handle tool calls if present
                if chunk.tool_calls:
                    for tool_call in chunk.tool_calls:
                        if not current_tool_call or tool_call.index != current_tool_call.index:
                            if current_tool_call:
                                accumulated_tool_calls.append(current_tool_call)
                            current_tool_call = tool_call
                        else:
                            # Merge with current tool call
                            if hasattr(tool_call, 'function'):
                                if hasattr(tool_call.function, 'name'):
                                    current_tool_call.function.name += tool_call.function.name
                                if hasattr(tool_call.function, 'arguments'):
                                    current_tool_call.function.arguments += tool_call.function.arguments

                # Handle content if present
                if chunk.content:
                    accumulated_response += chunk.content
                    yield chunk.content

                # Handle end of response
                if chunk.stop_reason:
                    if current_tool_call:
                        accumulated_tool_calls.append(current_tool_call)
                    break

        finally:
            # Store the complete response
            if accumulated_response:
                self.store.store_string(accumulated_response, "assistant")

            # Handle any accumulated tool calls
            if accumulated_tool_calls:
                self.subject.notify({
                    "type": "tool_calls",
                    "tool_calls": accumulated_tool_calls
                })

            # Notify observers that streaming is complete
            self.subject.notify({
                "type": "stream_end",
                "message": "Stream completed"
            })


class StreamingObserver(Observer):
    """Observer for handling streaming updates"""

    def __init__(self, display_class):
        self.display = display_class(title="LLM Response")
        self.current_stream = None

    def update(self, event: Dict[str, Any]):
        """Handle various streaming events"""
        if event["type"] == "stream_start":
            # Initialize new stream display
            self.current_stream = ""
        elif event["type"] == "content":
            # Update display with new content
            self.current_stream += event["content"]
            self.display.update_content(self.current_stream)
        elif event["type"] == "tool_calls":
            # Handle tool calls
            self.display.show_tool_calls(event["tool_calls"])
        elif event["type"] == "stream_end":
            # Finalize display
            self.display.finish_stream()

    def get_input(self, event: Any) -> str:
        """Handle input requests if needed"""
        return ""

</file>

<file path="src\framework\exceptions.py">
class ResponseConversionError(Exception):
    def __init__(self, message, response):
        super().__init__(message)
        self.response = response


class WorkflowError(Exception):
    def __init__(self, message, response):
        super().__init__(message)
        self.response = response

class BlockError(Exception):
    def __init__(self, message, response):
        super().__init__(message)
        self.response = response


class BlockException(Exception):
    """Custom exception for block execution failures"""

    def __init__(self, message: str, block: Block, traceback: Optional[str] = None):
        super().__init__(message)
        self.block = block
        self.traceback = traceback or format_exc()

</file>

<file path="src\framework\observability\__init__.py">

</file>

<file path="src\framework\observability\local.py">

</file>

<file path="src\framework\observability\log_parser.py">

</file>

<file path="src\framework\prompts\__init__.py">

</file>

<file path="src\framework\prompts\prompts.py">
import json
import re

"""
Prompt Structure
{
"args": {
    "arg1": "description",
    "arg2": "description",
    ...},
"prompt": "prompt string"
}
"""

class Prompt:
    def __init__(self, prompt: dict):
        self.args = prompt['args']
        self.nargs = len(prompt['args'].keys())
        self.prompt = prompt['prompt']
   
    @classmethod
    def from_file(cls, path: str):
        with open(path, 'r') as file:
            prompt = json.load(file)
        return cls(prompt)

    def compile(self, *args) -> str:
        input = {}
        if len(args) != self.nargs:
            raise ValueError(f"Expected {self.nargs} arguments, got {len(args)}")
        i = 0
        for arg in self.args.keys():
            input[arg] = args[i]
            i += 1
        return self.prompt.format(**input)

    @property
    def info(self):
        return f"Prompt has arguments {self.args} and prompt {self.prompt}"

    @property
    def args_info(self):
        return str(self.args)

    def save(self, path: str):
        with open(path, 'w') as file:
            json.dump({'args': self.args, 'prompt': self.prompt}, file, indent=4)

def validate_prompt_format(prompt: str, args: dict[str, str]) -> bool:
    """
    Validates that all args are present in the prompt string as format placeholders.
    
    Args:
        prompt: The prompt string with format placeholders
        args: Dictionary of argument names and descriptions
        
    Returns:
        bool: True if all args are present in prompt, False otherwise
    """
    # Find all format placeholders in prompt
    format_args = sorted(list(set(re.findall(r'\{([^}]+)\}', prompt))))
    # Get sorted list of argument names
    arg_names = sorted(list(args.keys()))
    
    # Check if all args are in format_args and vice versa
    return format_args == arg_names

def make_prompt(name: str, prompt: str, args: dict[str, str], save=False) -> Prompt:
    if save:
        with open(f"prompts/{name}.json", 'w') as file:
            json.dump({'args': args, 'prompt': prompt}, file, indent=4)
    return Prompt({'prompt': prompt, 'args': args})


    
if __name__ == "__main__":
    # Basic prompt testing
    prompt = Prompt.from_file('prompts/hello_world.json')
    print("Basic prompt testing:")
    print(prompt.compile('hello', 'world'))
    print(prompt.info)
    print(prompt.args_info)
    print("=============")
    
    # Testing validate_prompt_format
    print("\nTesting validate_prompt_format:")
    
    def run_test(name: str, prompt: str, args: dict[str, str]):
        # Find format args and arg names for display
        format_args = sorted(list(set(re.findall(r'\{([^}]+)\}', prompt))))
        arg_names = sorted(list(args.keys()))
        is_valid = validate_prompt_format(prompt, args)
        
        print(f"\nTest: {name}")
        print(f"Prompt: {prompt}")
        print(f"Args provided: {args}")
        print(f"Format args found: {format_args}")
        print(f"Arg names provided: {arg_names}")
        print(f"Valid: {is_valid}")
        print("-" * 50)
    
    # Test 1: Valid prompt format
    run_test(
        "Valid format",
        "Test {arg1} and {arg2}",
        {"arg1": "first", "arg2": "second"}
    )
    
    # Test 2: Missing arg in prompt
    run_test(
        "Missing arg in prompt",
        "Test {arg1} only",
        {"arg1": "first", "arg2": "second"}
    )
    
    # Test 3: Extra arg in prompt
    run_test(
        "Extra arg in prompt",
        "Test {arg1} and {arg2} and {arg3}",
        {"arg1": "first", "arg2": "second"}
    )
    
    # Test 4: Empty prompt and args
    run_test(
        "Empty prompt and args",
        "",
        {}
    )
    
    # Test 5: Complex format with multiple occurrences and different order
    run_test(
        "Multiple occurrences and different order",
        "Test {arg2} first, then {arg1} twice: {arg1}",
        {"arg1": "first", "arg2": "second"}
    )

</file>

<file path="src\framework\telemetry.py">

</file>

<file path="src\framework\tool_calling\__init__.py">
from .tool_calling import (
    ToolManager,
    openai_function_wrapper,
    create_tools_schema,
    create_tools_lookup,
    parse_functions,
    execute_function
)

__all__ = ['ToolManager',
              'openai_function_wrapper',
              'create_tools_schema',
              'create_tools_lookup',
              'parse_functions',
              'execute_function']

</file>

<file path="src\framework\tool_calling\tool_calling.py">
from typing import List, Callable, Dict
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
import inspect
import json
from loguru import logger
from pprint import pformat

from rich.pretty import Pretty

from framework.core.observer import EngineSubject
from interfaces.abstract import Interface
from framework.types.events import EngineObserverEventType

from framework.types.callbacks import StatusCallback

# ====== Function Calling Decorator ======

def openai_function_wrapper(
        funct_descript: str,
        param_descript: Dict[str, str],
        required_parameters: List[str] = None,
        enum_parameters: Dict[str, List[str]] = None,
        strict: bool = True,
        additional_properties: bool = False,
) -> Callable:
    def decorator(funct: Callable) -> Callable:
        class FunctionWrapper:
            def __init__(self):
                self.funct = funct
                self.function_description = funct_descript
                self.parameter_descriptions = param_descript
                self.enum_parameters = enum_parameters
                self.required_parameters = required_parameters
                self.strict = strict
                self.output = {
                    "type": "function",
                    "function": {
                        "name": funct.__name__,
                        "description": self.function_description,
                        "parameters": {
                            "type": "object",
                            "required": self.required_parameters or [],
                            "properties": {},
                            "additionalProperties": additional_properties,
                        },
                        "strict": strict
                    },
                }
                self._inspect_parameters()

            parameter_map = {
                str: "string",
                int: "integer",
                float: "number",
                bool: "boolean",
            }

            def _inspect_parameters(self):
                """
                Inspect the function signature and create a schema for the parameters
                """
                signature = inspect.signature(self.funct)
                for name, param in signature.parameters.items():
                    param_info = {
                        "description": self.parameter_descriptions.get(name, ""),
                        "type": (
                            self.parameter_map[param.annotation]
                            if param.annotation in self.parameter_map
                            else "string"
                        ),
                    }
                    if self.enum_parameters:
                        if name in self.enum_parameters:
                            param_info["enum"] = self.enum_parameters[name]
                    self.output["function"]["parameters"]["properties"][
                        name
                    ] = param_info
                    if self.strict:
                        # openai recommends to use strict, so this is the default and 99%
                        self.output["function"]["parameters"]["required"].append(name)
                    else:
                        # if not strict, required parameters are those specified in the function signature
                        if name in self.required_parameters:
                            continue
                        # if the parameter does not have a default value, it is required
                        if param.default == inspect.Parameter.empty:
                            if name not in self.output["function"]["parameters"]["required"]:
                                self.output["function"]["parameters"]["required"].append(name)

            def __call__(self, *args, **kwargs):
                return self.funct(*args, **kwargs)

        return FunctionWrapper()

    return decorator

# ====== Tool Manager Class ======

class ToolManager:
    def __init__(self,
                 tools: List[Callable],
                 store_result: Callable,
                 subject: EngineSubject,
                 confirm: bool = False):
        """
        Args:
            tools: List of functions to be used as tools
            store_result: Function to store the result of the tool call
        """
        self.tools = tools
        self.tools_schema = create_tools_schema(tools)
        self.tools_lookup = create_tools_lookup(tools)
        self.store_result = store_result
        self.subject = subject
        self.confirm = confirm
        self.confirm_status = True
        logger.debug(f"Tool Manager initialized with {len(tools)} tools")
        logger.debug(f"Tools schema: {pformat(self.tools_schema)}")

    def execute_responses(self, calls: List[ChatCompletionMessageToolCall]):
        for call in calls:
            # self.subject.notify({
            #     "type": EngineObserverEventType.FUNCTION_CALL,
            #     "tool_call_id": call.id,
            #     "name": call.function.name,
            #     "parameters": json.loads(call.function.arguments)
            # })
            self.subject.notify({
                "type": EngineObserverEventType.STATUS_UPDATE,
                "message": f"Executing function {call.function.name}..."
            })
            if self.confirm:
                self.confirm_status = self.subject.get_input({
                    "type": EngineObserverEventType.GET_CONFIRMATION,
                    # "message": f"[bold]Function:[/bold] '{call.function.name}'\n"
                    #            f"[bold]Parameters:[/bold] {(json.loads(call.function.arguments))}"
                    "message": {
                        "function": call.function.name,
                        "parameters": json.loads(call.function.arguments)
                    }
                })
            if self.confirm_status:
                try:
                    result = execute_function(call, tools_lookup=self.tools_lookup)
                    logger.info(f"Successfully executed function {call.function.name}")
                except Exception as e:
                    result = f"Error executing function {call.function.name}: {e}"
                    logger.info(f"Error executing function {call.function.name}: {e}")
            else:
                logger.info(f"Function {call.function.name} execution cancelled")
                result = "Function execution cancelled by user"
            result = {
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.function.name,
                "content": str(result)}
            self.store_result(result)
            self.subject.notify({
                "type": EngineObserverEventType.FUNCTION_RESULT,
                "tool_call_id": call.id,
                "name": call.function.name,
                "content": result
            })
            logger.info(f"Stored function call result: {result}")

# ====== Tool Manager Helper Functions ======

def create_tools_schema(functions: List[callable]) -> List[Dict]:
    tools = []
    for function in functions:
        tools.append(function.output)
    return tools

def create_tools_lookup(functions: List[callable]) -> Dict[str, callable]:
    tools_lookup = {}
    for function in functions:
        tools_lookup[function.funct.__name__] = function
    return tools_lookup

def parse_functions(tool_calls: List[ChatCompletionMessageToolCall]) -> List[callable]:
    functions = []
    if tool_calls:
        for tool in tool_calls:
            if tool.type == "function":
                functions.append(tool)
    else:
        raise ValueError("No tool calls found in response")
    return functions

def execute_function(function_object, tools_lookup: Dict[str, callable]):
    function = tools_lookup[function_object.function.name]
    kwargs = json.loads(function_object.function.arguments)
    for key, value in kwargs.items():
        if value == "":
            kwargs[key] = None
    result = function(**kwargs)
    return str(result)

</file>

<file path="src\framework\types\__init__.py">
from .block import Block

</file>

<file path="src\framework\types\block.py">
from abc import ABC, abstractmethod


class Block:
    @abstractmethod

    def execute(self, **kwargs) -> None:
        """Basic message execution"""
        pass

</file>

<file path="src\framework\types\callbacks.py">

from abc import ABC, abstractmethod

class StatusCallback(ABC):
    @abstractmethod
    def execute(self, **kwargs) -> None:
        """Basic message execution"""
        pass
    
    @abstractmethod
    def __enter__(self):
        """Enter loading state"""
        pass
    
    @abstractmethod
    def __exit__(self, exc_type, 
                 exc_val,
                 exc_tb) -> None:
        """Exit loading state"""
        pass
    
    @abstractmethod
    def update_status(self, message: str) -> None:
        """Update loading state message"""
        pass

    @abstractmethod
    def get_input(self, message: str) -> str:
        """Get input from user"""
        pass

class SimpleCallback(ABC):
    """
    Simply sends a message to the stack above
    """
    @abstractmethod
    def do(self, **kwargs):
        pass

</file>

<file path="src\framework\types\client.py">

</file>

<file path="src\framework\types\client_interface.py">
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class LLMClient(ABC):
    @abstractmethod
    def create_completion(
        self, model: , **kwargs
    ):
        pass

    @abstractmethod
    def create_streaming_completion(
        self, model_name: str, context: List[Dict[str, Any]], **kwargs
    ):
        pass

</file>

<file path="src\framework\types\clients.py">
from enum import Enum, auto
from typing import Dict


class ClientType(Enum):
    OPENAI = "openai"
    GEMINI_VERTEX = "gemini_vertex"
    GEMINI_API = "gemini_api"
    OPENROUTER = "openrouter"
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"


ClientKeyMap: Dict[ClientType, str] = {
    ClientType.OPENAI: "OPENAI_API_KEY",
    ClientType.GEMINI_API: "GEMINI_API_KEY",
    ClientType.OPENROUTER: "OPENROUTER_API_KEY",
    ClientType.DEEPSEEK: "DEEPSEEK_API_KEY",
    ClientType.ANTHROPIC: "ANTHROPIC_API_KEY",
}


class OpenAIReasoningAPIFormat(Enum):
    OPENROUTER = auto()
    DEEPSEEK = auto()
    GEMINI = auto()

</file>

<file path="src\framework\types\engine.py">
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

class ToolEngineMode(Enum):
    NORMAL = auto()
    MINIMAL = auto()
    CHAIN = auto()
    LINEAR_CHAIN = auto()

class Engine(ABC):
    @abstractmethod
    def subscribe(self, observer):
        pass

    @abstractmethod
    def execute(self, prompt: str):
        pass

</file>

<file path="src\framework\types\engine_types.py">
from pydantic import BaseModel
from typing import Literal, TypeAlias, Dict, Union, Type
from enum import Enum, auto
from framework.core.engine import ToolEngine, SimpleChatEngine

class EngineType(str, Enum):
    ToolEngine = auto()
    SimpleChatEngine = auto()

EngineTypeMap: Dict[EngineType | str, Type[ToolEngine | SimpleChatEngine] | EngineType] = {
    "ToolEngine": EngineType.ToolEngine,
    EngineType.ToolEngine: ToolEngine,
    "SimpleChatEngine": EngineType.SimpleChatEngine,
    EngineType.SimpleChatEngine: SimpleChatEngine}

</file>

<file path="src\framework\types\events.py">
from enum import Enum, auto


class EngineObserverEventType(Enum):
    RESPONSE = auto()
    FUNCTION_CALL = auto()
    FUNCTION_RESULT = auto()
    STATUS_UPDATE = auto()
    GET_INPUT = auto()
    GET_CONFIRMATION = auto()
    STREAM = auto()
    AWAITING_STREAM_COMPLETION = auto()

</file>

<file path="src\framework\types\model_register.py">
from typing import Dict
from .models import Model
from framework.types.clients import ClientType

ModelRegister: Dict[str, Model] = {
    "gpt-4o-mini": Model(
        name="gpt-4o-mini",
        default_provider=ClientType.OPENAI,
        allowed_providers=[ClientType.OPENAI, ClientType.OPENROUTER],
        provider_name_map={
            ClientType.OPENAI: "gpt-4o-mini",
            ClientType.OPENROUTER: "openai/gpt-4o-mini",
        },
    ),
    "gpt-4o": Model(
        name="gpt-4o",
        default_provider=ClientType.OPENAI,
        allowed_providers=[ClientType.OPENAI, ClientType.OPENROUTER],
        provider_name_map={
            ClientType.OPENAI: "gpt-4o",
            ClientType.OPENROUTER: "openai/chatgpt-4o-latest",
        },
    ),
    "o3-mini": Model(
        name="o3-mini",
        default_provider=ClientType.OPENAI,
        allowed_providers=[ClientType.OPENAI],
        provider_name_map={
            ClientType.OPENAI: "o3-mini",
        },
    ),
    "o1-mini": Model(
        name="o1-mini",
        default_provider=ClientType.OPENAI,
        allowed_providers=[ClientType.OPENAI],
        provider_name_map={
            ClientType.OPENAI: "o1-mini",
        },
    ),
    "gemini-2.0-flash": Model(
        name="gemini-2.0-flash",
        default_provider=ClientType.GEMINI_API,
        allowed_providers=[
            ClientType.GEMINI_API,
            ClientType.GEMINI_VERTEX,
        ],
        provider_name_map={
            ClientType.GEMINI_API: "gemini-2.0-flash-exp",
            ClientType.GEMINI_VERTEX: "google/gemini-2.0-flash-001",
        },
    ),
    "gemini-flash-2.0-thinking": Model(
        name="gemini-flash-2.0-thinking",
        default_provider=ClientType.OPENROUTER,
        allowed_providers=[ClientType.GEMINI_API, ClientType.OPENROUTER],
        provider_name_map={
            ClientType.GEMINI_API: "gemini-2.0-flash-thinking-exp-01-21",
            ClientType.OPENROUTER: "google/gemini-2.0-flash-thinking-exp:free",
        },
    ),
    "gemini-pro-2.0": Model(
        name="gemini-pro-2.0",
        default_provider=ClientType.GEMINI_API,
        allowed_providers=[ClientType.GEMINI_API],
        provider_name_map={
            ClientType.GEMINI_API: "gemini-exp-1206",
        },
    ),
    "claude-3.5-sonnet": Model(
        name="claude-3.5-sonnet",
        default_provider=ClientType.OPENROUTER,
        allowed_providers=[ClientType.OPENROUTER],
        provider_name_map={ClientType.OPENROUTER: "anthropic/claude-3.5-sonnet"},
    ),
    "deepseek-v3": Model(
        name="deepseek-v3",
        default_provider=ClientType.OPENROUTER,
        allowed_providers=[ClientType.DEEPSEEK, ClientType.OPENROUTER],
        provider_name_map={
            ClientType.DEEPSEEK: "deepseek-v3",
            ClientType.OPENROUTER: "deepseek/deepseek-chat",
        },
    ),
    "deepseek-r1": Model(
        name="deepseek-r1",
        default_provider=ClientType.OPENROUTER,
        allowed_providers=[ClientType.DEEPSEEK, ClientType.OPENROUTER],
        openrouter_providers=["DeepSeek", "DeepInfra", "Nebius"],
        provider_name_map={
            ClientType.DEEPSEEK: "deepseek-r1",
            ClientType.OPENROUTER: "deepseek/deepseek-r1",
        },
    ),
    "llama-3.1-405b": Model(
        name="llama-3.1-405b",
        default_provider=ClientType.OPENROUTER,
        allowed_providers=[ClientType.OPENROUTER],
        openrouter_providers=["DeepInfra", "Lambda"],
        provider_name_map={ClientType.OPENROUTER: "meta-llama/llama-3.1-405b-instruct"},
    ),
}

</file>

<file path="src\framework\types\models.py">
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, List, Literal, Union, Any

from framework.types.clients import ClientType
from framework.types.openrouter_providers import OpenRouterProvider
from pydantic import BaseModel, field_validator

__all__ = [
    "ToolChoiceFunction",
    "ToolChoice",
    "ToolConfig",
    "ConfigDefaults",
    "Model",
    "ClientSetupConfig",
    "ModelInstanceRequest",
    "ModelInstance",
    "OpenAIReasoningEffort",
]


class OpenAIReasoningEffort(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolChoiceFunction(BaseModel):
    """
    Attributes:
        name: str
    """

    name: str


class ToolChoice(BaseModel):
    """
    Attributes:
        function: ToolChoiceFunction
        type: Literal["function"]
    """

    function: ToolChoiceFunction
    type: str = "function"

    def __init__(self, name: str):
        super().__init__(function=ToolChoiceFunction(name=name))


class ToolConfig(BaseModel):
    """
    Attributes:
        tools: tools schema
        parallel_tool_calls: bool
        tool_choice: ToolChoice | Literal["none", "auto"]
    """

    tools: List[Dict]
    parallel_tool_calls: Optional[bool] = None
    tool_choice: Optional[Literal["none", "auto"] | ToolChoice] = None


@dataclass
class Model:
    """
    Attributes:
        name: str
        default_provider: ClientType
        provider_name_map: Dict[ClientType, str]
        allowed_providers: Optional[List[ClientType]] = None
        openrouter_providers: List[Optional[OpenRouterProvider]] = None
    """

    name: str  # Our internal reference name
    default_provider: ClientType
    provider_name_map: Dict[ClientType, str]  # Mapping of provider names to model names
    allowed_providers: Optional[List[ClientType]] = None
    openrouter_providers: List[Optional[OpenRouterProvider]] = None


@dataclass
class ClientSetupConfig:
    """
    Attributes:
        client: ClientType
        api_key: str
        project_id: Optional[str] = None
        location: Optional[str] = None
    """

    client: ClientType
    api_key: Optional[str] = None
    project_id: Optional[str] = None  # For Google
    location: Optional[str] = None  # For Google


@dataclass
class ModelInstanceRequest:
    """
    Attributes:
        model_name: str
        provider: Optional[ClientType] = None
        openrouter_provider: Optional[OpenRouterProvider] = None
        model_defaults: Optional[Dict[str, str]] = None
    """

    model_name: str
    provider: Optional[ClientType] = None
    openrouter_provider: Optional[OpenRouterProvider] = None
    model_extras: Optional[Dict[str, str]] = None

    @field_validator("openrouter_provider")
    def validate_openrouter_provider(
        cls, v: Optional[OpenRouterProvider], info
    ) -> Optional[OpenRouterProvider]:
        if v and info.raw.get("provider") != ClientType.OPENROUTER:
            raise ValueError(
                "openrouter_provider can only be set when provider is OPENROUTER"
            )
        return v


@dataclass
class ModelInstance:
    """
    Attributes:
        model: Model
        provider_model_name: str
        provider: ClientType
        openrouter_provider: Optional[OpenRouterProvider] = None
        model_extras: Optional[Dict[str, str]] = None
    """

    model: Model
    provider_model_name: str
    provider: Union["ClientOpenAI", "ClientOpenRouter"]
    openrouter_provider: Optional[List[OpenRouterProvider] | OpenRouterProvider] = None
    model_extras: Optional[Dict[str, Any]] = None

</file>

<file path="src\framework\types\openrouter_providers.py">
from typing import Literal, TypeAlias



OpenRouterProvider: TypeAlias = Literal[
    "OpenAI",
    "Anthropic",
    "Google",
    "Google AI Studio",
    "Amazon Bedrock",
    "Groq",
    "SambaNova",
    "Cohere",
    "Mistral",
    "Together",
    "Together 2",
    "Fireworks",
    "DeepInfra",
    "Lepton",
    "Novita",
    "Avian",
    "Lambda",
    "Azure",
    "Modal",
    "AnyScale",
    "Replicate",
    "Perplexity",
    "Recursal",
    "OctoAI",
    "DeepSeek",
    "Infermatic",
    "AI21",
    "Featherless",
    "Inflection",
    "xAI",
    "Cloudflare",
    "SF Compute",
    "Minimax",
    "Nineteen",
    "Liquid",
    "Nebius",
    "Chutes",
    "Kluster",
    "01.AI",
    "HuggingFace",
    "Mancer",
    "Mancer 2",
    "Hyperbolic",
    "Hyperbolic 2",
    "Lynn 2",
    "Lynn",
    "Reflection"
]

</file>

<file path="src\framework\types\utils.py">
from framework.utils.singleton import singleton



def dummy_function(self, *args, **kwargs):
    return

</file>

<file path="src\framework\utils\__init__.py">
from .callbacks import DummieStatusCallback, CLIStatusCallback

</file>

<file path="src\framework\utils\callbacks.py">
from framework.types.callbacks import StatusCallback, SimpleCallback

class DummieStatusCallback(StatusCallback):
    def execute(self, message: str) -> None:
        pass
    
    def __enter__(self):
        pass
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def update_status(self, message: str) -> None:
        pass

    def get_input(self, message: str) -> str:
        return ""

class CLIStatusCallback(StatusCallback):
    def __init__(self, cli):
        self.cli = cli
        self.loading = None
        
    def execute(self, message: str, title: str, style: str) -> None:
        self.cli.print_message(message, title, style)
    
    def __enter__(self):
        self.loading = self.cli.show_loading("Engine starting...").__enter__()
        return self.loading
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.loading:
            self.loading.__exit__(exc_type, exc_val, exc_tb)
            self.loading = None
    
    def update_status(self, message: str) -> None:
        if self.loading:
            self.loading.update_status(message)
    
    def get_input(self, message: str) -> str:
        return self.cli.get_input(message)

class FunctionStudioSimpleCallback(SimpleCallback):
    def __init__(self):
        self.data = {}

    def do(self, key: str, data: str):
        self.data[key] = data

</file>

<file path="src\framework\utils\client_model_lookup.py">
from dataclasses import dataclass
from enum import Enum, auto
from framework.clients.openai_client import ClientOpenAI
from framework.clients.openrouter_client import ClientOpenRouter


class Clients(Enum):
    OPENROUTER_CLIENT = auto()
    OPENAI_CLIENT = auto()
    GEMINI_CLIENT = auto()
    DEEPSEEK_CLIENT = auto()

</file>

<file path="src\framework\utils\runtime.py">
from pydantic import BaseModel
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Union
from framework.clients.openai_client import ClientOpenAI
from framework.clients.openrouter_client import ClientOpenRouter


@dataclass
class Runtime:
    session_id: str = datetime.now().strftime("%Y%m%d%H%M%S")
    client_list: Optional[List[Union[ClientOpenAI, ClientOpenRouter]]] = field(default_factory=list)

global_runtime = None

def init_global_runtime():
    global global_runtime
    global_runtime = Runtime()

def get_global_runtime():
    global global_runtime
    return global_runtime

</file>

<file path="src\framework\utils\singleton.py">
def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance

</file>

<file path="src\framework\workflow\__init__.py">

</file>

</file>

<file path="src\interfaces\__init__.py">

</file>

<file path="src\interfaces\abstract\__init__.py">
from .abstract_interface import Interface, DummyInterface

</file>

<file path="src\interfaces\abstract\abstract_interface.py">
from abc import ABC, abstractmethod
from typing import Any

class Interface(ABC):
    @abstractmethod
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def get(self, request: Any) -> str:
        pass

    @abstractmethod
    def out(self, content: Any) -> str:
        pass

class DummyInterface(Interface):
    def __init__(self, **kwargs):
        pass

    def get(self, request: Any) -> str:
        return "DummyInterface get"

    def out(self, content: Any) -> str:
        return "DummyInterface out"

</file>

<file path="src\interfaces\cli\__init__.py">
from .cli import ToolCLI

</file>

<file path="src\interfaces\cli\chat.py">
from typing import Dict, Optional

from framework.types.engine import Engine


class CLIChat:
    def __init__(self,
                 engine: Engine,
                 context: Optional[Dict[str, str]] = None,):
        """Initialize CLI Chat with configuration"""
        self.engine = engine
        self.context = context or {}

    def run(self):
        """Run the CLI Chat interface"""
        print("CLI Chat Interface")
        print("Available commands:")
        print("1. chat")
        print("2. exit")

        while True:
            command = input("Enter command: ")
            if command == "chat":
                self.chat()
            elif command == "exit":
                break
            else:
                print("Invalid command")

</file>

<file path="src\interfaces\cli\cli.py">
import os
from typing import List, Dict, Optional, Any
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich import box
from rich.live import Live
from rich.spinner import Spinner
from rich.pretty import Pretty
from rich.rule import Rule

def wrap_with_thinking(text: str) -> str:
    """Wrap text in thinking emoji."""
    return f"<thinking>\n{text}\n</thinking>\n"


class ToolCLI:
    """Simplified CLI interface with menu, messages, and loading states."""
    
    def __init__(self, menu_text: Optional[str] = None):
        self.console = Console()
        self.commands = []
        self.messages = []  # Store all messages to redraw
        self.command_functions = {}  # Store command functions
        
        # Default menu text if none provided
        self.menu_text = menu_text or """
🔧 Command Interface

Type 'help' for available commands
Type 'exit' to quit
"""

    def clear_messages(self):
        """Clear all stored messages."""
        self.messages = []

    def add_message(self, content: str, author: str, style: str):
        """Add a message to the message list."""
        self.messages.append({"content": content, "author": author, "style": style})

    def redraw(self):
        """Clear screen and redraw all content."""
        self.clear_terminal()

        # Print menu once at the top
        self.console.print(Panel(
            Text(self.menu_text, justify="center", style="bold white"),
            title="Command Interface",
            subtitle="v1.0",
            border_style="blue",
            box=box.HEAVY
        ))

        # Print all stored messages
        for msg in self.messages:
            try:
                # Try to render as markdown first
                content = Markdown(msg["content"])
            except Exception:
                # Fall back to plain text if markdown parsing fails
                content = Text(msg["content"], style=msg["style"])
            
            self.console.print(Panel(
                content,
                title=msg["author"],
                border_style=msg["style"],
                box=box.ROUNDED
            ))

    def print_message(self, content: str, author:str, style: str):
        """Print a boxed message with an author."""
        msg = {"content": content, "author": author, "style": style}
        try:
            # Try to render as markdown first
            content = Markdown(msg["content"])
        except Exception:
            try:
            # Fall back to plain text if markdown parsing fails
                content = Text(msg["content"], style=msg["style"])
            except Exception:
                content = Pretty(msg["content"], expand_all=True)

        self.console.print(Panel(
            content,
            title=msg["author"],
            border_style=msg["style"],
            box=box.ROUNDED
        ))

    def print_streamed_message(self, response: Any):
        # todo find proper type for response
        """Print a message that updates live within a panel."""
        with Live(None, vertical_overflow='visible', auto_refresh=True) as live:
            for chunk in response:
                if response.reasoning:
                    live.update(
                        Panel(Markdown(wrap_with_thinking(response.reasoning)+response.content), style="green",
                              title="Assistant"))
                if response.content:
                    live.update(Panel(Markdown(response.content), border_style="green", title="Assistant"))
                if response.response_tool_stream:
                    live.update(Panel(Markdown(response.response_tool_stream), border_style="green", title="Assistant"))


    def add_and_redraw(self, content: str, author: str, style: str = "blue"):
        """Print a boxed message with an author."""
        message = {"content": content, "author": author, "style": style}
        self.messages.append(message)
        self.redraw()

    def show_loading(self, message: str = "Processing..."):
        """
        Show a loading spinner with updateable message.
        Returns a context manager that can be used to update the loading message.
        
        Example:
            with cli.show_loading("Initial message...") as loading:
                # Do some work
                loading.update("Step 1...")
                # Do more work
                loading.update("Step 2...")
        """
        spinner = Spinner("dots", text=Text(message, style="yellow"))
        live = Live(
            spinner,
            console=self.console,
            refresh_per_second=10,
            transient=True
        )
        
        class LoadingContext:
            def __init__(self, live_context, spinner):
                self.live_context = live_context
                self.spinner = spinner
            
            def __enter__(self):
                self.live_context.__enter__()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                return self.live_context.__exit__(exc_type, exc_val, exc_tb)
            
            def update_status(self, new_message: str):
                """Update the loading message."""
                self.spinner.text = Text(new_message, style="yellow")
        
        return LoadingContext(live, spinner)

    def get_input(self, prompt: str = "You") -> str:
        """Get input from user and store command."""
        # Create a gradient prompt
        self.console.print(Rule(
            title=f"[bold blue]{prompt}[/bold blue]",
            style="blue",
        ))
        user_input = self.console.input("❯ ")
        
        if user_input.lower() not in ['exit', 'quit']:
            self.commands.append(user_input)
            # Add user input as a message
            self.print_message(user_input, prompt, "blue")
        # Check if input matches a registered command function
        if user_input.lower() in self.command_functions:
            try:
                self.command_functions[user_input.lower()]()
            except Exception as e:
                self.print_error(f"Error executing command: {str(e)}")
        self.clear_terminal()
        self.redraw()
        return user_input

    def get_confirmation(self, prompt: str = "You") -> str:
        """Get input from user and store command."""
        self.console.print(Panel(Pretty(prompt, expand_all=True), title="[bold]Confirmation function call? (y/n)[/bold]", border_style="yellow"))
        user_input = self.console.input("❯ ")
        return user_input

    def load_command(self, func) -> None:
        """
        Register a function to be executed when its name is typed as a command.
        The function name will be converted to lowercase for case-insensitive matching.
        
        Args:
            func: The function to register as a command
        """
        command_name = func.__name__.lower()
        self.command_functions[command_name] = func

    def clear_terminal(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def get_command_history(self) -> List[str]:
        """Get list of stored commands."""
        return self.commands

    def print_error(self, message: str):
        """Print an error message."""
        self.print_message(message, "Error", "red")

    def print_info(self, message: str):
        """Print an info message."""
        self.print_message(message, "Info", "yellow")

    def print_success(self, message: str):
        """Print a success message."""
        self.print_message(message, "Success", "green")

</file>

<file path="src\interfaces\cli\observer.py">
from framework.core.observer import Observer
from typing import Any
from interfaces.cli import ToolCLI
from rich.prompt import Confirm

class CLIObserver(Observer):
    def __init__(self, cli_interface: ToolCLI):
        self.cli_interface = cli_interface
        self.loading = None

    def update(self, event: Any):
        if event["type"] == "response":
            self.cli_interface.print_message(event["content"], event["type"], "green")
        if event["type"] == "function_call":
            self.cli_interface.print_message(event["parameters"], event["name"], "yellow")
        if event["type"] == "function_result":
            self.cli_interface.print_message(event["content"]["content"], event["name"], "yellow")
        if event["type"] == "status_update":
            if not self.loading:
                self.loading = self.cli_interface.show_loading(event["message"])
                self.loading.__enter__()
            elif event["message"] == "done":
                if self.loading:
                    self.loading.__exit__(None, None, None)
                    self.loading = None
                else:
                    raise Exception("Loading spinner not initialized.")
            else:
                self.loading.update_status(event["message"])

    def get_input(self, event: Any):
        if event["type"] == "confirm":
            while True:
                self.loading.live_context.stop()
                response = self.cli_interface.get_confirmation(event["message"]).lower().strip()
                self.loading.live_context.start()
                if response in ['yes', 'y']:
                    return True
                elif response in ['no', 'n']:
                    return False
                print("Please enter 'yes' or 'no'")
        return self.cli_interface.get_input(event["message"])

</file>

<file path="src\interfaces\cli\test_cli.py">
from cli import ToolCLI
from rich.spinner import Spinner
from rich.text import Text
import time

# Create a single CLI instance that can be accessed by all functions
cli = ToolCLI(menu_text="""
🚀 Enhanced CLI Demo

Available commands:
- greet: Display a friendly greeting
- process: Run a multi-step process
- exit/quit: Exit the program

Type a command to begin:
""")

def greet():
    """Example command that prints a greeting"""
    cli.print_success("👋 Hello from the greet command!")

def process():
    """Example command that demonstrates updateable loading state"""
    with cli.show_loading("Starting process...") as loading:
        # Simulate multi-step process
        time.sleep(1)
        loading.update_status("Step 1: Initializing...")
        time.sleep(1)
        loading.update_status("Step 2: Processing data...")
        time.sleep(1)
        loading.update_status("Step 3: Finalizing...")
        time.sleep(1)
    cli.print_success("✅ Process completed successfully!")

def main():
    # Register command functions
    cli.load_command(greet)
    cli.load_command(process)
    
    # Show different message types with markdown
    cli.print_message("""# Welcome to the CLI Interface!
    
This interface supports **markdown** formatting including:
- *Italic text*
- **Bold text**
- `Code blocks`
- Lists and more

## Example Code
```python
def hello():
    print("Hello, World!")
```
""", "System", "green")

    cli.print_error("**Error:** Something went wrong!")
    cli.print_success("✅ Operation completed with `status=200`")
    cli.print_info("""### Information
1. First point
2. Second point
3. Third point""")
    cli.print_message("*Custom styled message with markdown*", "Custom", "magenta")
    
    while True:
        try:
            # Get user input
            user_input = cli.get_input()
            
            # Handle exit
            if user_input.lower() in ['exit', 'quit']:
                cli.print_info("Goodbye!")
                break
            
            # Show loading state for unrecognized input
            if user_input.lower() not in cli.command_functions:
                with cli.show_loading("Processing input...") as loading:
                    time.sleep(1)  # Simulate processing
                cli.print_message(f"Unrecognized command: {user_input}", "Echo", "cyan")
            
        except KeyboardInterrupt:
            cli.print_error("Operation cancelled")
            break

if __name__ == "__main__":
    main()

</file>

<file path="tools\__init__.py">

</file>
