import asyncio
from types import NoneType
import uuid
import os
import json
from typing import Any, Callable, Dict, List, Optional

from llmgine.bus.bus import MessageBus
from llmgine.llm.context.memory import SimpleChatHistory
from llmgine.llm.models.gemini_models import Gemini25FlashPreview
from llmgine.llm.models.openai_models import Gpt41Mini
from llmgine.llm.providers.providers import Providers
from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.llm.tools.types import ToolCall
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from dataclasses import dataclass, field
from tools.notion.notion import (
    get_all_users,
    get_active_tasks,
    get_active_projects,
    create_task,
    update_task,
)

from tools.notion.data import (
    get_user_from_notion_id,
    notion_user_id_type,
    UserData,
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


class NotionCRUDEngineV2:
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
        self.temp_project_lookup = {}
        self.temp_task_lookup = {}

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
        # self.llm_manager = Gpt41Mini(Providers.OPENAI)
        self.llm_manager = Gemini25FlashPreview(Providers.OPENROUTER)
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

    async def register_tools(self, function_list: List[Callable]):
        """Register tools for the engine.
        """
        for function in function_list:
            await self.tool_manager.register_tool(function)

    async def handle_prompt_command(
        self, command: NotionCRUDEnginePromptCommand
    ) -> CommandResult:
        """Handle a prompt command following OpenAI tool usage pattern.

        Args:
            command: The prompt command to handle

        Returns:
            CommandResult: The result of the command execution
        """
        max_tool_calls = 7
        tool_call_count = 0
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
                    messages=current_context, tools=tools
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
                    return CommandResult(success=True, result=final_content)

                # 8. Process tool call
                for tool_call in response_message.tool_calls:
                    tool_call_obj = ToolCall(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=tool_call.function.arguments,
                    )
                    tool_call_count += 1
                    if tool_call_count > max_tool_calls:
                        self.context_manager.store_tool_call_result(
                            tool_call_id=tool_call_obj.id,
                            name=tool_call_obj.name,
                            content="The max number of tool calls has been reached. Please close these set of tool calls and inform the user. THIS CURRENT TOOL CALL WAS NOT SUCCESSFUL",
                        )
                        continue
                    if tool_call_obj.name == "update_task":
                        # patch task name and user name for confirmation request
                        temp = json.loads(tool_call.function.arguments)
                        if "notion_task_id" in temp:
                            temp["notion_task_id"] = self.temp_task_lookup[
                                temp["notion_task_id"]
                            ]["name"]
                        if "user_id" in temp:
                            # AI : Get user data using the new function
                            notion_id = notion_user_id_type(temp["task_in_charge"]) # AI : Type cast
                            user_data: UserData | None = get_user_from_notion_id(notion_id)
                            # AI : Use user name if found, otherwise keep original or indicate unknown
                            temp["task_in_charge"] = user_data.name if user_data else "Unknown User"
                        result = await self.message_bus.execute(
                            NotionCRUDEngineConfirmationCommand(
                                prompt=f"Updating task {temp}",
                                session_id=self.session_id,
                            )
                        )
                        if not result.result:
                            self.context_manager.store_tool_call_result(
                                tool_call_id=tool_call_obj.id,
                                name=tool_call_obj.name,
                                content="User purposefully denied tool execution, it was not successful, use this informormation in final response.",
                            )
                            continue

                    if tool_call_obj.name == "create_task":
                        # patch project name and user name for confirmation request
                        temp = json.loads(tool_call.function.arguments)
                        if "notion_project_id" in temp and temp["notion_project_id"]:
                            temp["notion_project_id"] = self.temp_project_lookup[
                                temp["notion_project_id"]
                            ]
                        # AI : Get user data using the new function
                        notion_id = notion_user_id_type(temp["user_id"]) # AI : Type cast
                        user_data: UserData | None = get_user_from_notion_id(notion_id)
                        # AI : Use user name if found, otherwise keep original or indicate unknown
                        temp["user_id"] = user_data.name if user_data else "Unknown User"

                        result = await self.message_bus.execute(
                            NotionCRUDEngineConfirmationCommand(
                                prompt=f"Creating task {temp}",
                                session_id=self.session_id,
                            )
                        )
                        if not result.result:
                            self.context_manager.store_tool_call_result(
                                tool_call_id=tool_call_obj.id,
                                name=tool_call_obj.name,
                                content="User purposefully denied tool execution, it was not successful, use this informormation in final response.",
                            )
                            continue

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
                    if tool_call_obj.name == "get_active_projects":
                        self.temp_project_lookup = result
                    elif tool_call_obj.name == "get_active_tasks":
                        self.temp_task_lookup = result
        except Exception as e:
            print(e)
            return CommandResult(success=False, error=str(e))

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
