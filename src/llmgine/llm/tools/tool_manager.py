"""Tool management and execution for LLMs.

This module provides a way to register, describe, and execute tools
that can be called by language models.
"""

import asyncio
import inspect
import json
import logging
import re
from typing import Any, Dict, List, Optional, Type, Union

from llmgine.llm.tools.tool import Tool, Parameter,ToolFunction, AsyncToolFunction
from llmgine.llm.tools.tool_parser import OpenAIToolParser, ClaudeToolParser, DeepSeekToolParser
from llmgine.messages.events import ToolCall

logger = logging.getLogger(__name__)

class ToolManager:
    """Manages tool registration and execution."""

    def __init__(self):
        """Initialize the tool manager."""
        self.tools: Dict[str, Tool] = {}

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
        function_desc_pattern = r'^\s*(.+?)(?=\s*Args:|$)'
        desc_doc = re.search(function_desc_pattern, function.__doc__ or "", re.MULTILINE)
        if not description:
            if desc_doc:
                description = desc_doc.group(1).strip()
                description = ' '.join(line.strip() for line in description.split('\n'))
            else:
                description = "No description provided"

        # Extract parameters from function signature
        sig = inspect.signature(function)
        parameters: List[Parameter] = []
        param_dict = {}

        # Find the Args section
        args_match = re.search(r'Args:(.*?)(?:Returns:|Raises:|$)', function.__doc__ or "", re.DOTALL)
        if args_match:
            args_section = args_match.group(1).strip()
    
            # Pattern to match parameter documentation
            # Matches both single-line and multi-line parameter descriptions
            param_pattern = r'(\w+):\s*((?:(?!\w+:).+?\n?)+)'

            # Find all parameters in the Args section
            for match in re.finditer(param_pattern, args_section, re.MULTILINE):
                param_name = match.group(1)
                param_desc = match.group(2).strip()

                param_dict[param_name] = param_desc
            
        for param_name, param in sig.parameters.items():
            param_type = "string"
            param_required = False
            param_desc = f"Parameter: {param_name}"

            if param.annotation != inspect.Parameter.empty:
                # Convert type annotation to JSON schema type
                param_type = self._annotation_to_json_type(param.annotation)

            # Add to required list if no default value
            if param.default is inspect.Parameter.empty:
                param_required = True

            # If the parameter has a description in the Args section, use it
            if param_name in param_dict:
                param_desc = param_dict[param_name]

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
        logger.info(f"Registered tool: {name}")

    def get_tool_descriptions(self, llm_model_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get descriptions of all registered tools in the given model's format.
        
        Args:
            llm_model_name: The name of the LLM model to get the tools for, defaults to "openai"

        Returns:
            A list of tool descriptions in the given model's format
        """
        if llm_model_name == "openai":
            parser = OpenAIToolParser()
        elif llm_model_name == "claude":
            parser = ClaudeToolParser()
        elif llm_model_name == "deepseek":
            parser = DeepSeekToolParser()
        else:
            parser = OpenAIToolParser()

        return [parser.parse_tool(tool) for tool in self.tools.values()]

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