"""Example demonstrating the refactored ObservabilityBus with custom handlers.

This example shows how to use the ObservabilityBus with various handlers.
"""

import asyncio
import time
from typing import Any, Dict

from llmgine.observability import ObservabilityBus
from llmgine.observability.events import LogEvent, LogLevel, MetricEvent, TraceEvent
from llmgine.observability.handlers import (
    ConsoleLogHandler,
    JsonFileHandler,
    InMemoryMetricsHandler,
    InMemoryTraceHandler,
    ObservabilityHandler
)


# Create a custom handler
class CustomLogHandler(ObservabilityHandler[LogEvent]):
    """Custom handler for log events that adds prefixes."""
    
    def __init__(self, prefix: str = "CUSTOM"):
        """Initialize the custom log handler.
        
        Args:
            prefix: Prefix to add to log messages
        """
        super().__init__()
        self.prefix = prefix
        
    def _get_event_type(self):
        """Get the event type this handler processes."""
        return LogEvent
        
    async def handle(self, event: LogEvent):
        """Handle a log event by printing with custom prefix.
        
        Args:
            event: The log event
        """
        print(f"{self.prefix} - {event.level.value}: {event.message}")


async def main():
    """Run the observability example."""
    # Get the ObservabilityBus instance
    obs_bus = ObservabilityBus(log_dir="logs/observability_example")
    
    # Add our custom handlers
    obs_bus.add_handler(CustomLogHandler(prefix="[APP]"))
    
    # Add in-memory handlers for metrics and traces
    metrics_handler = InMemoryMetricsHandler()
    trace_handler = InMemoryTraceHandler()
    obs_bus.add_handler(metrics_handler)
    obs_bus.add_handler(trace_handler)
    
    # Start the bus
    await obs_bus.start()
    
    try:
        # Send some log events
        obs_bus.log(LogLevel.INFO, "Application started", {"version": "1.0.0"})
        obs_bus.log(LogLevel.DEBUG, "Debug information", {"detail": "Some debug info"})
        
        # Record some metrics
        obs_bus.metric("request_count", 1, tags={"endpoint": "/api/v1/users"})
        obs_bus.metric("response_time", 150.5, unit="ms", tags={"endpoint": "/api/v1/users"})
        
        # Create a trace
        span = obs_bus.start_trace("process_request", {"user_id": "user123"})
        
        # Simulate some work
        time.sleep(0.5)
        
        # Create a child span
        child_span = obs_bus.start_trace("database_query", 
                                        {"query": "SELECT * FROM users"}, 
                                        parent_context=span)
        
        # Simulate database work
        time.sleep(0.2)
        
        # End the child span
        obs_bus.end_trace(child_span, status="success")
        
        # End the parent span
        obs_bus.end_trace(span, status="success")
        
        # Wait for all events to be processed
        await asyncio.sleep(1)
        
        # Retrieve metrics from memory
        print("\nStored Metrics:")
        metric = metrics_handler.get_metric("response_time", {"endpoint": "/api/v1/users"})
        if metric:
            print(f"  response_time: {metric['value']} {metric['unit']} for {metric['tags']}")
        
        # Retrieve trace from memory
        print("\nStored Traces:")
        trace = trace_handler.get_trace(span["trace_id"])
        if trace:
            print(f"  Trace ID: {trace['trace_id']}")
            print(f"  Number of spans: {len(trace['spans'])}")
            for span_id, span_data in trace['spans'].items():
                print(f"    - {span_data['name']} ({span_data['duration_ms']:.2f}ms)")
        
    finally:
        # Shutdown the bus
        await obs_bus.stop()
        

if __name__ == "__main__":
    asyncio.run(main())