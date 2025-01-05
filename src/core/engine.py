from typing import Any, List, Optional, Union

from loguru import logger
from pydantic import BaseModel

from src.clients.anthropic_client import ClientAnthropic
from src.clients.openai_client import ClientOpenAI
from src.core.store import BasicChatContextStore, ContextStore
from src.tool_calling.tool_calling import (
    create_tools_lookup,
    create_tools_schema,
    execute_function,
    openai_function_wrapper,
    parse_functions,
)
from src.types.model_config import LLMInit
from src.utils.callbacks import CLICallback, DummieCallback


class AgentEngine():
    def __init__(
            self,
            initial_llm_config: LLMInit,
            agent_system_prompt: Optional[str] = None,
            initial_tools: Optional[List[callable]] = None,
            initial_prompts: Optional[List[str]] = None,
            callback: Any = DummieCallback()
    ):
        """_summary_

        Args:
            initial_llm_config (LLMInit): _description_
            agent_system_prompt (Optional[str], optional): _description_. Defaults to None.
            initial_tools (Optional[List[callable]], optional): _description_. Defaults to None.
            initial_prompts (Optional[List[str]], optional): _description_. Defaults to None.
            callback (Any, optional): _description_. Defaults to DummieCallback().
        """
        self.client = initial_llm_config.client
        self.model_name = initial_llm_config.model_name
        self.default_store = ContextStore()
        if agent_system_prompt:
            self.store.set_system_prompt(agent_system_prompt)
        else:
            self.store.set_system_prompt("You are a helpful assistant agent.")
        self.callback = callback
        self.tools = initial_tools if initial_tools else []
        self.prompts = initial_prompts if initial_prompts else []
        self.queue = []

    temp = ""
    state = "begin"

    def queue_prompt(self, prompt: str):
        self.queue.append(prompt)

    def get_user_input(self, message: str):
        input = self.callback.get(message)
        return input
    
    def start(self):
        while self.task_start == False:
            self.run()
    
    def run(self):
        if len(self.tools) == 0:
            raise ValueError("No tools added to the engine.")
        self.store.store_string("These are the tools you have:"
                                + create_tools_schema(self.tools), 
                                "assistant")
        with self.callback as loading:
            self.store.store_string("""
            You are in the getting task specification phase. Youl will 
            converse with the user to get the task specification. When
            you have enough information, you will proceed to the planning
            phase by calling the finish_task_definition function.
            """, "assistant")
            while self.state == "begin":
                input = self.input()
                self.store.store_string(input, "user")
                response = self.client.create_tool_completion(
                    self.model_name,
                    self.store.retrieve(),
                    tools=create_tools_schema([self.agent_tools[1]])
                )
                if response.stop_reason == "tool_calls":
                    self.store.store_tool_response(response)
                    self.process_tool_calls(response, create_tools_lookup(self.agent_tools), loading)
                else:
                    self.store.store_response(response, "assistant")
            self.store.store_string("""
            You are in the planning phase. You will plan the task based on the
            information you have gathered. When you have a plan, you will call
            the finish_planning function to proceed to the execution phase. Please
            proceed with the planning.
            """, "assistant")
            self.response = self.client.create_completion(
                self.model_name,
                self.store.retrieve()
            )
            self.store.store_response(self.response, "assistant")
            while self.state == "planning":
                input = self.input()
                self.store.store_string(input, "user")
                response = self.client.create_tool_completion(
                    self.model_name,
                    self.store.retrieve(),
                    tools=create_tools_schema([self.agent_tools[2]])
                )
                if response.stop_reason == "tool_calls":
                    self.store.store_tool_response(response)
                    self.process_tool_calls(response, create_tools_lookup(self.agent_tools), loading)
                else:
                    self.store.store_response(response, "assistant")
            self.store.store_string("""
            You are in the execution phase. You will execute the plan you have
            created. When you need help, additional input, or approval from the
            user, you will call the get_user_input function.
            """, "assistant")
            while self.state != "task_finished":
                # one complete round
                response = self.client.create_tool_completion(
                    self.model_name,
                    self.store.retrieve(),
                    tools=create_tools_schema(self.tools)
                )
                self.process_tool_calls(response, create_tools_lookup(self.tools), loading)
                temp_contex = self.store.retrieve()
                temp_contex.append({
                    "role": "assistant",
                    "content": "Explain what you just did and what was the result. Then\
                            explain what you're going to do next. If you need user input\
                            also write the question here."
                })
                response = self.client.create_completion(
                    self.model_name,
                    temp_contex)
                self.store.store_response(response, "assistant")
                if self.state == "user_input":
                    input = self.get_user_input()
                    self.store.store_string(input, "user")
                    response = self.client.create_tool_completion(
                        self.model_name,
                        self.store.retrieve(),
                        tools=create_tools_schema([self.agent_tools[3]])
                    )
                    if response.stop_reason == "tool_calls":
                        self.store.store_tool_response(response)
                        self.process_tool_calls(response, create_tools_lookup(self.agent_tools), loading)
                    else:
                        self.store.store_response(response, "assistant")

    def process_tool_calls(self, response, tool_lookup, callback):
        """
        Executes a list of function calls.
        """
        for call in parse_functions(response.tool_calls):
            # Execute the task
            callback.update_status(f"Executing {call.function.name} function...")
            try:
                result = f"{call.function.name}: {execute_function(call, tool_lookup)}"
            except Exception as e:
                result = f"Error executing {call.function.name} function: {str(e)}"
            # Store the result
            self.store.store_function_call_result(
                {"role": "tool",
                "tool_call_id": call.id,
                "name": call.function.name,
                "content": str(result)})
            self.callback.execute(
                content = str(result)[0:500],
                author = "Tool Result",
                style = "yellow"
            )
            logger.info(f"Tool call {call.function.name} executed\n{str(result)}")  

                                    
                    


class LinearAgentEngine():
    def __init__(self,
                 client: Union[ClientOpenAI, ClientAnthropic],
                model_name: str,
                system_prompt: Optional[str] = None,
                tools: Optional[list[callable]] = None,
                callback: Any = None):
        self.client = client
        self.model_name = model_name
        self.store = ContextStore()
        if system_prompt:
            self.store.set_system_prompt(system_prompt)
        else:
            self.store.set_system_prompt("You are a helpful assistant agent.")
        self.callback = callback
        self.agent_tools = []
        self.tools = tools if tools else []
        self.queue = []
        self.temp = ""
    
    def queue_prompt(self, prompt: str):
        """
        Queues a single instruction.
        """
        self.queue.append(prompt)

    def execute_prompt(self, prompt: str):
        """
        Executes a single instruction.
        """
        self.queue_prompt(prompt)
        self.run()
    
    def run(self):
        """
        Runs all instructions in the queue.
        """
        with self.callback.show_loading() as loading:
            while self.queue:
                # Get next prompt
                prompt = self.queue.pop(0)
                if prompt[0:15] == "(self-prompted)":
                    self.store.store_string(prompt, "assistant")
                else:
                    self.store.store_string(prompt, "user")
                response = self.client.create_tool_completion(
                    self.model_name,
                    self.store.retrieve(),
                    tools=create_tools_schema(self.tools)
                )
                # Create completion
                if response.stop_reason == "tool_calls":
                    if prompt[0:15] != "(self-prompted)": 
                        # If the prompt is not self-prompted, then the agent will explain what it is going to do
                        # before executing the tool calls
                        temp = self.store.retrieve()
                        temp.append({
                            "role": "assistant",
                            "content": f"Explain why I have called {response.tool_calls[0]} (and only called) in future tense..."
                        })
                        plan_response = self.client.create_completion(
                            self.model_name,
                            temp
                        )
                        self.store.store_response(plan_response, "assistant")
                        self.callback.print_message(
                            content = plan_response.content,
                            author = "Assistant",
                            style = "green"
                        )
                    # Handle tool calls
                    self.store.store_tool_response(response)
                    self.process_tool_calls(response, create_tools_lookup(self.tools), loading)
                    # Finished calling all functions from prompt
                    # Now send responses back to api, response can either finish the prompt, 
                    # or ask for more tool calls, if it asks for more tool calls, 
                    # it can only do so by adding a new prompt to the queue, and it also
                    # will explain what it did and why in the self_prompt function
                    response = self.client.create_tool_completion(
                        self.model_name,
                        self.store.retrieve(),
                        tools=create_tools_schema(self.agent_tools),
                    )
                    if (response.stop_reason == "tool_calls"):
                        # Agent wants to self prompt,
                        # the self prompt will be added to the queue
                        # and the agent will explain what it did and why
                        # in the self_prompt function
                        self.store.store_tool_response(response)
                        self.process_tool_calls(response, create_tools_lookup(self.agent_tools), loading)
                    else:
                        # Agent is finished this prompt
                        self.store.store_response(response, "assistant")
                else:
                    # No tool call required, simply continue
                    self.store.store_response(response, "assistant")

    def process_tool_calls(self, response, tool_lookup, callback):
        """
        Executes a list of function calls.
        """
        for call in parse_functions(response.tool_calls):
            # Execute the task
            callback.update_status(f"Executing {call.function.name} function...")
            try:
                result = execute_function(call, tool_lookup)
            except Exception as e:
                result = f"Error executing {call.function.name} function: {str(e)}"
            # Store the result
            self.store.store_function_call_result(
                {"role": "tool",
                "tool_call_id": call.id,
                "name": call.function.name,
                "content": str(result)})
            if self.temp != "":
                self.callback.print_message(
                    content = self.temp,
                    author = "Assistant",
                    style = "green"
                )
                self.store.store_string(self.temp, "assistant")
                self.temp = ""
            self.callback.print_message(
                content = str(result)[0:500],
                author = "Tool Result",
                style = "yellow"
            )
            logger.info(f"Tool call {call.function.name} executed\n{str(result)}")  

    def add_tools(self, tools: list[callable]):
        """
        Adds a list of tools to the engine.
        """
        self.tools.extend(tools)
    
    def add_agent_tools(self, tools: list[callable]):
        """
        Adds a list of agent tools to the engine.
        """
        self.agent_tools.extend(tools)


class ToolEngine():
    def __init__(self, 
                client: Union[ClientOpenAI, ClientAnthropic],
                model_name: str,
                system_prompt: Optional[str] = None,
                instructions: Optional[List[str]] = None,
                tools: Optional[List[callable]] = None,
                callback: Any = None
                ):
        self.callback = callback
        self.client = client
        self.model_name = model_name
        self.store = ContextStore()
        if system_prompt:
            self.store.set_system_prompt(system_prompt)
        else:
            self.store.set_system_prompt("You are a helpful assistant.")
        self.instructions = instructions if instructions else []
        self.tools = tools if tools else []
        self.tasks = []
    
    
    def execute_instructions(self, instructions: List[str]):
        """
        Executes a list of instructions.
        """
        self.instructions.extend(instructions)
        self.run()

    def run(self):
        """
        Runs all instructions.
        An instruction can generate multiple tasks (tool calls).
        A task is a function that is being called by the tool engine.
        """
        while self.instructions:
            with self.callback.show_loading() as callback:
            # Get next instruction and store it
                callback.update_status("Executing instruction...")
                instruction = self.instructions.pop(0)
                self.store.store_string(instruction, "user")
                
                # Create completion with tools
                callback.update_status("Waiting for instruction API response...")
                response = self.client.create_tool_completion(
                    self.model_name,
                    self.store.retrieve(), 
                    tools=create_tools_schema(self.tools)
                )
                # If response contains tool calls, handle them
                if response.stop_reason == "tool_calls":
                    while response.stop_reason == "tool_calls":
                        # Store the response with tool calls
                        callback.update_status("Processing tool calls...")
                        self.store.store_tool_response(response)
                        # Parse and execute each tool call
                        tool_lookup = create_tools_lookup(self.tools)
                        for call in parse_functions(response.tool_calls):
                            # Execute the task
                            callback.update_status(f"Executing {call.function.name} function...")
                            try:
                                result = execute_function(call, tool_lookup)
                            except Exception as e:
                                result = f"Error executing {call.function.name} function: {str(e)}"
                            # Store the result
                            self.store.store_function_call_result(
                                {"role": "tool",
                                "tool_call_id": call.id,
                                "name": call.function.name,
                                "content": str(result)})
                            self.callback.print_message(
                                content = str(result)[0:500],
                                author = "Tool Result",
                                style = "yellow"
                            )
                            logger.info(f"Tool call {call.function.name} executed\n{str(result)}")
                        callback.update_status("Waiting for tool API response...")
                        response = self.client.create_tool_completion(
                            self.model_name,
                            self.store.retrieve(),
                            tools=create_tools_schema(self.tools)
                        )
                        if response.stop_reason == "tool_calls":
                            continue
                        self.store.store_response(response, "assistant")
                else:
                    # For regular responses without tool calls
                    self.store.store_response(response, "assistant")
            
    def add_tool(self, tool: callable):
        """
        Adds a tool to the tool engine.
        """
        self.tools.append(tool)

    def add_instruction(self, instruction: str):
        """
        Adds an instruction to the tool engine.
        """
        self.instructions.append(instruction)

    def set_system_prompt(self, system_prompt: str):
        """
        Sets the system prompt for the tool engine.
        """
        self.store.set_system_prompt(system_prompt)


class BasicChatContextEngine():
    def __init__(self, 
                client: Union[ClientOpenAI, ClientAnthropic],
                model_name: str,
                system_prompt: Optional[str] = None):
        self.client = client
        self.model_name = model_name
        self.store = BasicChatContextStore()
        if system_prompt:
            self.store.set_system_prompt(system_prompt)
    
    def compile(self, message: str) -> Any:
        """
        Compiles context store with user input and returns the context.
        """
        self.store.store_string(message, "user")
        return self.store.retrieve()

    
    def execute(self, message: str):
        """
        Executes the context engine with a user message.
        """
        context = self.compile(message)
        response = self.client.create_completion(
            self.model_name, 
            context)
        self.store.store_response(response, "assistant")
        return response
