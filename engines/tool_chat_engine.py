import uuid
import os
import json
from typing import Any, Dict, List, Optional

from llmgine.bus.bus import MessageBus
from llmgine.llm.context.memory import SimpleChatHistory
from llmgine.llm.providers.response import OpenAIManager
from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import ToolCall, LLMResponse, Event
from dataclasses import dataclass, field


class PromptCommand(Command):
    def __init__(self, message: str, session_id: str = None, tools: List[Any] = None):
        super().__init__()
        self.message = message
        self.session_id = session_id
        self.tools = tools


@dataclass
class PromptResponseEvent(Event):
    """Event emitted when a prompt is processed and a response is generated."""

    prompt: str = ""
    response: str = ""
    tool_calls: Optional[List[ToolCall]] = None
    session_id: str = "global"


@dataclass
class ToolExecutionEvent(Event):
    """Event emitted when a tool is executed."""

    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    session_id: str = "global"


# Create a simple engine interface to avoid circular imports
class SimpleEngine:
    """Simple engine interface to avoid circular imports."""

    def __init__(self, engine_id: str, session_id: str):
        self.engine_id = engine_id
        self.session_id = session_id


class ToolChatEngine:
    def __init__(
        self,
        session_id: str,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None,
        message_bus: Optional[MessageBus] = None,
    ):
        """Initialize the LLM engine.

        Args:
            session_id: The session identifier
            api_key: OpenAI API key (defaults to environment variable)
            model: The model to use
            system_prompt: Optional system prompt to set
            message_bus: Optional MessageBus instance (from bootstrap)
        """
        # Use the provided message bus or create a new one
        self.message_bus = message_bus or MessageBus()
        self.engine_id = str(uuid.uuid4())
        self.session_id = session_id
        self.model = model

        # Get API key from environment if not provided
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key must be provided or set as OPENAI_API_KEY environment variable"
            )

        # Create a simple engine interface to avoid circular imports
        simple_engine = SimpleEngine(engine_id=self.engine_id, session_id=self.session_id)

        # Create tightly coupled components - pass the simple engine
        self.context_manager = SimpleChatHistory(engine=simple_engine)
        self.llm_manager = OpenAIManager(engine=simple_engine)
        self.tool_manager = ToolManager(engine=simple_engine, llm_model_name="openai")

        # Set system prompt if provided
        if system_prompt:
            self.context_manager.set_system_prompt(system_prompt)

        # Register command handlers
        self.message_bus.register_command_handler(
            PromptCommand, self.handle_prompt_command
        )

    async def handle_prompt_command(self, command: PromptCommand) -> CommandResult:
        """Handle a prompt command.

        Args:
            command: The prompt command to handle

        Returns:
            CommandResult: The result of the command execution
        """
        try:
            # Get the current context using retrieve() method from SimpleChatHistory
            context = self.context_manager.retrieve()

            # Get available tools
            tools = (
                await self.tool_manager.get_tools() if command.tools is not None else None
            )

            # Store the user message using store_string() method
            self.context_manager.store_string(command.message, "user")

            # Generate response from LLM
            response = await self.llm_manager.generate(context=context, tools=tools)

            # Store the assistant response using store_response() method
            self.context_manager.store_response(response, "assistant")

            # Check if we have tool calls to execute
            if response.has_tool_calls():
                for tool_call in response.tool_calls:
                    try:
                        # Execute the tool
                        result = await self.tool_manager.execute_tool_call(tool_call)

                        # Convert result to string if it's not already
                        if isinstance(result, dict):
                            result_str = json.dumps(result)
                        else:
                            result_str = str(result)

                        # Store function call result using store_function_call_result()
                        self.context_manager.store_function_call_result({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.name,
                            "content": result_str,
                        })

                        # Publish tool execution event
                        await self.message_bus.publish(
                            ToolExecutionEvent(
                                tool_name=tool_call.name,
                                arguments=json.loads(tool_call.arguments),
                                result=result,
                                session_id=self.session_id,
                            )
                        )

                    except Exception as e:
                        error_msg = f"Error executing tool {tool_call.name}: {str(e)}"
                        # Store error result
                        self.context_manager.store_function_call_result({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.name,
                            "content": error_msg,
                        })

                # Get a follow-up response with the tool results
                follow_up_context = self.context_manager.retrieve()
                follow_up_response = await self.llm_manager.generate(
                    context=follow_up_context
                )

                # Store the follow-up response
                self.context_manager.store_response(follow_up_response, "assistant")

                # Publish event with the follow-up response
                await self.message_bus.publish(
                    PromptResponseEvent(
                        prompt=command.message,
                        response=follow_up_response.content,
                        session_id=self.session_id,
                    )
                )

                return CommandResult(
                    success=True,
                    original_command=command,
                    result=follow_up_response.content,
                )

            # Publish event with the response
            await self.message_bus.publish(
                PromptResponseEvent(
                    prompt=command.message,
                    response=response.content,
                    tool_calls=response.tool_calls,
                    session_id=self.session_id,
                )
            )

            return CommandResult(
                success=True, original_command=command, result=response.content
            )

        except Exception as e:f
            return CommandResult(success=False, original_command=command, error=str(e))

    async def register_tool(self, function):
        """Register a function as a tool.

        Args:
            function: The function to register as a tool
        """
        await self.tool_manager.register_tool(function)

    async def process_message(self, message: str) -> str:
        """Process a user message and return the response.

        Args:
            message: The user message to process

        Returns:
            str: The assistant's response
        """
        command = PromptCommand(message=message, session_id=self.session_id)
        result = await self.message_bus.execute(command)

        if not result.success:
            raise RuntimeError(f"Failed to process message: {result.error}")

        return result.result

    async def clear_context(self):
        """Clear the conversation context."""
        self.context_manager.clear()

    def set_system_prompt(self, prompt: str):
        """Set the system prompt.

        Args:
            prompt: The system prompt to set
        """
        self.context_manager.set_system_prompt(prompt)
