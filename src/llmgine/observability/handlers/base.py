"""Base class for event observability handlers."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from llmgine.messages.events import Event


class ObservabilityEventHandler(ABC):
    """Base class for handlers that process events from the MessageBus for observability purposes."""

    def __init__(self, **kwargs: Any) -> None:
        # Allow for configuration parameters
        pass

    @abstractmethod
    async def handle(self, event: Event) -> None:
        """Process an incoming event.

        Args:
            event: The event received from the MessageBus.
        """
        pass

    def event_to_dict(self, event: Any) -> Dict[str, Any]:
        """Convert an event to a dictionary representation for logging.

        Args:
            event: The event to convert

        Returns:
            Dictionary representation of the event
        """
        # Use to_dict method if available
        if hasattr(event, "to_dict") and callable(event.to_dict):
            try:
                return event.to_dict()
            except Exception:
                pass

        # Try dataclasses.asdict
        try:
            from dataclasses import asdict

            return asdict(event)
        except (TypeError, ImportError):
            pass

        # Use __dict__
        if hasattr(event, "__dict__"):
            return {k: v for k, v in event.__dict__.items() if not k.startswith("_")}

        # Fallback
        return {"event_repr": repr(event)}

    def __repr__(self) -> str:
        """Get string representation."""
        return f"{self.__class__.__name__}()"
