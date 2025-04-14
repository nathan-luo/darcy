import asyncio
from dataclasses import dataclass
from typing import List, Dict
import uuid
from rich.table import Table
from rich.console import Console

from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.llm.providers.response import OpenAIManager
from llmgine.bus.bus import MessageBus


@dataclass
class functionStudioConfig:
    """
    Configuration for Function Studio.
    """
    id: str
    model: str
    tools: List[str]
    history: List[Dict]

@dataclass
class FakeToolCall:
    name: str
    arguments: Dict

async def set_up_tool_manager(engine_id: str, session_id: str, model: str, tools: List[str]):
    """
    Set up a tool manager for a given model and tools.
    """
    tool_manager = ToolManager(engine_id=engine_id, session_id=session_id, llm_model_name=model)
    await tool_manager.register_tools(tools)
    return tool_manager

def set_up_llm_manager(engine_id: str, session_id: str):
    """
    Set up an LLM manager for a given model.
    """
    llm_manager = OpenAIManager(engine_id=engine_id, session_id=session_id)
    return llm_manager

def create_table(test_table: Dict[str, List[FakeToolCall]]):
    """
    Create a table to display the test results.
    """
    table = Table(title="Function Studio Tests")
    table.add_column("History ID", justify="right")
    table.add_column("Output", justify="right")
    for test_id, output in test_table.items():
        table.add_row(test_id, str(output))
    return table

async def function_studio(history: List[Dict]=[], model: str="openai", tools: List[str]=["notion"]):
    """
    Function Studio is a tool that allows you to perform a test run of function registration,
    history passing, and tool calling.
    """

    # Fake ids
    engine_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    # Set up managers
    tool_manager = await set_up_tool_manager(engine_id=engine_id, session_id=session_id, model=model, tools=tools)
    llm_manager = set_up_llm_manager(engine_id=engine_id, session_id=session_id)

    # Retrieve tools and generate llm response
    tools = await tool_manager.get_tools()
    llm_response = await llm_manager.generate(context=history, tools=tools)

    # Extract the first choice's message object
    response_message = llm_response.raw.choices[0].message
    output: List[FakeToolCall] = []
    for tool_call in response_message.tool_calls:
        output.append(FakeToolCall(name=tool_call.function.name, 
                                   arguments=tool_call.function.arguments))

    return output

async def main(tests: List[functionStudioConfig]):
    """
    Main function for Function Studio.
    """
    message_bus = MessageBus()
    await message_bus.start()

    test_table = {}
    for test in tests:
        output = await function_studio(test.history, test.model, test.tools)
        test_table[test.id] = output
    await message_bus.stop()

    # create a table to display the test results
    table = create_table(test_table)
    console = Console()
    console.print(table)

asyncio.run(main([functionStudioConfig(id="User defined id 1", 
                           model="openai", 
                           tools=["notion"], 
                           history=[{"role": "system", "content": "You're a helpful assistant that can help me with my tasks."},
                                    {"role": "user", "content": "get me the Yiwen's notion tasks"}]),
                           ]))