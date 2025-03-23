import asyncio
import logging
import json
import random
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import key components from llmgine
from llmgine.bootstrap import ApplicationBootstrap
from llmgine.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.observability.bus import ObservabilityBus
from llmgine.observability.events import LogLevel

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Define command types for our demo


class FetchDataCommand(Command):
    """Command to fetch data from external sources."""

    def __init__(self, source: str, query: str):
        super().__init__()
        self.source = source
        self.query = query


class ProcessDataCommand(Command):
    """Command to process fetched data."""

    def __init__(self, data: Dict[str, Any], options: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.data = data
        self.options = options or {}


class GenerateResponseCommand(Command):
    """Command to generate a response from processed data."""

    def __init__(self, processed_data: List[Dict[str, Any]], format: str = "text"):
        super().__init__()
        self.processed_data = processed_data
        self.format = format


class SearchRequest(Command):
    """High-level command representing a user search request."""

    def __init__(self, query: str, sources: List[str], format: str = "text"):
        super().__init__()
        self.query = query
        self.sources = sources
        self.format = format


# Define events
class DataFetchedEvent(Event):
    """Event emitted when data is fetched."""

    def __init__(self, source: str, data: Dict[str, Any]):
        super().__init__()
        self.source = source
        self.data = data


class DataProcessedEvent(Event):
    """Event emitted when data is processed."""

    def __init__(self, processed_data: List[Dict[str, Any]]):
        super().__init__()
        self.processed_data = processed_data


class ResponseGeneratedEvent(Event):
    """Event emitted when a response is generated."""

    def __init__(self, response: str, format: str):
        super().__init__()
        self.response = response
        self.format = format


class TraceDemoApplication(ApplicationBootstrap):
    """Demo application with multilevel tracing."""

    def __init__(self):
        super().__init__()
        # Set up log directory
        self.log_dir = Path("multilevel_trace_logs")
        self.log_dir.mkdir(exist_ok=True)

    async def bootstrap(self) -> None:
        """Start the application buses and register handlers."""
        await super().bootstrap()

        # Register command handlers
        self.register_command_handler(FetchDataCommand, self.handle_fetch_data)
        self.register_command_handler(ProcessDataCommand, self.handle_process_data)
        self.register_command_handler(
            GenerateResponseCommand, self.handle_generate_response
        )
        self.register_command_handler(SearchRequest, self.handle_search_request)

    async def run_demo(self):
        """Run the demo with a multilevel trace hierarchy."""
        # Start the application
        await self.bootstrap()

        # Log start of demo
        self.obs_bus.log(
            LogLevel.INFO,
            "Starting multilevel trace demo",
            {"component": "TraceDemoApplication"},
        )

        # Execute a high-level search command which will create nested traces
        for i in range(3):
            query = f"demo query {i + 1}"
            sources = ["database", "api", "cache"] if i == 0 else ["database", "api"]

            logger.info(f"Executing search request {i + 1}: {query}")
            result = await self.message_bus.execute(
                SearchRequest(
                    query=query, sources=sources, format="json" if i % 2 == 0 else "text"
                )
            )
            logger.info(f"Search result: {result.result[:50]}...")

        # Log end of demo
        self.obs_bus.log(
            LogLevel.INFO,
            "Demo completed. Traces have been generated.",
            {"component": "TraceDemoApplication"},
        )

        # Show where logs are saved
        logger.info(f"Trace logs saved to: {self.log_dir.absolute()}")

        # Shutdown the application
        await self.shutdown()

    async def handle_search_request(self, command: SearchRequest) -> CommandResult:
        """Handle a search request with multiple nested operations."""
        # Start a trace for the entire search request
        search_span = self.obs_bus.start_trace(
            "search_request",
            {
                "query": command.query,
                "sources": ",".join(command.sources),
                "request_id": command.id,
            },
        )

        try:
            all_data = []

            # Fetch data from each source (creates child spans)
            for source in command.sources:
                # Execute the fetch command for each source
                fetch_result = await self.message_bus.execute(
                    FetchDataCommand(source, command.query)
                )

                if fetch_result.success:
                    all_data.append(fetch_result.result)

            # Process the combined data
            process_span = self.obs_bus.start_trace(
                "process_combined_data",
                {"data_sources": len(all_data)},
                search_span,  # Pass parent context
            )

            process_result = await self.message_bus.execute(
                ProcessDataCommand(
                    {"sources": command.sources, "data": all_data},
                    {"combine": True, "deduplicate": True},
                )
            )

            self.obs_bus.end_trace(process_span, "success")

            # Generate the final response
            response_result = await self.message_bus.execute(
                GenerateResponseCommand(process_result.result, format=command.format)
            )

            # End the parent trace
            self.obs_bus.end_trace(search_span, "success")

            return CommandResult(
                command_id=command.id, success=True, result=response_result.result
            )

        except Exception as e:
            logger.exception(f"Error processing search request: {e}")
            self.obs_bus.end_trace(search_span, "error")

            return CommandResult(command_id=command.id, success=False, error=str(e))

    async def handle_fetch_data(self, command: FetchDataCommand) -> CommandResult:
        """Handle a fetch data command with nested operations."""
        # Create a span for the fetch operation
        fetch_span = self.obs_bus.start_trace(
            "fetch_data", {"source": command.source, "query": command.query}
        )

        try:
            # Create nested spans for sub-operations
            connect_span = self.obs_bus.start_trace(
                "connect_to_source", {"source": command.source}, fetch_span
            )

            # Simulate connecting to a data source
            await asyncio.sleep(random.uniform(0.05, 0.2))
            self.obs_bus.end_trace(connect_span, "success")

            # Create a span for the actual data retrieval
            retrieve_span = self.obs_bus.start_trace(
                "retrieve_data",
                {"source": command.source, "query": command.query},
                fetch_span,
            )

            # Simulate data retrieval
            await asyncio.sleep(random.uniform(0.1, 0.5))

            # Generate fake data
            data = {
                "source": command.source,
                "timestamp": datetime.now().isoformat(),
                "results": [
                    {
                        "id": f"{command.source}_{i}",
                        "value": f"Result {i} for {command.query}",
                    }
                    for i in range(random.randint(3, 8))
                ],
            }

            self.obs_bus.end_trace(retrieve_span, "success")

            # Optionally create an error span to demonstrate error handling
            if random.random() < 0.2:  # 20% chance of a validation error
                validate_span = self.obs_bus.start_trace(
                    "validate_data",
                    {"source": command.source, "result_count": len(data["results"])},
                    fetch_span,
                )

                await asyncio.sleep(random.uniform(0.05, 0.1))

                # Simulate a validation issue (but not a failure)
                self.obs_bus.log(
                    LogLevel.WARNING,
                    f"Data validation warning for source {command.source}",
                    {"warning": "Some fields may be incomplete"},
                )

                self.obs_bus.end_trace(validate_span, "warning")

            # End the parent fetch span
            self.obs_bus.end_trace(fetch_span, "success")

            # Emit data fetched event
            await self.message_bus.publish(DataFetchedEvent(command.source, data))

            return CommandResult(command_id=command.id, success=True, result=data)

        except Exception as e:
            logger.exception(f"Error fetching data from {command.source}: {e}")
            self.obs_bus.end_trace(fetch_span, "error")

            return CommandResult(command_id=command.id, success=False, error=str(e))

    async def handle_process_data(self, command: ProcessDataCommand) -> CommandResult:
        """Handle data processing."""
        process_span = self.obs_bus.start_trace(
            "process_data", {"data_size": len(str(command.data))}
        )

        try:
            # Create nested spans for each processing step
            steps = ["parse", "transform", "analyze", "summarize"]
            processed_results = []

            for step in steps:
                step_span = self.obs_bus.start_trace(
                    f"process_{step}", {"step": step}, process_span
                )

                # Simulate processing work
                await asyncio.sleep(random.uniform(0.05, 0.2))

                # Fake processing result
                if step == "parse":
                    result = {"parsed": True, "items": command.data.get("data", [])}
                elif step == "transform":
                    result = {
                        "transformed": True,
                        "count": len(command.data.get("data", [])),
                    }
                elif step == "analyze":
                    result = {"analyzed": True, "score": random.uniform(0.5, 0.95)}
                else:  # summarize
                    result = {"summarized": True, "length": random.randint(50, 200)}

                processed_results.append(result)
                self.obs_bus.end_trace(step_span, "success")

            # End the parent process span
            self.obs_bus.end_trace(process_span, "success")

            # Emit data processed event
            await self.message_bus.publish(DataProcessedEvent(processed_results))

            return CommandResult(
                command_id=command.id, success=True, result=processed_results
            )

        except Exception as e:
            logger.exception(f"Error processing data: {e}")
            self.obs_bus.end_trace(process_span, "error")

            return CommandResult(command_id=command.id, success=False, error=str(e))

    async def handle_generate_response(
        self, command: GenerateResponseCommand
    ) -> CommandResult:
        """Handle response generation."""
        generate_span = self.obs_bus.start_trace(
            "generate_response", {"format": command.format}
        )

        try:
            # Create format-specific span
            format_span = self.obs_bus.start_trace(
                f"format_{command.format}",
                {"data_elements": len(command.processed_data)},
                generate_span,
            )

            # Simulate the formatting work
            await asyncio.sleep(random.uniform(0.1, 0.3))

            # Generate a fake response
            if command.format == "json":
                response = json.dumps(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "results": command.processed_data,
                        "count": len(command.processed_data),
                    },
                    indent=2,
                )
            else:
                response = (
                    f"Generated text response with {len(command.processed_data)} items.\n"
                )
                for i, item in enumerate(command.processed_data):
                    response += f"Item {i + 1}: {json.dumps(item)[:30]}...\n"

            self.obs_bus.end_trace(format_span, "success")

            # End the parent generate span
            self.obs_bus.end_trace(generate_span, "success")

            # Emit response generated event
            await self.message_bus.publish(
                ResponseGeneratedEvent(response, command.format)
            )

            return CommandResult(command_id=command.id, success=True, result=response)

        except Exception as e:
            logger.exception(f"Error generating response: {e}")
            self.obs_bus.end_trace(generate_span, "error")

            return CommandResult(command_id=command.id, success=False, error=str(e))


# Run the demo
async def main():
    demo = TraceDemoApplication()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
