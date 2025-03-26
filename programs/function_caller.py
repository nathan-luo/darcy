#!/usr/bin/env python3
"""Function calling example using the refactored LLMgine.

This example shows how to set up more advanced function calls with the new LLMgine.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
from llmgine.llm import (
    LLMEngine,
    PromptCommand,
    SystemPromptCommand,
    LLMResponseEvent,
    ToolCallEvent,
    ToolResultEvent,
    default_tool_manager,
)
from llmgine.llm.providers.openai import OpenAIProvider
from llmgine.messages.events import Event
from llmgine.observability.events import LogLevel


# More complex tools for demonstration
def search_database(query: str, limit: int = 5) -> List[Dict[str, str]]:
    """Search a mock database for information.

    Args:
        query: Search query
        limit: Maximum number of results to return

    Returns:
        List of matching records
    """
    # Mock database
    database = [
        {
            "id": "1",
            "name": "Apple iPhone 14",
            "category": "Electronics",
            "price": "$799",
        },
        {
            "id": "2",
            "name": "Samsung Galaxy S23",
            "category": "Electronics",
            "price": "$849",
        },
        {
            "id": "3",
            "name": "Kindle Paperwhite",
            "category": "Electronics",
            "price": "$139",
        },
        {"id": "4", "name": "Macbook Pro M2", "category": "Computers", "price": "$1299"},
        {"id": "5", "name": "Dell XPS 13", "category": "Computers", "price": "$999"},
        {"id": "6", "name": "LEGO Star Wars Set", "category": "Toys", "price": "$59.99"},
        {"id": "7", "name": "Barbie Dreamhouse", "category": "Toys", "price": "$179.99"},
        {
            "id": "8",
            "name": "Harry Potter Book Set",
            "category": "Books",
            "price": "$89.99",
        },
        {"id": "9", "name": "Nike Air Max", "category": "Clothing", "price": "$129.99"},
        {
            "id": "10",
            "name": "Adidas Ultraboost",
            "category": "Clothing",
            "price": "$189.99",
        },
    ]

    # Perform search (case-insensitive)
    query = query.lower()
    results = []

    for item in database:
        if query in item["name"].lower() or query in item["category"].lower():
            results.append(item)

        if len(results) >= limit:
            break

    return results


def create_user(name: str, email: str, age: Optional[int] = None) -> Dict[str, Any]:
    """Create a mock user in the system.

    Args:
        name: User's name
        email: User's email
        age: Optional user's age

    Returns:
        Created user record
    """
    # Validate inputs
    if not name:
        raise ValueError("Name cannot be empty")

    if not email or "@" not in email:
        raise ValueError("Invalid email address")

    if age is not None and (age < 0 or age > 120):
        raise ValueError("Age must be between 0 and 120")

    # Create user
    user_id = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    user = {
        "id": user_id,
        "name": name,
        "email": email,
        "age": age,
        "created_at": datetime.now().isoformat(),
    }

    return user


def get_weather(location: str, unit: str = "celsius") -> Dict[str, Any]:
    """Get weather information for a location.

    Args:
        location: City or location name
        unit: Temperature unit (celsius or fahrenheit)

    Returns:
        Weather information
    """
    # Validate inputs
    if not location:
        raise ValueError("Location cannot be empty")

    if unit not in ["celsius", "fahrenheit"]:
        raise ValueError("Unit must be 'celsius' or 'fahrenheit'")

    # Mock weather data based on location
    weather_data = {
        "new york": {
            "condition": "Partly Cloudy",
            "temperature_c": 22,
            "temperature_f": 72,
            "humidity": 65,
            "wind_speed": 10,
        },
        "london": {
            "condition": "Rainy",
            "temperature_c": 18,
            "temperature_f": 64,
            "humidity": 80,
            "wind_speed": 15,
        },
        "tokyo": {
            "condition": "Sunny",
            "temperature_c": 28,
            "temperature_f": 82,
            "humidity": 70,
            "wind_speed": 8,
        },
        "sydney": {
            "condition": "Clear",
            "temperature_c": 25,
            "temperature_f": 77,
            "humidity": 60,
            "wind_speed": 12,
        },
        "paris": {
            "condition": "Cloudy",
            "temperature_c": 20,
            "temperature_f": 68,
            "humidity": 75,
            "wind_speed": 9,
        },
    }

    # Check if we have data for this location
    location_key = location.lower()
    if location_key not in weather_data:
        # Generate random weather if location not found
        import random

        temp_c = random.randint(10, 35)
        conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Clear", "Stormy"]

        weather_data[location_key] = {
            "condition": random.choice(conditions),
            "temperature_c": temp_c,
            "temperature_f": round((temp_c * 9 / 5) + 32),
            "humidity": random.randint(40, 90),
            "wind_speed": random.randint(0, 30),
        }

    # Format response based on requested unit
    result = {
        "location": location,
        "condition": weather_data[location_key]["condition"],
        "humidity": f"{weather_data[location_key]['humidity']}%",
        "wind_speed": f"{weather_data[location_key]['wind_speed']} km/h",
    }

    if unit == "celsius":
        result["temperature"] = f"{weather_data[location_key]['temperature_c']}°C"
    else:
        result["temperature"] = f"{weather_data[location_key]['temperature_f']}°F"

    return result


class FunctionCallerApp(ApplicationBootstrap):
    """Function calling example application."""

    def __init__(self):
        """Initialize the function caller application."""
        # Create configuration
        config = ApplicationConfig(
            log_level=LogLevel.INFO,
            log_dir="logs/function_caller",
            console_logging=True,
            file_logging=True,
            metrics_enabled=True,
            tracing_enabled=True,
        )

        # Initialize bootstrap with config
        super().__init__(config)

        # Initialize engine
        self.llm_engine = LLMEngine(
            message_bus=self.message_bus,
            obs_bus=self.obs_bus,
        )

        # Register LLM provider
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            print("Warning: OPENAI_API_KEY environment variable not set.")
            print("Using dummy provider instead.")
        else:
            openai_provider = OpenAIProvider(api_key=openai_api_key)
            self.llm_engine.llm_manager.register_provider("openai", openai_provider)
            self.llm_engine.llm_manager.set_default_provider("openai")

        # Register tools
        self._register_tools()

        # Set up event handlers
        self._register_event_handlers()

    def _register_command_handlers(self):
        """Register command handlers for the application."""
        pass

    def _register_event_handlers(self):
        """Register event handlers for the application."""
        self.message_bus.register_event_handler(
            LLMResponseEvent, self._handle_llm_response
        )
        self.message_bus.register_event_handler(ToolCallEvent, self._handle_tool_call)
        self.message_bus.register_event_handler(ToolResultEvent, self._handle_tool_result)

    def _register_tools(self):
        """Register tools for the function caller."""
        # Create observable wrappers for our tools
        search_db_obs = self._create_observable_tool(search_database, "search_database")
        create_user_obs = self._create_observable_tool(create_user, "create_user")
        get_weather_obs = self._create_observable_tool(get_weather, "get_weather")
        
        # Register wrapped tools
        default_tool_manager.register_tool(search_db_obs)
        default_tool_manager.register_tool(create_user_obs)
        default_tool_manager.register_tool(get_weather_obs)
        
    def _create_observable_tool(self, func, name):
        """Create an observable wrapper for a tool function.
        
        Args:
            func: The original function
            name: Function name for logging
            
        Returns:
            Wrapped function with observability
        """
        import functools
        import inspect
        import time
        import json
        from datetime import datetime
        
        # Get the original signature and annotations
        sig = inspect.signature(func)
        
        # Create a wrapper that preserves the function signature
        @functools.wraps(func)
        def observable_wrapper(*args, **kwargs):
            # Start the trace
            span = self.obs_bus.start_trace(
                f"tool_execution_{name}",
                {
                    "tool": name,
                    "params": json.dumps({k: str(v) for k, v in kwargs.items()})
                }
            )
            
            # Log the tool call
            self.obs_bus.log(
                LogLevel.INFO,
                f"Tool call: {name}",
                {
                    "tool": name,
                    "params": kwargs,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            start_time = time.time()
            try:
                # Execute the original function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Record metrics
                self.obs_bus.metric(
                    f"tool_execution_{name}_duration_ms",
                    duration_ms,
                    "milliseconds"
                )
                
                # Log success
                self.obs_bus.log(
                    LogLevel.INFO,
                    f"Tool {name} executed successfully",
                    {
                        "duration_ms": duration_ms,
                        "result": str(result)[:100] + ("..." if len(str(result)) > 100 else "")
                    }
                )
                
                # End the trace
                self.obs_bus.end_trace(span, "success")
                
                return result
                
            except Exception as e:
                # Calculate duration for failed execution
                duration_ms = (time.time() - start_time) * 1000
                
                # Log error
                self.obs_bus.log(
                    LogLevel.ERROR,
                    f"Tool {name} execution failed: {str(e)}",
                    {
                        "duration_ms": duration_ms,
                        "error": str(e)
                    }
                )
                
                # Record error metric
                self.obs_bus.metric(
                    f"tool_execution_{name}_error",
                    1,
                    "count"
                )
                
                # End the trace with error
                self.obs_bus.end_trace(span, "error")
                
                # Re-raise the exception
                raise
                
        # Return the wrapped function
        return observable_wrapper

    async def _handle_llm_response(self, event: LLMResponseEvent):
        """Handle an LLM response event.

        Args:
            event: The LLM response event
        """
        print("\n--- LLM Response ---")
        if event.response.content:
            print(event.response.content)
        else:
            print("(No text response, using function calls)")

    async def _handle_tool_call(self, event: ToolCallEvent):
        """Handle a tool call event.

        Args:
            event: The tool call event
        """
        import json

        try:
            args = json.loads(event.tool_call.arguments)
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            print(f"\n--- Tool Call ---")
            print(f"Tool: {event.tool_call.name}")
            print(f"Arguments: {args_str}")
        except json.JSONDecodeError:
            print(f"\n--- Tool Call ---")
            print(f"Tool: {event.tool_call.name}")
            print(f"Arguments: {event.tool_call.arguments}")

    async def _handle_tool_result(self, event: ToolResultEvent):
        """Handle a tool result event.

        Args:
            event: The tool result event
        """
        print(f"\n--- Tool Result ---")
        if event.error:
            print(f"ERROR: {event.error}")
        else:
            if isinstance(event.result, (dict, list)):
                print(json.dumps(event.result, indent=2))
            else:
                print(event.result)

    async def run_prompt(
        self, prompt: str, model: Optional[str] = None, verbose: bool = False
    ):
        """Run a single prompt and wait for the response.

        Args:
            prompt: The prompt to send
            model: Optional model to use
            verbose: Whether to display verbose output
        """
        # Create prompt command
        prompt_command = PromptCommand(
            prompt=prompt, use_tools=True, conversation_id="default", model=model
        )

        # Print the prompt
        print(f"\n>>> {prompt}")

        # Execute the command
        result = await self.message_bus.execute(prompt_command)

        # Check for errors
        if not result.success:
            error_msg = result.error or "Unknown error"
            print(f"\nError: {error_msg}")

        # In verbose mode, display the LLM response details
        if verbose and result.success:
            import json

            llm_response = result.result
            print("\n--- LLM Response Details ---")
            print(f"Model: {llm_response.model}")
            print(f"Finish Reason: {llm_response.finish_reason}")
            if llm_response.usage:
                print(f"Tokens: {json.dumps(llm_response.usage, indent=2)}")

        # Wait a moment for event handlers to complete
        await asyncio.sleep(0.1)


async def main():
    """Run the function caller application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LLMgine Function Caller Example")
    parser.add_argument(
        "prompt", nargs="?", default=None, help="Prompt to send to the LLM"
    )
    parser.add_argument(
        "--model", default="gpt-4o-mini", help="Model to use (default: gpt-3.5-turbo)"
    )
    parser.add_argument("--verbose", action="store_true", help="Display verbose output")
    parser.add_argument(
        "--prompts", action="store_true", help="Run a series of example prompts"
    )
    args = parser.parse_args()

    # Create the app
    app = FunctionCallerApp()
    await app.bootstrap()

    # Set the system prompt
    system_prompt = """You are a helpful assistant with access to functions. Use the functions to help users with their requests. When calling functions:
1. Use the search_database function to look up products
2. Use the create_user function to create a new user account
3. Use the get_weather function to get weather information

Call functions whenever they are needed to fulfill the user's request. Be concise in your responses."""

    system_command = SystemPromptCommand(
        system_prompt=system_prompt, conversation_id="default"
    )
    await app.message_bus.execute(system_command)

    try:
        if args.prompts:
            # Run a series of example prompts
            prompts = [
                "What electronics products do you have available?",
                "What's the weather like in Tokyo?",
                "Create a new user account for John Doe with email john@example.com",
                "I need to find toys under $100",
                "What's the weather in Paris and London?",
                "Can you tell me about computer products and also create a user for alice@example.com named Alice Smith?",
            ]

            for prompt in prompts:
                await app.run_prompt(prompt, model=args.model, verbose=args.verbose)
                print("\n" + "-" * 70)

        elif args.prompt:
            # Run a single prompt
            await app.run_prompt(args.prompt, model=args.model, verbose=args.verbose)
        else:
            # No prompt provided, show usage
            parser.print_usage()

    finally:
        # Shut down the application
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
