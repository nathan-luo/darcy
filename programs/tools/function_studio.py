""" This module will be the test program for tool manager.
    Involving tool manager initialization, tool registration, tool execution, and tool result display
    with real LLM model.

    Tools for test are from tests/tools/tools_for_test.py
"""

import asyncio
import os
import json
import dotenv
from typing import List, Callable
from openai import OpenAI
import logging

from tools_for_test import get_weather, send_email
from llmgine.llm.tools import ToolManager

dotenv.load_dotenv()

# Add these lines after your imports
logging.getLogger("openai").setLevel(logging.WARNING)  # or logging.ERROR
logging.getLogger("httpx").setLevel(logging.WARNING)   # for HTTP client logging
logging.getLogger().setLevel(logging.WARNING)          # for root logger

# Define a class for managing LLM interactions
class LLMManager:
    def __init__(self, api_key, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
    def generate_response(self, messages, tools=None):
        """Generate a response from the LLM with optional tools."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None
        )
        return response.choices[0].message

# Define a class for managing chat context
class ChatContext:
    def __init__(self, system_message="You are a helpful assistant."):
        self.messages = [{"role": "system", "content": system_message}]
    
    def add_user_message(self, content):
        """Add a user message to the context."""
        self.messages.append({"role": "user", "content": content})
    
    def add_assistant_message(self, message):
        """Add an assistant message to the context."""
        self.messages.append({
            "role": "assistant",
            "content": message.content if hasattr(message, 'content') else message
        })
        
        # If this message contains tool calls, add them too
        if hasattr(message, 'tool_calls') and message.tool_calls:
            # Use model_dump() to convert Pydantic model to dict if needed
            if hasattr(message, 'model_dump'):
                self.messages[-1] = message.model_dump()
    
    def add_tool_result(self, tool_call_id, name, content):
        """Add a tool result to the context."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content
        })
    
    def get_messages(self):
        """Get all messages in the context."""
        return self.messages


# Define a simple chat application that uses these components
class ChatApplication:
    def __init__(self, api_key, model, system_message="You are a helpful assistant."):
        self.llm_manager = LLMManager(api_key)
        self.tool_manager = ToolManager(llm_model_name=model)
        self.context = ChatContext(system_message)
    
    def register_tool(self, func):
        """Register a function as a tool."""
        self.tool_manager.register_tool(func)
        return self
    
    async def process_user_input(self, user_input):
        """Process user input and return the assistant's response."""
        # Add user message to context
        self.context.add_user_message(user_input)
        
        # Get schemas for registered tools
        tools = self.tool_manager.get_tools()
        
        # Get initial response from LLM
        response = self.llm_manager.generate_response(
            self.context.get_messages(),
            tools=tools if tools else None
        )
        
        # Add assistant's response to context
        self.context.add_assistant_message(response)
        
        # Check if any tool calls are requested
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # Process each tool call
            for tool_call in response.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                try:
                    # Execute the tool
                    result = await self.tool_manager.execute_tool(function_name, arguments)
                    
                    # Add tool result to context
                    self.context.add_tool_result(
                        tool_call.id,
                        function_name,
                        str(result) if not isinstance(result, dict) else json.dumps(result)
                    )
                except Exception as e:
                    # Handle errors
                    error_message = f"Error executing tool {function_name}: {str(e)}"
                    self.context.add_tool_result(tool_call.id, function_name, error_message)
            
            # Get final response from LLM with tool results
            final_response = self.llm_manager.generate_response(self.context.get_messages())
            
            # Add final response to context
            self.context.add_assistant_message(final_response)
            
            return final_response.content
        else:
            # No tool calls, so return initial response
            return response.content


async def function_studio(model: str, tools: List[Callable], inputs: List[str]):
    """Function Studio.
    
    Args:
        model: The model to be used.
        inputs: The input prompts to the function.
    """
    
    # Send request to LLM model with the registered tools and the input prompts
    # Create a chat application
    api_key = os.environ.get("OPENAI_API_KEY")
    app = ChatApplication(api_key, model)

    # Register tools
    for tool in tools:
        app.register_tool(tool)
    print(f'Registered tools: {[tool["function"]["name"] for tool in app.tool_manager.get_tools()]}')

    # Process some user input
    for input in inputs:    
        print("User:", input)
        response = await app.process_user_input(input)
        print("Assistant:", response)

    

def main():
    asyncio.run(function_studio(model="openai", tools=[get_weather, send_email], inputs=["Hey, what's weather like in Brisbane", 
                                                                 "Also, send an email to John Doe. Subject is 'Test' and body 'This is a test email', thanks!"]))



main()