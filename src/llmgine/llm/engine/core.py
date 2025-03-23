"""Core LLM Engine for handling interactions with language models."""

import json
import logging
from typing import Any, Dict, List, Optional, Protocol, Type

from llmgine.bus import MessageBus
from llmgine.llm.context import ContextManager
from llmgine.llm.engine.messages import (
    ClearHistoryCommand,
    LLMResponseEvent,
    PromptCommand,
    SystemPromptCommand,
)
from llmgine.llm.providers import LLMManager
from llmgine.llm.tools import ToolCallEvent, ToolManager, ToolResultEvent
from llmgine.messages.commands import CommandResult

logger = logging.getLogger(__name__)


class LLMEngine:
    """Engine for handling interactions with language models."""

    def __init__(
        self,
        message_bus: MessageBus,
        llm_manager: LLMManager,
        context_manager: ContextManager,
        tool_manager: Optional[ToolManager] = None,
    ):
        """Initialize the LLM engine.

        Args:
            message_bus: The message bus for command and event handling
            llm_manager: The manager for LLM providers
            context_manager: The manager for conversation context
            tool_manager: Optional tool manager for function calling
        """
        self.message_bus = message_bus
        self.llm_manager = llm_manager
        self.context_manager = context_manager
        self.tool_manager = tool_manager or ToolManager()

        # Note: Command handlers are now registered externally via bootstrap

    async def _handle_system_prompt(self, command: SystemPromptCommand) -> CommandResult:
        """Handle a system prompt command.

        Args:
            command: The system prompt command

        Returns:
            The result of handling the command
        """
        system_prompt = command.system_prompt
        conversation_id = command.conversation_id

        try:
            # Get current context
            context = self.context_manager.get_context(conversation_id)

            # Remove any existing system prompts
            context = [msg for msg in context if msg.get("role") != "system"]

            # Add system prompt at the beginning
            system_message = {"role": "system", "content": system_prompt}
            self.context_manager.clear_context(conversation_id)
            self.context_manager.add_message(conversation_id, system_message)

            # Add back the rest of the messages
            for message in context:
                self.context_manager.add_message(conversation_id, message)

            logger.info(f"Added system prompt to conversation {conversation_id}")

            return CommandResult(success=True, result="System prompt set successfully")

        except Exception as e:
            error_msg = f"Error setting system prompt: {e!s}"
            logger.exception(error_msg)
            return CommandResult(success=False, error=error_msg)

    async def _handle_clear_history(self, command: ClearHistoryCommand) -> CommandResult:
        """Handle a clear history command.

        Args:
            command: The clear history command

        Returns:
            The result of handling the command
        """
        conversation_id = command.conversation_id

        try:
            self.context_manager.clear_context(conversation_id)
            logger.info(f"Cleared conversation history for {conversation_id}")

            return CommandResult(success=True, result="Conversation history cleared")

        except Exception as e:
            error_msg = f"Error clearing conversation history: {e!s}"
            logger.exception(error_msg)
            return CommandResult(success=False, error=error_msg)

    async def _handle_prompt(self, command: PromptCommand) -> CommandResult:
        """Handle a prompt command.

        Args:
            command: The prompt command

        Returns:
            The result of handling the command
        """
        prompt = command.prompt
        conversation_id = command.conversation_id

        # Add user message to context
        user_message = {"role": "user", "content": prompt}
        self.context_manager.add_message(conversation_id, user_message)

        # Get the conversation context
        context = self.context_manager.get_context(conversation_id)

        # Get tool descriptions if enabled
        tools = None
        if command.use_tools and self.tool_manager and self.tool_manager.tools:
            tools = self.tool_manager.get_tool_descriptions()

        try:
            # Generate response using the LLM manager
            llm_response = await self.llm_manager.generate(
                prompt=prompt,
                context=context,
                # Additional parameters could be passed here
            )

            # Add assistant response to context
            assistant_message = {"role": "assistant", "content": llm_response.content}
            self.context_manager.add_message(conversation_id, assistant_message)

            # Extract function calls if any (placeholder for actual integration)
            # In a real implementation, function calls would be extracted from the LLM response
            function_calls = llm_response.tool_calls

            # Publish response event
            await self.message_bus.publish(
                LLMResponseEvent(prompt, llm_response.content, conversation_id)
            )

            # Handle function calls if present
            if function_calls:
                await self._process_tool_calls(function_calls, conversation_id)

            return CommandResult(success=True, result=llm_response.content)

        except Exception as e:
            error_msg = f"Error processing prompt: {e!s}"
            logger.exception(error_msg)
            return CommandResult(success=False, error=error_msg)

    async def _process_tool_calls(
        self, tool_calls: List[Dict[str, Any]], conversation_id: str
    ) -> None:
        """Process tool calls from the LLM response.

        Args:
            tool_calls: The tool calls to process
            conversation_id: The conversation identifier
        """
        for call in tool_calls:
            tool_name = call.get("name")
            arguments = json.loads(call.get("arguments", "{}"))

            # Publish tool call event
            tool_call_event = ToolCallEvent(tool_name, arguments)
            await self.message_bus.publish(tool_call_event)

            # Execute tool and get result
            try:
                result = await self.tool_manager.execute_tool(tool_name, arguments)

                # Add tool result to context
                tool_message = {
                    "role": "tool",
                    "tool_call_id": str(tool_call_event.id),
                    "name": tool_name,
                    "content": str(result),
                }
                self.context_manager.add_message(conversation_id, tool_message)

                # Publish tool result event
                await self.message_bus.publish(
                    ToolResultEvent(tool_name, arguments, result)
                )

            except Exception as e:
                error_msg = f"Error executing tool {tool_name}: {e!s}"
                logger.exception(error_msg)

                # Add error to context
                error_message = {
                    "role": "tool",
                    "tool_call_id": str(tool_call_event.id),
                    "name": tool_name,
                    "content": f"ERROR: {error_msg}",
                }
                self.context_manager.add_message(conversation_id, error_message)

                # Publish tool result event with error
                await self.message_bus.publish(
                    ToolResultEvent(tool_name, arguments, None, error=error_msg)
                )

    async def _handle_tool_call_event(self, event: ToolCallEvent) -> CommandResult:
        """Handle a tool call event (for testing and debugging).

        Args:
            event: The tool call event

        Returns:
            Command result
        """
        try:
            result = await self.tool_manager.execute_tool(
                event.tool_name, event.arguments
            )
            return CommandResult(success=True, result=result)
        except Exception as e:
            error_msg = f"Error executing tool {event.tool_name}: {e!s}"
            logger.exception(error_msg)
            return CommandResult(success=False, error=error_msg)
