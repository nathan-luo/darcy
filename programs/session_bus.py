#!/usr/bin/env python3
"""
Session Bus Demo

This program demonstrates the session-based message bus functionality.
It creates multiple sessions with their own handlers and shows:
1. Session-specific event handling
2. Session-specific command handling
3. Automatic cleanup when sessions end
"""

import asyncio
import logging
import sys
import traceback
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from llmgine.bus.bus import MessageBus

# Directly import BusSession now
# from llmgine.bus.session import BusSession
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event


# Configure logging
class SessionAdapter(logging.LoggerAdapter):
    """Logger adapter that ensures session_id is always present."""

    def process(self, msg, kwargs):
        # Ensure 'extra' exists in kwargs
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        # Ensure 'session_id' exists in extra
        if "session_id" not in kwargs["extra"]:
            kwargs["extra"]["session_id"] = "unknown"
        return msg, kwargs


# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(session_id)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Create logger with adapter for session ID
base_logger = logging.getLogger("session_demo")
logger = SessionAdapter(base_logger, {})


# ----- Define Commands and Events for the Demo -----


@dataclass
class GreetCommand(Command):
    """Command to greet someone."""

    name: str = "World"
    greeting_type: str = "Hello"


@dataclass
class CalculateCommand(Command):
    """Command to perform a calculation."""

    operation: str = "add"
    operands: List[float] = field(default_factory=list)


@dataclass
class UserEvent(Event):
    """Event related to user actions."""

    user_id: str = ""
    action: str = ""


@dataclass
class SystemEvent(Event):
    """Event related to system actions."""

    component: str = ""
    action: str = ""
    severity: str = "info"


# ----- Command Handlers -----


def greet_handler(command: GreetCommand) -> CommandResult:
    """Handle the greeting command."""
    logger.info(
        f"{command.greeting_type}, {command.name}!",
        extra={"session_id": command.session_id or "unknown"},
    )
    return CommandResult(
        success=True,
        original_command=command,
        result=f"{command.greeting_type}, {command.name}!",
    )


def calculate_handler(command: CalculateCommand) -> CommandResult:
    """Handle the calculate command."""
    result = None
    error = None

    try:
        if command.operation == "add":
            result = sum(command.operands)
        elif command.operation == "multiply":
            result = 1
            for num in command.operands:
                result *= num
        elif command.operation == "subtract":
            if len(command.operands) < 2:
                raise ValueError("Subtraction requires at least 2 operands")
            result = command.operands[0]
            for num in command.operands[1:]:
                result -= num
        else:
            raise ValueError(f"Unknown operation: {command.operation}")

        logger.info(
            f"Calculation result: {result}",
            extra={"session_id": command.session_id or "unknown"},
        )
    except Exception as e:
        error = str(e)
        logger.error(
            f"Calculation error: {error}",
            extra={"session_id": command.session_id or "unknown"},
        )

    return CommandResult(
        success=error is None, original_command=command, result=result, error=error
    )


# ----- Event Handlers -----


def user_event_handler(event: UserEvent) -> None:
    """Handle user events."""
    logger.info(
        f"User {event.user_id} performed action: {event.action}",
        extra={"session_id": event.session_id or "unknown"},
    )


def system_event_handler(event: SystemEvent) -> None:
    """Handle system events."""
    logger.info(
        f"System component {event.component} performed action: {event.action} [severity: {event.severity}]",
        extra={"session_id": event.session_id or "unknown"},
    )


def global_event_handler(event: Event) -> None:
    """Handle all events globally."""
    logger.info(
        f"GLOBAL HANDLER: Received event of type {type(event).__name__}",
        extra={"session_id": event.session_id or "unknown"},
    )


# ----- Remove the AsyncBusSession class -----
# class AsyncBusSession:
#     """Async context manager wrapper for BusSession with better error handling."""

#     def __init__(self, bus):
#         self.bus = bus
#         self.session = None

#     async def __aenter__(self):
#         """Async enter the context."""
#         try:
#             self.session = self.bus.create_session()
#             # Enter the sync context manager
#             self.session.__enter__()
#             return self.session
#         except Exception as e:
#             logger.error(f"Error creating session: {e}", exc_info=True)
#             raise

#     async def __aexit__(self, exc_type, exc_val, exc_tb):
#         """Async exit the context with proper cleanup."""
#         if not self.session:
#             return

#         try:
#             # Exit the sync context manager
#             self.session.__exit__(exc_type, exc_val, exc_tb)
#             # Short wait for event processing to complete
#             await asyncio.sleep(0.1)
#             logger.info(
#                 f"Session {self.session.session_id} closed successfully",
#                 extra={"session_id": self.session.session_id}
#             )
#         except asyncio.CancelledError:
#             logger.warning(
#                 f"Session {self.session.session_id} cleanup interrupted",
#                 extra={"session_id": self.session.session_id}
#             )
#         except Exception as e:
#             logger.error(
#                 f"Error closing session: {e}",
#                 extra={"session_id": getattr(self.session, "session_id", "unknown")},
#                 exc_info=True
#             )


# ----- Main Demo Function with Improved Error Handling -----
async def run_demo() -> None:
    """Run the session bus demo with proper async handling."""
    # Get the message bus singleton
    bus = MessageBus()

    # Flag to track if bus was started
    bus_started = False

    try:
        # Start the message bus processing
        await bus.start()
        bus_started = True
        logger.info("Message bus started", extra={"session_id": "global"})

        # Register a global event handler for all events
        bus.register_event_handler("global", Event, global_event_handler)
        logger.info("Registered global event handler", extra={"session_id": "global"})

        # ----- Session 1: User Session -----
        logger.info("Starting Session 1 (User Session)", extra={"session_id": "global"})

        # Use async with bus.create_session() directly
        async with bus.create_session() as user_session:
            session_id = user_session.session_id
            logger.info(
                f"Created User Session with ID: {session_id}",
                extra={"session_id": session_id},
            )

            # Register session-specific handlers
            user_session.register_event_handler(UserEvent, user_event_handler)
            user_session.register_command_handler(GreetCommand, greet_handler)
            logger.info(
                "Registered handlers for user session", extra={"session_id": session_id}
            )

            # Execute commands in this session
            greet_cmd = GreetCommand(name="User", greeting_type="Welcome")
            logger.info("Executing greeting command", extra={"session_id": session_id})
            try:
                # Use await user_session.execute_with_session
                result = await user_session.execute_with_session(greet_cmd)
                logger.info(
                    f"Greeting result: {result.result}", extra={"session_id": session_id}
                )
            except Exception as e:
                logger.error(
                    f"Error executing greeting command: {e}",
                    extra={"session_id": session_id},
                    exc_info=True,
                )

            # Publish events in this session with proper awaiting
            try:
                user_event = UserEvent(user_id="user123", action="login")
                user_event.session_id = session_id
                logger.info("Publishing user event", extra={"session_id": session_id})
                await bus.publish(user_event)
                logger.info("User event published", extra={"session_id": session_id})

                # Wait a moment for event processing
                await asyncio.sleep(0.1)

                # This session also publishes a system event, which it doesn't handle directly
                system_event = SystemEvent(
                    component="auth", action="user_authenticated", severity="info"
                )
                system_event.session_id = session_id
                logger.info("Publishing system event", extra={"session_id": session_id})
                await bus.publish(system_event)
                logger.info("System event published", extra={"session_id": session_id})

                # Wait a moment for event processing
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(
                    f"Error publishing events: {e}",
                    extra={"session_id": session_id},
                    exc_info=True,
                )

            logger.info("User session work complete", extra={"session_id": session_id})
            # Session will be closed by the context manager

        logger.info("User Session ended", extra={"session_id": "global"})

        # ----- Session 2: System Session -----
        logger.info("Starting Session 2 (System Session)", extra={"session_id": "global"})

        # Use async with bus.create_session() directly
        async with bus.create_session() as system_session:
            session_id = system_session.session_id
            logger.info(
                f"Created System Session with ID: {session_id}",
                extra={"session_id": session_id},
            )

            # Register session-specific handlers
            system_session.register_event_handler(SystemEvent, system_event_handler)
            system_session.register_command_handler(CalculateCommand, calculate_handler)
            logger.info(
                "Registered handlers for system session", extra={"session_id": session_id}
            )

            # Execute commands in this session
            try:
                calc_cmd = CalculateCommand(operation="add", operands=[10, 20, 30])
                logger.info(
                    "Executing calculation command", extra={"session_id": session_id}
                )
                # Use await system_session.execute_with_session
                result = await system_session.execute_with_session(calc_cmd)
                logger.info(
                    f"Calculation result: {result.result}",
                    extra={"session_id": session_id},
                )

                # Try another calculation with error
                calc_cmd = CalculateCommand(operation="divide", operands=[10, 0])
                logger.info(
                    "Executing invalid calculation", extra={"session_id": session_id}
                )
                # Use await system_session.execute_with_session
                result = await system_session.execute_with_session(calc_cmd)
                logger.info(
                    f"Expected calculation error: {result.error}",
                    extra={"session_id": session_id},
                )
            except Exception as e:
                logger.error(
                    f"Error executing calculation: {e}",
                    extra={"session_id": session_id},
                    exc_info=True,
                )

            # Publish events in this session
            try:
                system_event = SystemEvent(
                    component="processor", action="calculation_completed", severity="info"
                )
                system_event.session_id = session_id
                logger.info("Publishing system event", extra={"session_id": session_id})
                await bus.publish(system_event)
                logger.info("System event published", extra={"session_id": session_id})

                # Wait a moment for event processing
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(
                    f"Error publishing event: {e}",
                    extra={"session_id": session_id},
                    exc_info=True,
                )

            logger.info("System session work complete", extra={"session_id": session_id})
            # Session will be closed by the context manager

        logger.info("System Session ended", extra={"session_id": "global"})

        # Final demonstration with unregistered handlers
        logger.info(
            "Final demonstration with unregistered handlers:",
            extra={"session_id": "global"},
        )

        # Create events of both types without session IDs
        try:
            user_event = UserEvent(user_id="user456", action="logout")
            system_event = SystemEvent(
                component="app", action="shutdown", severity="info"
            )

            # These should only be handled by the global handler now
            logger.info("Publishing final events", extra={"session_id": "global"})
            await bus.publish(user_event)
            logger.info("Final user event published", extra={"session_id": "global"})

            await bus.publish(system_event)
            logger.info("Final system event published", extra={"session_id": "global"})

            # Wait for final events to be processed
            logger.info(
                "Waiting for final event processing...", extra={"session_id": "global"}
            )
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(
                f"Error in final demonstration: {e}",
                extra={"session_id": "global"},
                exc_info=True,
            )

        logger.info("Demo completed successfully!", extra={"session_id": "global"})

    except asyncio.CancelledError:
        logger.info("Demo was cancelled", extra={"session_id": "global"})
    except Exception as e:
        logger.error(
            f"Demo failed with error: {e}", extra={"session_id": "global"}, exc_info=True
        )
    finally:
        # Stop the message bus if it was started
        if bus_started:
            try:
                logger.info("Stopping message bus", extra={"session_id": "global"})
                await bus.stop()
                logger.info("Message bus stopped", extra={"session_id": "global"})
            except Exception as e:
                logger.error(
                    f"Error stopping message bus: {e}",
                    extra={"session_id": "global"},
                    exc_info=True,
                )


if __name__ == "__main__":
    try:
        # Run with a shorter timeout to prevent long hanging
        asyncio.run(asyncio.wait_for(run_demo(), timeout=5.0))
    except asyncio.TimeoutError:
        logger.error("Demo timed out after 5 seconds", extra={"session_id": "global"})
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user", extra={"session_id": "global"})
        sys.exit(0)
    except Exception as e:
        logger.error(f"Demo failed: {e}", extra={"session_id": "global"})
        sys.exit(1)
