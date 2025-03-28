from dataclasses import dataclass
from typing import Any, Dict, Union, Callable

# Type for tool function
ToolFunction = Callable[..., Any]
AsyncToolFunction = Callable[..., "asyncio.Future[Any]"]

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