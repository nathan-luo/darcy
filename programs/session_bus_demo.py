#!/usr/bin/env python3
"""
Session Bus Demo

This demo showcases the simplified message bus with session handling.
It demonstrates:
1. Creating sessions
2. Registering event and command handlers
3. Publishing events and executing commands with proper session ID inheritance
4. Session lifecycle and context handling
5. Using the bootstrap pattern for application setup
"""

import asyncio
import os
import uuid
import logging
from typing import List, Optional
from dataclasses import dataclass, field

from llmgine.bootstrap import (
    ApplicationBootstrap,
    ApplicationConfig,
    LogLevel,
    setup_basic_logging,
)
from llmgine.bus.bus import MessageBus, current_session_id
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.observability.events import EventLogWrapper


# --- Custom Logging Filter ---
class SessionFilter(logging.Filter):
    """Filter that ensures all log records have a session_id field."""

    def filter(self, record):
        if not hasattr(record, "session_id"):
            record.session_id = "global"
        return True


# --- Create a custom configuration for our demo ---


@dataclass
class SessionDemoConfig(ApplicationConfig):
    """Configuration for the session bus demo."""

    name: str = "session_bus_demo"
    description: str = "Demonstrates the simplified message bus with session handling"

    # Override default log settings
    log_level: LogLevel = LogLevel.INFO

    # File logging setup
    enable_file_handler: bool = True
    file_handler_log_dir: str = "logs/session_demo"

    # Console output for demo visibility
    enable_console_handler: bool = True

    # Tracing control
    enable_tracing: bool = True


# --- Define custom events and commands for the demo ---


@dataclass
class GreetingEvent(Event):
    """Event that carries a greeting message."""

    message: str = ""


@dataclass
class NotificationEvent(Event):
    """Event that carries a notification message."""

    message: str = ""
    importance: str = "normal"  # low, normal, high


@dataclass
class CalculateCommand(Command):
    """Command to perform a calculation."""

    operation: str = ""  # add, subtract, multiply, divide
    operands: List[float] = field(default_factory=list)
    result: Optional[float] = None


@dataclass
class LogCommand(Command):
    """Command to log a message."""

    message: str = ""
    level: str = "info"  # debug, info, warning, error


# --- Helper class to capture and display events ---


class EventCollector:
    """Collects and records events for display purposes."""

    def __init__(self, name: str):
        self.name = name
        self.events = []
        self.session_events = {}  # Organized by session ID

    async def handle_event(self, event_wrapper: EventLogWrapper):
        """Event handler that collects events."""
        # Extract useful info from the wrapper
        event_type = event_wrapper.original_event_type
        event_data = event_wrapper.original_event_data
        session_id = getattr(event_wrapper, "session_id", None) or "global"

        # Store event info
        event_info = {"type": event_type, "session_id": session_id, "data": event_data}

        self.events.append(event_info)

        # Also organize by session
        if session_id not in self.session_events:
            self.session_events[session_id] = []
        self.session_events[session_id].append(event_info)

        # Log the event
        message = event_data.get("message", "")
        if event_type == "GreetingEvent" and message:
            logging.info(
                f"[Collector: {self.name}] Greeting received: {message}",
                extra={"session_id": session_id},
            )
        elif event_type == "NotificationEvent" and message:
            importance = event_data.get("importance", "normal")
            logging.info(
                f"[Collector: {self.name}] Notification ({importance}): {message}",
                extra={"session_id": session_id},
            )
        else:
            logging.info(
                f"[Collector: {self.name}] Received {event_type}",
                extra={"session_id": session_id},
            )

    def display_summary(self):
        """Display a summary of collected events."""
        print(f"\n=== {self.name} Event Summary ===")
        print(f"Total events collected: {len(self.events)}")

        # Summary by session
        print("\nEvents by session:")
        for session_id, events in self.session_events.items():
            print(f"  Session {session_id}: {len(events)} events")
            # Group by type within each session
            event_types = {}
            for e in events:
                event_type = e["type"]
                if event_type not in event_types:
                    event_types[event_type] = 0
                event_types[event_type] += 1

            for event_type, count in event_types.items():
                print(f"    - {event_type}: {count}")


# --- Command handlers ---


async def calculate_handler(command: CalculateCommand) -> CommandResult:
    """Handler for the CalculateCommand."""
    try:
        operation = command.operation.lower()
        operands = command.operands

        if not operands:
            return CommandResult(
                success=False, original_command=command, error="No operands provided"
            )

        if operation == "add":
            result = sum(operands)
        elif operation == "subtract":
            result = operands[0] - sum(operands[1:])
        elif operation == "multiply":
            result = 1
            for operand in operands:
                result *= operand
        elif operation == "divide":
            if 0 in operands[1:]:
                return CommandResult(
                    success=False, original_command=command, error="Division by zero"
                )
            result = operands[0]
            for operand in operands[1:]:
                result /= operand
        else:
            return CommandResult(
                success=False,
                original_command=command,
                error=f"Unknown operation: {operation}",
            )

        # Log the calculation via an event in the same session context
        bus = MessageBus()
        notification = NotificationEvent(
            message=f"Calculation result: {result} (operation: {operation})",
            importance="normal",
        )
        await bus.publish(notification)

        # Return successful result
        return CommandResult(success=True, original_command=command, result=result)

    except Exception as e:
        return CommandResult(
            success=False,
            original_command=command,
            error=f"Error in calculation: {str(e)}",
        )


async def log_handler(command: LogCommand) -> CommandResult:
    """Handler for the LogCommand."""
    level = command.level.lower()
    message = command.message
    session_id = command.session_id or "unknown"

    # Use Python's standard logging with session_id extra parameter
    log_func = logging.info
    if level == "debug":
        log_func = logging.debug
    elif level == "info":
        log_func = logging.info
    elif level == "warning":
        log_func = logging.warning
    elif level == "error":
        log_func = logging.error

    log_func(f"[Command Log] {message}", extra={"session_id": session_id})

    # Also publish a notification event with the same session context
    bus = MessageBus()
    notification = NotificationEvent(
        message=f"Log entry created: {message}", importance="low"
    )
    await bus.publish(notification)

    return CommandResult(success=True, original_command=command)


# --- Demo Bootstrap class ---


class SessionDemoBootstrap(ApplicationBootstrap[SessionDemoConfig]):
    """Bootstrap for the session bus demo."""

    def __init__(self, config: SessionDemoConfig = None):
        """Initialize the bootstrap with our custom config."""
        # Initialize with the default config if none provided
        config = config or SessionDemoConfig()

        # Call parent constructor - this will set up logging based on config
        super().__init__(config)

        # Set up global event collector
        self.global_collector = EventCollector("Global")

        # Configure tracing according to config
        if not self.config.enable_tracing:
            self.message_bus.disable_tracing()
            logging.info(
                "Tracing has been disabled for this demo", extra={"session_id": "global"}
            )

    async def bootstrap(self) -> None:
        """Bootstrap the application."""
        # Call the parent bootstrap method first
        await super().bootstrap()

        # Add our session filter to the root logger and all existing handlers
        session_filter = SessionFilter()
        root_logger = logging.getLogger()
        root_logger.addFilter(session_filter)

        # Also add to all handlers
        for handler in root_logger.handlers:
            handler.addFilter(session_filter)

        logging.info(
            "Session filter added to ensure all logs have session_id",
            extra={"session_id": "global"},
        )

    def _register_command_handlers(self) -> None:
        """Register our demo command handlers."""
        # Register the calculator command handler
        self.message_bus.register_command_handler(
            "global", CalculateCommand, calculate_handler
        )

        # Register the log command handler
        self.message_bus.register_command_handler("global", LogCommand, log_handler)

        logging.info("Registered command handlers", extra={"session_id": "global"})

    def _register_event_handlers(self) -> None:
        """Register our demo event handlers."""
        # Register global event collector for all wrapped events
        self.message_bus.register_event_handler(
            "global", EventLogWrapper, self.global_collector.handle_event
        )

        logging.info("Registered event handlers", extra={"session_id": "global"})

    async def run_demo(self):
        """Run the main demo sequence."""
        # Display info about the demo
        print("Starting Session Bus Demo")
        print("=========================")
        print(f"Demo Name: {self.config.name}")
        print(f"Description: {self.config.description}")
        print(f"Log Directory: {self.config.file_handler_log_dir}")
        print(f"Log Filename: {self.config.file_handler_log_filename}")
        print(f"Tracing Enabled: {self.message_bus.tracing_enabled}\n")

        # Step 1: Sending events and commands without a session
        print("1. Sending events and commands without a session")
        print("-----------------------------------------------")

        # Send a greeting event without a session
        greeting = GreetingEvent(message="Hello, world!")
        await self.message_bus.publish(greeting)

        # Execute a calculation command without a session
        calc_cmd = CalculateCommand(operation="add", operands=[10, 20, 30])
        result = await self.message_bus.execute(calc_cmd)
        print(f"Calculation result: {result.result}")

        # Log something without a session
        log_cmd = LogCommand(message="This is a global log entry", level="info")
        await self.message_bus.execute(log_cmd)

        await asyncio.sleep(0.1)  # Allow events to be processed

        # Step 2: Creating and using Session A
        print("\n2. Creating Session A and using it")
        print("----------------------------------")

        # Create a session and work within it
        async with self.message_bus.create_session() as session_a:
            print(f"Session A created with ID: {session_a.session_id}")

            # Create a session-specific collector
            session_collector = EventCollector("Session A")
            session_a.register_event_handler(
                EventLogWrapper, session_collector.handle_event
            )

            # Send a greeting event within the session
            greeting = GreetingEvent(message="Hello from Session A!")
            await self.message_bus.publish(
                greeting
            )  # Should inherit session from context

            # Execute commands within the session
            calc_cmd = CalculateCommand(operation="multiply", operands=[2, 3, 4])
            result = await session_a.execute_with_session(calc_cmd)
            print(f"Session A calculation result: {result.result}")

            # Log something in the session
            log_cmd = LogCommand(message="This is a session log entry", level="info")
            await session_a.execute_with_session(log_cmd)

            await asyncio.sleep(0.1)  # Allow events to be processed

            # Display session collector summary
            session_collector.display_summary()

        # Step 3: Creating Session B with custom handler
        print("\n3. Creating Session B and demonstrating session isolation")
        print("-------------------------------------------------------")

        # Create another session to demonstrate isolation
        async with self.message_bus.create_session() as session_b:
            print(f"Session B created with ID: {session_b.session_id}")

            # Override the calculate handler for this session only
            async def custom_calculate_handler(
                command: CalculateCommand,
            ) -> CommandResult:
                """Custom handler that doubles the result."""
                # First use the original handler
                original_result = await calculate_handler(command)

                if original_result.success and original_result.result is not None:
                    # Double the result and modify the command result
                    doubled_result = original_result.result * 2

                    # Publish a notification about this
                    notification = NotificationEvent(
                        message=f"Result doubled in session B: {doubled_result}",
                        importance="high",
                    )
                    await self.message_bus.publish(notification)

                    return CommandResult(
                        success=True, original_command=command, result=doubled_result
                    )
                else:
                    return original_result

            # Register our custom handler just for this session
            session_b.register_command_handler(CalculateCommand, custom_calculate_handler)

            # Now execute the same calculation - should use our custom handler
            calc_cmd = CalculateCommand(operation="multiply", operands=[2, 3, 4])
            result = await session_b.execute_with_session(calc_cmd)
            print(f"Session B calculation result (should be doubled): {result.result}")

            await asyncio.sleep(0.1)  # Allow events to be processed

        # Step 4: Execute commands after sessions end
        print("\n4. Executing more commands after sessions have ended")
        print("--------------------------------------------------")

        # Sessions A and B are now closed, handlers should be unregistered

        # Execute another calculation - should use the global handler
        calc_cmd = CalculateCommand(operation="subtract", operands=[100, 20, 5])
        result = await self.message_bus.execute(calc_cmd)
        print(f"Global calculation result after sessions: {result.result}")

        await asyncio.sleep(0.1)  # Allow events to be processed

        # Display the global collector summary
        self.global_collector.display_summary()

        print("\nDemo completed.")
        log_dir = self.config.file_handler_log_dir
        log_file = self.config.file_handler_log_filename

        if self.config.enable_file_handler:
            print(f"Event logs written to: {log_dir}")
        else:
            print("File logging was not enabled.")

    async def shutdown(self) -> None:
        """Shutdown the application components."""
        # Close the primary session (using __aexit__ since it's an async context manager)
        if hasattr(self, "primary_session"):
            # Using __aexit__ directly as it's an async context manager
            await self.primary_session.__aexit__(None, None, None)

        # Stop message bus
        await self.message_bus.stop()

        logging.info("Application shutdown complete", extra={"session_id": "global"})


# --- Main entry point ---


async def main():
    """Main entry point for the session bus demo."""
    try:
        # Create the bootstrap with our custom config
        config = SessionDemoConfig()

        # You can enable or disable tracing here
        config.enable_tracing = False  # Uncomment to disable tracing

        # Create logs directory if it doesn't exist
        if config.enable_file_handler:
            os.makedirs(config.file_handler_log_dir, exist_ok=True)

        bootstrap = SessionDemoBootstrap(config)

        # Bootstrap the application (starts message bus, registers handlers)
        await bootstrap.bootstrap()

        # Run the demo
        await bootstrap.run_demo()

    except Exception as e:
        logging.exception("Error in demo: %s", str(e), extra={"session_id": "global"})
        raise
    finally:
        # Shutdown the application safely
        if "bootstrap" in locals():
            await bootstrap.shutdown()


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())
