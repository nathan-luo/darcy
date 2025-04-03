import asyncio
import dotenv
import os
import json
import uuid
import argparse
import sys
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from engines.tool_chat_engine import ToolChatEngine
from engines.tool_engine import ToolEngine
from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
from llmgine.bus.bus import MessageBus
from llmgine.observability.events import LogLevel
from programs.function_chat import get_current_weather

dotenv.load_dotenv()

@dataclass
class FunctionEngineSessionConfig(ApplicationConfig):
    """Configuration for the Function Engine Session application."""

    # Application-specific configuration
    name: str = "Function Engine Session"
    description: str = "A simple chat application with function calling capabilities"

    enable_tracing: bool = False
    enable_console_handler: bool = False

    # OpenAI configuration
    model: str = "gpt-4o-mini"

async def use_engine():
    """Create and configure the engine."""
    bus = MessageBus()
    with bus.create_session("function_engine_session") as session:
        engine = ToolEngine(
            session_id=session.session_id,
            system_prompt="You are a helpful assistant that can use tools to answer questions.",
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        engine.register_tool()
    return engine

async def create_and_execute_engine()
    # Tool engine configuration
    
