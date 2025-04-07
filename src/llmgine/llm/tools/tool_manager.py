"""Tool management and execution for LLMs.

This module provides a way to register, describe, and execute tools
that can be called by language models.
"""

import asyncio
import inspect
import json
import re
import uuid
from typing import Any, Dict, List, Optional, Type, Union

from llmgine.bus.bus import MessageBus
from llmgine.llm.engine.core import LLMEngine
from llmgine.llm.tools.tool import Tool, Parameter, ToolFunction, AsyncToolFunction
from llmgine.llm.tools.tool_parser import (
    OpenAIToolParser,
    ClaudeToolParser,
    DeepSeekToolParser,
)
from llmgine.messages.events import ToolCall
from llmgine.llm.tools.tool_events import (
    ToolRegisterEvent,
    ToolCompiledEvent,
    ToolExecuteResultEvent,
)


class ToolManager:
    """Manages tool registration and execution."""

    def __init__(
        self, engine_id: str, session_id: str, llm_model_name: Optional[str] = None
    ):
        """Initialize the tool manager."""
        self.tool_manager_id = str(uuid.uuid4())
        self.tools: Dict[str, Tool] = {}
        self.engine_id = engine_id
        self.session_id = session_id
        self.message_bus = MessageBus()
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

    async def register_tool(
        self, function: Union[ToolFunction, AsyncToolFunction]
    ) -> None:
        """Register a function as a tool.

        Args:
            function: The function to register

        Raises:
            ValueError: If the function has no description
        """
        name = function.__name__

        function_desc_pattern = r"^\s*(.+?)(?=\s*Args:|$)"
        desc_doc = re.search(function_desc_pattern, function.__doc__ or "", re.MULTILINE)
        if desc_doc:
            description = desc_doc.group(1).strip()
            description = " ".join(line.strip() for line in description.split("\n"))
        else:
            raise ValueError(f"Function '{name}' has no description provided")

        # Extract parameters from function signature
        sig = inspect.signature(function)
        parameters: List[Parameter] = []
        param_dict = {}

        # Find the Args section
        args_match = re.search(
            r"Args:(.*?)(?:Returns:|Raises:|$)", function.__doc__ or "", re.DOTALL
        )
        if args_match:
            args_section = args_match.group(1).strip()

            # Pattern to match parameter documentation
            # Matches both single-line and multi-line parameter descriptions
            param_pattern = r"(\w+):\s*((?:(?!\w+:).+?\n?)+)"

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
            else:
                raise ValueError(
                    f"Parameter '{param_name}' has no description in the Args section"
                )

            parameters.append(
                Parameter(
                    name=param_name,
                    description=param_desc,
                    type=param_type,
                    required=param_required,
                )
            )

        is_async = asyncio.iscoroutinefunction(function)

        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            function=function,
            is_async=is_async,
        )

        # Publish the tool registration event
        await self.message_bus.publish(
            ToolRegisterEvent(
                tool_manager_id=self.tool_manager_id,
                session_id=self.session_id,
                engine_id=self.engine_id,
                tool_info=tool.to_dict(),
            )
        )

        self.tools[name] = tool

    async def get_tools(self) -> List[Tool]:
        """Get all registered tools.

        Returns:
            A list of tools in the registered model's format
        """
        # Publish the tool compilation event
        await self.message_bus.publish(
            ToolCompiledEvent(
                tool_manager_id=self.tool_manager_id,
                session_id=self.session_id,
                engine_id=self.engine_id,
                tool_compiled_list=[tool.to_dict() for tool in self.tools.values()],
            )
        )

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
        print(f"i made it here executing tool {tool_name}")
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

            # Publish the tool execution event
            await self.message_bus.publish(
                ToolExecuteResultEvent(
                    tool_manager_id=self.tool_manager_id,
                    session_id=self.session_id,
                    engine_id=self.engine_id,
                    execution_succeed=True,
                    tool_info=tool.to_dict(),
                    tool_args=arguments,
                    tool_result=str(result),
                )
            )
            return result
        except Exception as e:
            # Publish the tool execution event
            await self.message_bus.publish(
                ToolExecuteResultEvent(
                    tool_manager_id=self.tool_manager_id,
                    session_id=self.session_id,
                    engine_id=self.engine_id,
                    execution_succeed=False,
                    tool_info=tool.to_dict(),
                    tool_args=arguments,
                    tool_result=str(e),
                )
            )
            raise e

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
