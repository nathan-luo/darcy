"""Tool management and execution for LLMs.

This module provides a way to register, describe, and execute tools
that can be called by language models.
"""

import asyncio
import inspect
import json
import re
from typing import Any, Dict, List, Optional, Type, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from llmgine.llm.engine.core import LLMEngine
    from llmgine.bus.bus import MessageBus

from llmgine.llm.tools.tool import Tool, ToolFunction, AsyncToolFunction
from llmgine.messages.events import ToolCall


class ToolManager:
    """Manages tool registration and execution."""

    def __init__(self, 
                 engine: Optional['LLMEngine'] = None, 
                 message_bus: Optional['MessageBus'] = None, 
                 llm_model_name: Optional[str] = None):
        """Initialize the tool manager."""
        self.tools: Dict[str, Tool] = {}
        self.engine = engine
        self.message_bus = message_bus
        self.tool_parser = self._get_parser(llm_model_name)


    def _get_parser(self, llm_model_name: Optional[str] = None):
        """Get the appropriate tool parser based on the LLM model name."""
        if llm_model_name == "openai":
            tool_parser = OpenAIToolParser()
        elif llm_model_name == "claude":
            tool_parser = ClaudeToolParser()
        elif llm_model_name == "deepseek":
            tool_parser = DeepSeekToolParser()
        else:
            tool_parser = OpenAIToolParser()
        return tool_parser

    def register_tool(self, function: Union[ToolFunction, AsyncToolFunction]) -> None:
        """Register a function as a tool.
        
        Args:
            function: The function to register

        Raises:
            ValueError: If the function has no description
        """
        name = function.__name__
        
        function_desc_pattern = r'^\s*(.+?)(?=\s*Args:|$)'
        desc_doc = re.search(function_desc_pattern, function.__doc__ or "", re.MULTILINE)
        if desc_doc:
            description = desc_doc.group(1).strip()
            description = ' '.join(line.strip() for line in description.split('\n'))
        else:
            raise ValueError(f"Function '{name}' has no description provided")

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
                param_required = True

            # If the parameter has a description in the Args section, use it
            if param_name in param_dict:
                param_desc = param_dict[param_name]
            else:
                raise ValueError(f"Parameter '{param_name}' has no description in the Args section")

            parameters.append(Parameter(
                name=param_name,
                description=param_desc,
                type=param_type,
                required=param_required
            ))

        is_async = asyncio.iscoroutinefunction(function)

        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            function=function,
            is_async=is_async
        )

        self.tools[name] = tool

    def get_tools(self) -> List[Tool]:
        """Get all registered tools.
        
        Returns:
            A list of tools in the registered model's format
        """
        return [self.tool_parser.parse_tool(tool) for tool in self.tools.values()]

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