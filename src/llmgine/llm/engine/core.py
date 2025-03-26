"""Core LLM Engine for handling interactions with language models."""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Protocol, Type, Union

from llmgine.bus import MessageBus
from llmgine.llm.context import InMemoryContextManager
from llmgine.llm.engine.messages import (
    ClearHistoryCommand, 
    LLMResponseEvent,
    PromptCommand, 
    SystemPromptCommand,
    ToolCallEvent,
    ToolResultEvent,
)
from llmgine.llm.providers import DefaultLLMManager, create_tool_call
from llmgine.llm.tools import default_tool_manager
from llmgine.messages.commands import CommandResult
from llmgine.messages.events import LLMResponse, ToolCall
from llmgine.observability import ObservabilityBus

logger = logging.getLogger(__name__)


class LLMEngine:
    """Engine for handling interactions with language models.
    
    This class is the main coordinator of LLM interactions, managing:
    1. Context and history management
    2. LLM provider selection and communication
    3. Tool/function calling
    4. Event publishing
    """

    def __init__(
        self,
        message_bus: MessageBus,
        obs_bus: ObservabilityBus,
    ):
        """Initialize the LLM engine.

        Args:
            message_bus: The message bus for command and event handling
            obs_bus: The observability bus for logging and tracing
        """
        self.message_bus = message_bus
        self.obs_bus = obs_bus
        
        # Create tightly coupled components
        self.llm_manager = DefaultLLMManager()
        self.context_manager = InMemoryContextManager()
        self.tool_manager = default_tool_manager
        
        # Register command handlers
        self._register_command_handlers()
        
    def _register_command_handlers(self) -> None:
        """Register command handlers with the message bus."""
        self.message_bus.register_command_handler(
            PromptCommand, self._handle_prompt
        )
        self.message_bus.register_command_handler(
            SystemPromptCommand, self._handle_system_prompt
        )
        self.message_bus.register_command_handler(
            ClearHistoryCommand, self._handle_clear_history
        )

    async def _handle_system_prompt(self, command: SystemPromptCommand) -> CommandResult:
        """Handle a system prompt command.

        Args:
            command: The system prompt command

        Returns:
            The result of handling the command
        """
        system_prompt = command.system_prompt
        conversation_id = command.conversation_id

        trace_context = {"conversation_id": conversation_id}
        span = self.obs_bus.start_trace("system_prompt", trace_context)
        
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

            self.obs_bus.log(
                "info", 
                f"Added system prompt to conversation {conversation_id}"
            )
            self.obs_bus.end_trace(span, "success")

            return CommandResult(
                command_id=command.id,
                success=True, 
                result="System prompt set successfully"
            )

        except Exception as e:
            error_msg = f"Error setting system prompt: {e!s}"
            logger.exception(error_msg)
            
            self.obs_bus.log("error", error_msg, trace_context)
            self.obs_bus.end_trace(span, "error")
                
            return CommandResult(
                command_id=command.id,
                success=False, 
                error=error_msg
            )

    async def _handle_clear_history(self, command: ClearHistoryCommand) -> CommandResult:
        """Handle a clear history command.

        Args:
            command: The clear history command

        Returns:
            The result of handling the command
        """
        conversation_id = command.conversation_id
        trace_context = {"conversation_id": conversation_id}
        span = self.obs_bus.start_trace("clear_history", trace_context)

        try:
            self.context_manager.clear_context(conversation_id)
            
            self.obs_bus.log(
                "info", 
                f"Cleared conversation history for {conversation_id}"
            )
            self.obs_bus.end_trace(span, "success")

            return CommandResult(
                command_id=command.id,
                success=True, 
                result="Conversation history cleared"
            )

        except Exception as e:
            error_msg = f"Error clearing conversation history: {e!s}"
            logger.exception(error_msg)
            
            self.obs_bus.log("error", error_msg, trace_context)
            self.obs_bus.end_trace(span, "error")
                
            return CommandResult(
                command_id=command.id,
                success=False, 
                error=error_msg
            )

    async def _handle_prompt(self, command: PromptCommand) -> CommandResult:
        """Handle a prompt command.

        Args:
            command: The prompt command

        Returns:
            The result of handling the command
        """
        prompt = command.prompt
        conversation_id = command.conversation_id
        trace_context = {
            "conversation_id": conversation_id,
            "provider": command.provider_id or "default",
            "model": command.model or "default"
        }
        span = self.obs_bus.start_trace("llm_prompt", trace_context)

        # Add user message to context
        user_message = {"role": "user", "content": prompt}
        self.context_manager.add_message(conversation_id, user_message)

        # Get the conversation context
        context = self.context_manager.get_context(conversation_id)

        # Get tool descriptions if enabled
        tools = None
        if command.use_tools and self.tool_manager.tools:
            tools = self.tool_manager.get_tool_descriptions()

        try:
            # Generate response using the LLM manager
            llm_response = await self.llm_manager.generate(
                prompt=prompt,
                context=context,
                provider_id=command.provider_id,
                temperature=command.temperature,
                max_tokens=command.max_tokens,
                model=command.model,
                tools=tools,
                **command.extra_params
            )
            
            # Update trace with model info
            if "metadata" not in span:
                span["metadata"] = {}
            span["metadata"]["model"] = llm_response.model
            if llm_response.usage:
                span["metadata"]["usage"] = llm_response.usage
            
            # Add assistant response to context
            assistant_message = {
                "role": "assistant",
            }
            
            # Add content if present (content is required by OpenAI except when tool_calls are present)
            if llm_response.content:
                assistant_message["content"] = llm_response.content
            elif not llm_response.tool_calls:
                assistant_message["content"] = ""
                
            # Add tool calls if present
            if llm_response.tool_calls:
                assistant_message["tool_calls"] = [
                    tc.to_dict() for tc in llm_response.tool_calls
                ]
                
            # Add the message to context
            self.context_manager.add_message(conversation_id, assistant_message)

            # Publish response event
            await self.message_bus.publish(
                LLMResponseEvent(prompt, llm_response, conversation_id)
            )

            # Handle tool calls if present
            if llm_response.has_tool_calls():
                await self._process_tool_calls(llm_response.tool_calls, conversation_id)

            # End the trace
            self.obs_bus.end_trace(span, "success")

            return CommandResult(
                command_id=command.id,
                success=True, 
                result=llm_response
            )

        except Exception as e:
            error_msg = f"Error processing prompt: {e!s}"
            logger.exception(error_msg)
            
            self.obs_bus.log("error", error_msg, trace_context)
            self.obs_bus.end_trace(span, "error")
                
            return CommandResult(
                command_id=command.id,
                success=False, 
                error=error_msg
            )

    async def _process_tool_calls(
        self, tool_calls: List[ToolCall], conversation_id: str
    ) -> None:
        """Process tool calls from the LLM response.

        Args:
            tool_calls: The tool calls to process
            conversation_id: The conversation identifier
        """
        for tool_call in tool_calls:
            # Publish tool call event
            tool_call_event = ToolCallEvent(tool_call, conversation_id)
            await self.message_bus.publish(tool_call_event)

            # Create trace for tool execution
            span = self.obs_bus.start_trace(
                "tool_execution", 
                {
                    "tool_name": tool_call.name,
                    "tool_id": tool_call.id,
                    "conversation_id": conversation_id
                }
            )

            # Execute tool and get result
            try:
                result = await self.tool_manager.execute_tool_call(tool_call)

                # Format the result properly to ensure it's a string
                result_str = str(result)
                if isinstance(result, (dict, list)):
                    try:
                        result_str = json.dumps(result)
                    except (TypeError, ValueError):
                        # Fallback to string representation
                        result_str = str(result)

                # Add tool result to context
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.name,
                    "content": result_str,
                }
                self.context_manager.add_message(conversation_id, tool_message)

                # Publish tool result event
                await self.message_bus.publish(
                    ToolResultEvent(tool_call, result, conversation_id=conversation_id)
                )
                
                # End trace with success
                self.obs_bus.end_trace(span, "success")

            except Exception as e:
                error_msg = f"Error executing tool {tool_call.name}: {e!s}"
                logger.exception(error_msg)

                # Add error to context
                error_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.name,
                    "content": f"ERROR: {error_msg}",
                }
                self.context_manager.add_message(conversation_id, error_message)

                # Publish tool result event with error
                await self.message_bus.publish(
                    ToolResultEvent(
                        tool_call, None, error=error_msg, 
                        conversation_id=conversation_id
                    )
                )
                
                # End trace with error
                self.obs_bus.end_trace(span, "error", error_details=str(e))