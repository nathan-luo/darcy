
from dataclasses import dataclass
from typing import Dict, Any, List

from llmgine.messages.events import Event


@dataclass
class ToolManagerEvent(Event):
    tool_manager_id: str
    engine_id: str

@dataclass
class ToolRegisterEvent(ToolManagerEvent):
    tool_info: Dict[str, Any]

@dataclass
class ToolCompiledEvent(ToolManagerEvent):
    tool_compiled_list: List[Dict[str, Any]]

@dataclass
class ToolExecuteResultEvent(ToolManagerEvent):
    execution_succeed: bool
    tool_info: Dict[str, Any]
    tool_args: Dict[str, Any]
    tool_result: str
