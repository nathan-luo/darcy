from dataclasses import dataclass
from typing import Any, Dict, Union, Callable, List

# Type for tool function
ToolFunction = Callable[..., Any]
AsyncToolFunction = Callable[..., "asyncio.Future[Any]"]

@dataclass
class Parameter:
    """A parameter for a tool.
    
    Attributes:
        name: The name of the parameter
        description: A description of the parameter
        type: The type of the parameter
        required: Whether the parameter is required
    """
    name: str
    description: str
    type: str
    required: bool = False

    def __init__(self, name: str, description: str, type: str, required: bool = False):
        self.name = name
        self.description = description or ""
        self.type = type
        self.required = required



@dataclass
class Tool:
    """Contains all information about a tool.
    
    Attributes:
        name: The name of the tool
        description: A description of what the tool does
        parameters: JSON schema for the tool parameters
        function: The function to call when the tool is invoked
        is_async: Whether the function is asynchronous
    """
    name: str
    description: str
    parameters: List[Parameter]
    function: Union[ToolFunction, AsyncToolFunction]
    is_async: bool = False
