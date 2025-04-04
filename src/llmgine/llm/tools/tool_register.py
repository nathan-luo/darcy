import re
import inspect
import asyncio
from typing import List, Dict, Union, Optional, Type

from llmgine.llm.tools.tool import Tool, Parameter, ToolFunction, AsyncToolFunction

class ToolRegister:
    def __init__(self, platform: Optional[str] = None):
        self.platform = platform or "notion"

    def register_tool(
        self, function: Union[ToolFunction, AsyncToolFunction]
    ) -> None:
        """Register a function as a tool.

        Args:
            function: The function to register

        Raises:
            ValueError: If the function has no description
        """
        
        # Get the name, description, parameters, and async status of the function
        name = function.__name__
        description = self._get_function_description(function)
        parameters = self._get_function_parameters(function)
        is_async = asyncio.iscoroutinefunction(function)

        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            function=function,
            is_async=is_async,
        )

        return name, tool

    def _get_function_description(self, function: Union[ToolFunction, AsyncToolFunction]) -> str:
        """Get the description of a function.

        Args:
            function: The function to get the description of

        Returns:
            The description of the function

        Raises:
            ValueError: If the function has no description
        """
        function_desc_pattern = r"^\s*(.+?)(?=\s*Args:|$)"
        desc_doc = re.search(function_desc_pattern, function.__doc__ or "", re.MULTILINE)

        if desc_doc:
            description = desc_doc.group(1).strip()
            description = " ".join(line.strip() for line in description.split("\n"))
        else:
            raise ValueError(f"Function '{function.__name__}' has no description provided")
        
        return description

    def _get_function_parameters(self, function: Union[ToolFunction, AsyncToolFunction]) -> List[Parameter]:
        """Get the parameters of a function.

        Args:
            function: The function to get the parameters of

        Returns:
            A list of function parameters, each with a name, type, and description

        Raises:
            ValueError: If the function has no parameters
        """


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

        return parameters

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