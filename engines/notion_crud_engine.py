import asyncio
import uuid
import os
import json
from typing import Any, Callable, Dict, List, Optional

from llmgine.bus.bus import MessageBus
from llmgine.llm.context.memory import SimpleChatHistory
from llmgine.llm.providers.response import OpenAIManager
from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import ToolCall, LLMResponse, Event
from dataclasses import dataclass, field
from llmgine.notion.notion import (
    get_all_users,
    get_active_tasks,
    get_active_projects,
    create_task,
    update_task,
)


@dataclass
class NotionCRUDEnginePromptCommand(Command):
    """Command to process a user prompt with tool usage."""

    prompt: str = ""


@dataclass
class NotionCRUDEngineConfirmationCommand(Command):
    """Command to confirm a user action."""

    prompt: str = ""


@dataclass
class NotionCRUDEngineStatusEvent(Event):
    """Event emitted when a status update is needed."""

    status: str = ""


@dataclass
class NotionCRUDEnginePromptResponseEvent(Event):
    """Event emitted when a prompt is processed and a response is generated."""

    prompt: str = ""
    response: str = ""
    tool_calls: Optional[List[ToolCall]] = None


class NotionCRUDEngine:
    def __init__(
        self,
        session_id: str,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None,
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
        self.message_bus = MessageBus()
        self.engine_id = str(uuid.uuid4())
        self.session_id = session_id
        self.model = model

        # Get API key from environment if not provided
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key must be provided or set as OPENAI_API_KEY environment variable"
            )

        # Create tightly coupled components - pass the simple engine
        self.context_manager = SimpleChatHistory(
            engine_id=self.engine_id, session_id=self.session_id
        )
        self.llm_manager = OpenAIManager(
            engine_id=self.engine_id, session_id=self.session_id
        )
        self.tool_manager = ToolManager(
            engine_id=self.engine_id, session_id=self.session_id, llm_model_name="openai"
        )

        # Set system prompt if provided
        if system_prompt:
            self.context_manager.set_system_prompt(system_prompt)

        # Register command handlers for this specific engine's session
        self.message_bus.register_command_handler(
            self.session_id, NotionCRUDEnginePromptCommand, self.handle_prompt_command
        )

    async def handle_prompt_command(
        self, command: NotionCRUDEnginePromptCommand
    ) -> CommandResult:
        """Handle a prompt command following OpenAI tool usage pattern.

        Args:
            command: The prompt command to handle

        Returns:
            CommandResult: The result of the command execution
        """
        try:
            # 1. Add user message to history
            self.context_manager.store_string(command.prompt, "user")

            # Loop for potential tool execution cycles
            while True:
                # 2. Get current context (including latest user message or tool results)
                current_context = self.context_manager.retrieve()

                # 3. Get available tools
                tools = await self.tool_manager.get_tools()

                # 4. Call LLM
                await self.message_bus.publish(
                    NotionCRUDEngineStatusEvent(
                        status="Calling LLM...",
                        session_id=self.session_id,
                    )
                )
                response = await self.llm_manager.generate(
                    context=current_context, tools=tools
                )

                # 5. Extract the first choice's message object
                # Important: Access the underlying OpenAI object structure
                response_message = response.raw.choices[0].message

                # 6. Add the *entire* assistant message object to history.
                # This is crucial for context if it contains tool_calls.
                self.context_manager.store_assistant_message(response_message)

                # 7. Check for tool calls
                if not response_message.tool_calls:
                    # No tool calls, break the loop and return the content
                    final_content = response_message.content or ""
                    await self.message_bus.publish(
                        NotionCRUDEnginePromptResponseEvent(
                            prompt=command.prompt,
                            response=final_content,
                            tool_calls=None,  # No tool calls in the final response
                            session_id=self.session_id,
                        )
                    )
                    return CommandResult(
                        success=True, original_command=command, result=final_content
                    )

                # 8. Process tool calls
                for tool_call in response_message.tool_calls:
                    tool_call_obj = ToolCall(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=tool_call.function.arguments,
                    )
                    if tool_call_obj.name == "update_task":
                        result = await self.message_bus.execute(
                            NotionCRUDEngineConfirmationCommand(
                                prompt=f"Updating task {tool_call.function.arguments}",
                                session_id=self.session_id,
                            )
                        )
                        if not result.result:
                            self.context_manager.store_tool_call_result(
                                tool_call_id=tool_call_obj.id,
                                name=tool_call_obj.name,
                                content="User denied tool execution",
                            )
                            continue

                    if tool_call_obj.name == "create_task":
                        result = await self.message_bus.execute(
                            NotionCRUDEngineConfirmationCommand(
                                prompt=f"Creating task {tool_call.function.arguments}",
                                session_id=self.session_id,
                            )
                        )
                        if not result.result:
                            self.context_manager.store_tool_call_result(
                                tool_call_id=tool_call_obj.id,
                                name=tool_call_obj.name,
                                content="User denied tool execution",
                            )
                            continue
                    try:
                        # Execute the tool
                        await self.message_bus.publish(
                            NotionCRUDEngineStatusEvent(
                                status=f"Executing tool {tool_call_obj.name}",
                                session_id=self.session_id,
                            )
                        )
                        result = await self.tool_manager.execute_tool_call(tool_call_obj)

                        # Convert result to string if needed for history
                        if isinstance(result, dict):
                            result_str = json.dumps(result)
                        else:
                            result_str = str(result)

                        # Store tool execution result in history
                        self.context_manager.store_tool_call_result(
                            tool_call_id=tool_call_obj.id,
                            name=tool_call_obj.name,
                            content=result_str,
                        )

                    except Exception as e:
                        return CommandResult(
                            success=False, original_command=command, error=str(e)
                        )

        except Exception as e:
            return CommandResult(success=False, original_command=command, error=str(e))

    async def register_tool(self, function: Callable):
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
        command = NotionCRUDEnginePromptCommand(
            prompt=message, session_id=self.session_id
        )
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
