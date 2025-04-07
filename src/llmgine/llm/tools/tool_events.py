"""This module defines the different events that can be
emitted by the ToolManager.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List

from llmgine.messages.events import Event


@dataclass
class ToolManagerEvent(Event):
    tool_manager_id: str = field(default_factory=str)
    engine_id: str = field(default_factory=str)
    session_id: str = field(default_factory=str)


@dataclass
class ToolRegisterEvent(ToolManagerEvent):
    tool_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCompiledEvent(ToolManagerEvent):
    tool_compiled_list: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ToolExecuteResultEvent(ToolManagerEvent):
    execution_succeed: bool = False
    tool_info: Dict[str, Any] = field(default_factory=dict)
    tool_args: Dict[str, Any] = field(default_factory=dict)
    tool_result: str = ""
