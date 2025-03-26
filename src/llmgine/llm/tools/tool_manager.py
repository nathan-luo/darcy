"""Tool management and execution for LLMs.

This module provides a way to register, describe, and execute tools
that can be called by language models.
"""

import asyncio
import inspect
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, Union
import uuid

from llmgine.messages.events import ToolCall

logger = logging.getLogger(__name__)

# Type for tool function
ToolFunction = Callable[..., Any]
AsyncToolFunction = Callable[..., "asyncio.Future[Any]"]


@dataclass
class ToolDescription:
    """Description of a tool that can be used by an LLM.
    
    Attributes:
        name: The name of the tool
        description: A description of what the tool does
        parameters: JSON schema for the tool parameters
        function: The function to call when the tool is invoked
        is_async: Whether the function is asynchronous
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Union[ToolFunction, AsyncToolFunction]
    is_async: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to OpenAI-compatible tool description format.
        
        Returns:
            Dict representation in OpenAI format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class ToolManager:
    """Manages tool registration and execution."""

    def __init__(self):
        """Initialize the tool manager."""
        self.tools: Dict[str, ToolDescription] = {}

    def register_tool(self, 
                     function: Union[ToolFunction, AsyncToolFunction],
                     name: Optional[str] = None,
                     description: Optional[str] = None) -> None:
        """Register a function as a tool.
        
        Args:
            function: The function to register
            name: Optional name for the tool (defaults to function name)
            description: Optional description (defaults to function docstring)
        """
        name = name or function.__name__
        description = description or (function.__doc__ or "No description provided")

        # Extract parameters from function signature
        sig = inspect.signature(function)
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for param_name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                # Try to convert type annotation to JSON schema type
                param_type = self._annotation_to_json_type(param.annotation)
                parameters["properties"][param_name] = {"type": param_type}

                # Add to required list if no default value
                if param.default is inspect.Parameter.empty:
                    parameters["required"].append(param_name)
            else:
                # Default to string if no type annotation
                parameters["properties"][param_name] = {"type": "string"}
                if param.default is inspect.Parameter.empty:
                    parameters["required"].append(param_name)

        is_async = asyncio.iscoroutinefunction(function)

        tool_desc = ToolDescription(
            name=name,
            description=description,
            parameters=parameters,
            function=function,
            is_async=is_async
        )

        self.tools[name] = tool_desc
        logger.info(f"Registered tool: {name}")

    def get_tool_descriptions(self) -> List[Dict[str, Any]]:
        """Get descriptions of all registered tools in OpenAI format.
        
        Returns:
            A list of tool descriptions in OpenAI function calling format
        """
        return [tool.to_dict() for tool in self.tools.values()]

    async def execute_tool_call(self, tool_call: ToolCall) -> Any:
        """Execute a tool from a ToolCall object.
        
        Args:
            tool_call: The tool call to execute
            
        Returns:
            The result of the tool execution
            
        Raises:
            ValueError: If the tool is not found
        """
        tool_name = tool_call.name
        
        try:
            # Parse arguments
            arguments = json.loads(tool_call.arguments)
            return await self.execute_tool(tool_name, arguments)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON arguments for tool {tool_name}: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool with the given arguments.
        
        Args:
            tool_name: The name of the tool to execute
            arguments: The arguments to pass to the tool
            
        Returns:
            The result of the tool execution
            
        Raises:
            ValueError: If the tool is not found
        """
        if tool_name not in self.tools:
            error_msg = f"Tool not found: {tool_name}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        tool = self.tools[tool_name]

        try:
            # Call the tool function with the provided arguments
            if tool.is_async:
                result = await tool.function(**arguments)
            else:
                result = tool.function(**arguments)

            return result
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}: {e}")
            raise

    def _annotation_to_json_type(self, annotation: Type) -> str:
        """Convert a Python type annotation to a JSON schema type.
        
        Args:
            annotation: The type annotation to convert
            
        Returns:
            A JSON schema type string
        """
        # Simple mapping of Python types to JSON schema types
        if annotation is str:
            return "string"
        elif annotation is int:
            return "integer"
        elif annotation is float:
            return "number"
        elif annotation is bool:
            return "boolean"
        elif annotation is list or annotation is List:
            return "array"
        elif annotation is dict or annotation is Dict:
            return "object"
        else:
            # Default to string for complex types
            return "string"


# Create a singleton instance
default_tool_manager = ToolManager()