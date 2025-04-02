"""Demonstration of the handler-based observability system using MessageBus."""

import asyncio
import sys
import os
import uuid # Added for trace IDs
from datetime import datetime # Added for trace timestamps
from typing import Any, List, Type, Optional, Dict # Added Optional and Dict
from dataclasses import dataclass, field

from llmgine.bus.bus import MessageBus, current_span_context
from llmgine.messages.commands import Command, CommandResult
from function_studio import main as function_studio_main

# Adjust path to import from the llmgine source directory
# This assumes the script is run from the root of the 'llmgine' project directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
# Import events directly
from llmgine.observability import (
    LogEvent, LogLevel, ObservabilityBaseEvent as ObservabilityBaseEvent, # Renamed BaseEvent
)
# Need the application Event base class
from llmgine.messages.events import Event

# --- Define Simple App Event for Testing ---
@dataclass(kw_only=True)
class DemoAppEvent(Event):
    """A simple application-specific event for the demo."""
    payload: Dict[str, Any]

# --- 2. Define Configuration --- 
@dataclass
class DemoConfig(ApplicationConfig):
    """Configuration specific to this demo."""
    name: str = "ToolsFunctionStudioV2Demo"
    description: str = "Demonstrates tools and functions via MessageBus."

    # Configure observability handlers via ApplicationConfig fields
    enable_console_handler: bool = True
    enable_file_handler: bool = True
    file_handler_log_dir: str = "logs/tool_events_demo" # Specify log directory
    file_handler_log_filename: str = "tool_events_demo.jsonl" # Specify log filename

    # Standard Python logging level (adjust if needed)
    log_level: LogLevel = LogLevel.DEBUG


class DemoApplicationBootstrap(ApplicationBootstrap):
    """Bootstrap the application."""
    def __init__(self, config: DemoConfig):
        super().__init__(config=config)


async def main():
    """Runs the simplified observability demo."""
    print("--- Starting Simplified Observability Demo (Handler-Based) --- ")

    # --- 3. Bootstrap Application --- 
    print("\n--- Initializing & Bootstrapping ---")
    config = DemoConfig()
    bootstrap = DemoApplicationBootstrap(config=config)
    await bootstrap.bootstrap()
    await asyncio.sleep(0.1) 
    message_bus = bootstrap.message_bus
    log_file_path = bootstrap.message_bus.log_file if hasattr(bootstrap.message_bus, 'log_file') else 'N/A' # Get log file path if FileHandler was enabled
    print(f"Handlers registered. File logging (if enabled) target: {log_file_path}")

    # --- 4. Demonstrate Observability Features ---
    print("\n--- Demonstrating Observability Features --- ")
    source_component = "SimplifiedDemoScript"

    # --- Example: Manual Span Creation ---
    manual_span_context = None
    manual_span_token = None
    try:
        print("\n* Manually starting a span 'DemoEventPublishing'")
        manual_span_context = await message_bus.start_span(
            name="DemoEventPublishing", 
            source="SimplifiedDemoScript",
            attributes={"demo_purpose": "Wrapping event publications"}
        )
        # Set context for manual span
        manual_span_token = current_span_context.set(manual_span_context) 
        
        # Events published within this block will be children of 'DemoEventPublishing' 
        # if their handlers use bus.execute or manually propagate context.

        # 1. Publish LogEvent
        print("\n* Publishing LogEvent...")
        log_event = LogEvent(level=LogLevel.WARNING, message="Test warning log event.", source=source_component)
        await message_bus.publish(log_event)
        # Expected: Handlers receive and process LogEvent.

    except Exception as e:
        print(f"\nError during event publishing demo: {e}")
        # Optionally end the span with error status if an exception occurs
        if manual_span_context:
            print("* Manually ending span 'DemoEventPublishing' with EXCEPTION status.")
            await message_bus.end_span(
                manual_span_context, 
                name="DemoEventPublishing", 
                status="EXCEPTION", 
                error=e,
                source="SimplifiedDemoScript (Error)"
            )
            manual_span_context = None # Prevent ending again in finally

        # --- 2. Run Function Studio --- 
        print("\n--- Running Function Studio ---")
        await function_studio_main()

    finally:
        # Ensure the manual span is always ended and context is reset
        if manual_span_context:
            print("* Manually ending span 'DemoEventPublishing' with OK status.")
            await message_bus.end_span(
                manual_span_context, 
                name="DemoEventPublishing", 
                status="OK",
                source="SimplifiedDemoScript (Finally)"
            )
        if manual_span_token:
            current_span_context.reset(manual_span_token)
            print("* Reset context var after manual span.")


    # Allow time for handlers to process events
    print("\n--- Allowing time for events to process/log ---")
    await asyncio.sleep(0.5)

    # --- 5. Shutdown --- 
    print("\n--- Shutting Down Application ---")
    await bootstrap.shutdown()

    print("\n--- Simplified Observability Demo Finished --- ")
    print(f"Check console output above and log file: {log_file_path}")

if __name__ == "__main__":
    # Add basic error handling for path setup
    if src_path not in sys.path:
        print(f"Error: Could not find source directory at {src_path}", file=sys.stderr)
        print("Please run this script from the root 'llmgine' project directory.", file=sys.stderr)
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nAn error occurred during the demo: {e}", file=sys.stderr)
        # import traceback
        # traceback.print_exc()
        sys.exit(1) 