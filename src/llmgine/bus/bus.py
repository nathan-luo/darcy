"""Core message bus implementation for handling commands and events.

The message bus is the central communication mechanism in the application,
providing a way for components to communicate without direct dependencies.
"""

import asyncio
import logging
import traceback
import uuid
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast
from dataclasses import asdict
from enum import Enum
import contextvars

from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

# Import only what's needed at the module level and use local imports for the rest
# to avoid circular dependencies
from llmgine.bus.session import BusSession
from llmgine.observability.handlers.base import ObservabilityEventHandler


# Get the base logger and wrap it with the adapter
logger = logging.getLogger(__name__)

# Context variable to hold the current session ID
trace: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace", default=None
)
span: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "span", default=None
)

TCommand = TypeVar("TCommand", bound=Command)
TEvent = TypeVar("TEvent", bound=Event)
CommandHandler = Callable[[TCommand], CommandResult]
AsyncCommandHandler = Callable[[TCommand], "asyncio.Future[CommandResult]"]
EventHandler = Callable[[TEvent], None]
AsyncEventHandler = Callable[[TEvent], "asyncio.Future[None]"]


class MessageBus:
    """Async message bus for command and event handling (Singleton).

    This is a simplified implementation of the Command Bus and Event Bus patterns,
    allowing for decoupled communication between components.
    """

    # --- Singleton Pattern ---
    _instance: Optional["MessageBus"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "MessageBus":
        """
        Ensure only one instance is created (Singleton pattern).
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """
        Initialize the message bus (only once).
        Sets up handler storage, event queue, and observability handlers.
        """
        if getattr(self, "_initialized", False):
            return

        self._command_handlers: Dict[str, Dict[Type[Command], AsyncCommandHandler]] = {}
        self._event_handlers: Dict[str, Dict[Type[Event], List[AsyncEventHandler]]] = {}
        self._event_queue: Optional[asyncio.Queue] = None
        self._processing_task: Optional[asyncio.Task] = None
        self._observability_handlers: List[ObservabilityEventHandler] = []

        logger.info("MessageBus initialized")
        self._initialized = True

    def register_observability_handler(self, handler: ObservabilityEventHandler) -> None:
        """
        Register an observability handler for this message bus.
        Registers the handler for both general and specific observability events.
        """
        self._observability_handlers.append(handler)

    def create_session(self, id: Optional[str] = None) -> BusSession:
        """
        Create a new session for grouping related commands and events.
        Args:
            id: Optional session identifier. If not provided, one will be generated.
        Returns:
            A new BusSession instance.
        """
        return BusSession(id=id)

    async def start(self) -> None:
        """
        Start the message bus event processing loop.
        Creates the event queue and launches the event processing task if not already running.
        """
        if self._processing_task is None:
            if self._event_queue is None:
                self._event_queue = asyncio.Queue()
                logger.info("Event queue created")

            if self._event_queue is not None:
                self._processing_task = asyncio.create_task(self._process_events())
                logger.info("MessageBus started")
            else:
                logger.error("Failed to create event queue, MessageBus cannot start")
        else:
            logger.warning("MessageBus already running")

    async def stop(self) -> None:
        """
        Stop the message bus event processing loop.
        Cancels the event processing task and cleans up.
        """
        if self._processing_task:
            logger.info("Stopping message bus...")
            self._processing_task.cancel()
            try:
                await asyncio.wait_for(self._processing_task, timeout=2.0)
                logger.info("MessageBus stopped successfully")
            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.warning(f"MessageBus stop issue: {type(e).__name__}")
            except Exception as e:
                logger.exception(f"Error during MessageBus shutdown: {e}")
            finally:
                self._processing_task = None
        else:
            logger.info("MessageBus already stopped or never started")

    def register_command_handler(
        self,
        session_id: str,
        command_type: Type[TCommand],
        handler: CommandHandler,
    ) -> None:
        """
        Register a command handler for a specific command type and session.
        Args:
            session_id: The session identifier (or 'GLOBAL').
            command_type: The type of command to handle.
            handler: The handler function/coroutine.
        Raises:
            ValueError: If a handler is already registered for the command in this session.
        """
        session_id = session_id or "GLOBAL"

        if session_id not in self._command_handlers:
            self._command_handlers[session_id] = {}

        async_handler = self._wrap_handler_as_async(handler)

        if command_type in self._command_handlers[session_id]:
            raise ValueError(
                f"Command handler for {command_type.__name__} already registered in session {session_id}"
            )

        self._command_handlers[session_id][command_type] = async_handler
        logger.debug(
            f"Registered command handler for {command_type.__name__} in session {session_id}"
        ) # TODO test

    def register_event_handler(
        self, session_id: str, event_type: Type[TEvent], handler: EventHandler
    ) -> None:
        """
        Register an event handler for a specific event type and session.
        Args:
            session_id: The session identifier (or 'global').
            event_type: The type of event to handle.
            handler: The handler function/coroutine.
        """
        session_id = session_id or "GLOBAL"

        if session_id not in self._event_handlers:
            self._event_handlers[session_id] = {}

        if event_type not in self._event_handlers[session_id]:
            self._event_handlers[session_id][event_type] = []

        async_handler = self._wrap_handler_as_async(handler)
        self._event_handlers[session_id][event_type].append(async_handler)
        logger.debug(
            f"Registered event handler for {event_type.__name__} in session {session_id}"
        )

    def unregister_session_handlers(self, session_id: str) -> None:
        """
        Unregister all command and event handlers for a specific session.
        Args:
            session_id: The session identifier.
        """
        if session_id not in self._command_handlers:
            logger.debug(f"No command handlers to unregister for session {session_id}")
            return

        if session_id in self._command_handlers:
            num_cmd_handlers = len(self._command_handlers[session_id])
            del self._command_handlers[session_id]
            logger.debug(
                f"Unregistered {num_cmd_handlers} command handlers for session {session_id}"
            )

        if session_id in self._event_handlers:
            num_event_handlers = sum(
                len(handlers) for handlers in self._event_handlers[session_id].values()
            )
            del self._event_handlers[session_id]
            logger.debug(
                f"Unregistered {num_event_handlers} event handlers for session {session_id}"
            )

    def unregister_command_handler(
        self, command_type: Type[TCommand], session_id: str = "GLOBAL"
    ) -> None:
        """
        Unregister a command handler for a specific command type and session.
        Args:
            command_type: The type of command.
            session_id: The session identifier (default 'global').
        """
        if session_id in self._command_handlers:
            if command_type in self._command_handlers[session_id]:
                del self._command_handlers[session_id][command_type]
                logger.debug(
                    f"Unregistered command handler for {command_type.__name__} in session {session_id}"
                )

    def unregister_event_handler(
        self, event_type: Type[TEvent], session_id: str = "GLOBAL"
    ) -> None:
        """
        Unregister an event handler for a specific event type and session.
        Args:
            event_type: The type of event.
            session_id: The session identifier (default 'global').
        """
        if session_id in self._event_handlers:
            if event_type in self._event_handlers[session_id]:
                del self._event_handlers[session_id][event_type]
                logger.debug(
                    f"Unregistered event handler for {event_type.__name__} in session {session_id}"
                )

    # --- Command Execution and Event Publishing ---

    async def execute(self, command: Command) -> CommandResult:
        """
        Execute a command and return its result.
        Args:
            command: The command instance to execute.
        Returns:
            CommandResult: The result of command execution.
        Raises:
            ValueError: If no handler is registered for the command type.
        """
        command_type = type(command)
        session_id = command.session_id or "GLOBAL"
        handler = None
        if session_id in self._command_handlers:
            handler = self._command_handlers[session_id].get(command_type)

        # Default to global handlers if no session-specific handler is found
        if handler is None and "GLOBAL" in self._command_handlers:
            handler = self._command_handlers["GLOBAL"].get(command_type)
            logger.warning(f"Using global command handler for {command_type.__name__} in session {session_id}")

        if handler is None:
            logger.error(
                f"No handler registered for command type {command_type.__name__}"
            )
            raise ValueError(f"No handler registered for command {command_type.__name__}")

        try:
            logger.info(f"Executing command {command_type.__name__}")
            result = await handler(command)
            logger.info(f"Command {command_type.__name__} executed successfully")
            return result

        except Exception as e:
            logger.exception(f"Error executing command {command_type.__name__}: {e}")
            failed_result = CommandResult(
                success=False,
                original_command=command,
                error=f"{type(e).__name__}: {str(e)}",
                metadata={"exception_details": traceback.format_exc()},
            )
            return failed_result


    async def publish(self, event: Event) -> None:
        """
        Publish an event onto the event queue.
        Args:
            event: The event instance to publish.
        """
        if hasattr(event, "session_id") and event.session_id is None:
            session_id = current_session_id.get()
            if session_id:
                event.session_id = session_id

        event_session_id = getattr(event, "session_id", None)
        if (
            hasattr(event, "metadata")
            and isinstance(event.metadata, dict)
            and event_session_id
        ):
            event.metadata.setdefault("session_id", event_session_id)

        logger.info(f"Publishing event {type(event).__name__}")
        for handler in self._observability_handlers:
            await handler.handle(event)

        try:
            await self._event_queue.put(event)
            logger.debug(f"Queued event: {type(event).__name__}")
        except Exception as e:
            logger.error(f"Error during event publishing: {e}", exc_info=True)

    async def _process_events(self) -> None:
        """
        Process events from the queue indefinitely.
        Handles each event by dispatching to registered handlers.
        """
        logger.info("Event processing loop starting")

        while True:
            try:
                event = await self._event_queue.get()
                logger.debug(f"Dequeued event {type(event).__name__}")

                try:
                    await self._handle_event(event)
                except asyncio.CancelledError:
                    logger.warning("Event handling cancelled")
                    raise
                except Exception:
                    logger.exception(f"Error processing event {type(event).__name__}")
                finally:
                    self._event_queue.task_done()

            except asyncio.CancelledError:
                logger.info("Event processing loop cancelled")
                break
            except Exception as e:
                logger.exception(f"Error in event processing loop: {e}")
                await asyncio.sleep(0.1)

        logger.info("Event processing loop finished")

    async def _handle_event(self, event: Event) -> None:
        """
        Handle a single event by calling all registered handlers.
        Args:
            event: The event instance to handle.
        """
        event_type = type(event)
        handlers_to_run = []
        event_session_id = getattr(event, "session_id", None)

        session_token = None
        if event_session_id:
            session_token = current_session_id.set(event_session_id)

        if event_session_id and event_session_id in self._event_handlers:
            for registered_type, handlers in self._event_handlers[event_session_id].items():
                if issubclass(event_type, registered_type):
                    handlers_to_run.extend(handlers)

        if "global" in self._event_handlers:
            for registered_type, handlers in self._event_handlers["global"].items():
                if issubclass(event_type, registered_type):
                    handlers_to_run.extend([
                        h for h in handlers if h not in handlers_to_run
                    ])

        try:
            if handlers_to_run:
                logger.debug(
                    f"Dispatching event {event_type.__name__} to {len(handlers_to_run)} handlers"
                )
                tasks = [asyncio.create_task(handler(event)) for handler in handlers_to_run]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        handler_name = getattr(
                            handlers_to_run[i], "__qualname__", repr(handlers_to_run[i])
                        )
                        logger.exception(
                            f"Error in handler '{handler_name}' for {event_type.__name__}: {result}"
                        )
            else:
                logger.debug(f"No handlers for event type {event_type.__name__}")
        except Exception as e:
            logger.exception(f"Error handling event {event_type.__name__}")
        finally:
            if session_token is not None:
                current_session_id.reset(session_token)

    def _wrap_handler_as_async(self, handler: Callable) -> Callable:
        """
        Convert synchronous handlers to asynchronous if needed.
        Args:
            handler: The handler function or coroutine.
        Returns:
            An async-compatible handler.
        """
        if asyncio.iscoroutinefunction(handler):
            return handler

        async def async_wrapper(*args, **kwargs):
            return handler(*args, **kwargs)

        return async_wrapper

    def _event_to_dict(self, event: Any) -> Dict[str, Any]:
        """
        Convert an event to a dictionary for serialization.
        Tries custom to_dict, dataclasses.asdict, __dict__, or falls back to repr.
        Args:
            event: The event object to serialize.
        Returns:
            A dictionary representation of the event.
        """
        if hasattr(event, "to_dict") and callable(event.to_dict):
            try:
                return event.to_dict()
            except Exception:
                logger.warning(f"Error calling to_dict on {type(event)}", exc_info=True)

        try:
            return asdict(
                event, dict_factory=lambda x: {k: self._convert_value(v) for k, v in x}
            )
        except TypeError:
            pass

        if hasattr(event, "__dict__"):
            return {
                k: self._convert_value(v)
                for k, v in event.__dict__.items()
                if not k.startswith("_")
            }

        logger.warning(f"Could not serialize {type(event)} to dict, using repr()")
        return {"event_repr": repr(event)}

    def _convert_value(self, value: Any) -> Any:
        """
        Convert values for serialization, handling enums, containers, and objects.
        Args:
            value: The value to convert.
        Returns:
            A serializable representation of the value.
        """
        if isinstance(value, Enum):
            return value.value
        elif isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, dict):
            return {str(k): self._convert_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple, set)):
            return [self._convert_value(item) for item in value]
        elif hasattr(value, "to_dict") and callable(value.to_dict):
            try:
                return value.to_dict()
            except Exception:
                pass
        elif hasattr(value, "__dict__") or hasattr(value, "__dataclass_fields__"):
            return self._event_to_dict(value)
        else:
            try:
                return str(value)
            except Exception:
                return repr(value)
