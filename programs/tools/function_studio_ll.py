"""Function Studio for managing LLM tools and engine."""

import asyncio
from typing import Optional, List, Dict, Any

from llmgine.llm.tools import ToolManager
from llmgine.llm.engine import LLMEngine
from llmgine.bus import MessageBus
from llmgine.observability.bus import ObservabilityBus
from llmgine.llm.tools.weather import get_weather
from llmgine.llm.engine.messages import PromptCommand
from llmgine.llm.providers import OpenAIProvider

class FunctionStudio:
    """A studio for managing LLM tools and function calling."""
    
    def __init__(self, openai_api_key: str):
        """Initialize the Function Studio.
        
        Args:
            openai_api_key: OpenAI API key
        """
        # Initialize message bus
        self.message_bus = MessageBus()
        
        # Initialize observability bus
        self.obs_bus = ObservabilityBus()
        
        # Initialize tool manager and register tools
        self.tool_manager = ToolManager()
        
        # Register weather tool
        self.tool_manager.register_tool(get_weather)
        
        # Initialize LLM engine
        self.llm_engine = LLMEngine(
            message_bus=self.message_bus,
            obs_bus=self.obs_bus
        )
        
        # Register OpenAI provider
        openai_provider = OpenAIProvider(api_key=openai_api_key)
        self.llm_engine.llm_manager.register_provider("openai", openai_provider)
        self.llm_engine.llm_manager.set_default_provider("openai")
        
        # Set the tool manager
        self.llm_engine.tool_manager = self.tool_manager
        
    async def start(self):
        """Start the studio."""
        await self.message_bus.start()
        await self.obs_bus.start()
        
    async def stop(self):
        """Stop the studio."""
        await self.message_bus.stop()
        await self.obs_bus.stop()
        
    async def query(self, prompt: str) -> str:
        """Send a query to the LLM.
        
        Args:
            prompt: The user's prompt
            
        Returns:
            The LLM's response
        """
        # Create and send PromptCommand with tools enabled
        command = PromptCommand(prompt=prompt, use_tools=True)
        result = await self.llm_engine._handle_prompt(command)
        
        # Return response content
        if result.success and result.result:
            return result.result.content or ""
        else:
            raise RuntimeError(f"Query failed: {result.error}")
