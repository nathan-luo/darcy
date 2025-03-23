"""Messages used by the LLM engine.

This module defines the commands and events used by the LLM engine.
"""

from llmgine.messages.commands import Command
from llmgine.messages.events import Event


class PromptCommand(Command):
    """Command to send a prompt to the LLM."""

    def __init__(self, prompt: str, use_tools: bool = True, conversation_id: str = "default"):
        """Initialize the prompt command.
        
        Args:
            prompt: The prompt to send to the LLM
            use_tools: Whether to allow tool usage
            conversation_id: The conversation identifier
        """
        self.prompt = prompt
        self.use_tools = use_tools
        self.conversation_id = conversation_id


class SystemPromptCommand(Command):
    """Command to set the system prompt for a conversation."""

    def __init__(self, system_prompt: str, conversation_id: str = "default"):
        """Initialize the system prompt command.
        
        Args:
            system_prompt: The system prompt to set
            conversation_id: The conversation identifier
        """
        self.system_prompt = system_prompt
        self.conversation_id = conversation_id


class ClearHistoryCommand(Command):
    """Command to clear the conversation history."""

    def __init__(self, conversation_id: str = "default"):
        """Initialize the clear history command.
        
        Args:
            conversation_id: The conversation identifier
        """
        self.conversation_id = conversation_id


class LLMResponseEvent(Event):
    """Event emitted when the LLM responds."""

    def __init__(self, prompt: str, response: str, conversation_id: str = "default"):
        """Initialize the LLM response event.
        
        Args:
            prompt: The prompt that was sent
            response: The response from the LLM
            conversation_id: The conversation identifier
        """
        super().__init__()
        self.prompt = prompt
        self.response = response
        self.conversation_id = conversation_id
