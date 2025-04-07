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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engines.tool_chat_engine import ToolChatEngine
from engines.tool_engine import ToolEngine, ToolEnginePromptCommand
from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
from llmgine.bus.bus import MessageBus
from llmgine.observability.events import LogLevel
from programs.function_chat import get_weather

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


async def use_engine(command: ToolEnginePromptCommand):
    """Create and configure the engine."""
    bus = MessageBus()

    async with bus.create_session() as session:
        engine = ToolEngine(
            session_id=session.session_id,
            system_prompt="You are a helpful assistant that can use tools to answer questions.",
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        await engine.register_tool(get_weather)
        result = await engine.handle_prompt_command(command)
    return result


async def main():
    app = ApplicationBootstrap(FunctionEngineSessionConfig())
    await app.bootstrap()
    result1 = asyncio.create_task(
        use_engine(ToolEnginePromptCommand(prompt="What is the weather in Tokyo?"))
    )
    result2 = asyncio.create_task(
        use_engine(ToolEnginePromptCommand(prompt="What is the weather in SF?"))
    )
    result3 = asyncio.create_task(
        use_engine(ToolEnginePromptCommand(prompt="What is the weather in NY?"))
    )
    results = await asyncio.gather(result1, result2, result3)
    for result in results:
        print(result.result)


if __name__ == "__main__":
    asyncio.run(main())
