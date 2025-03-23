"""Base classes for observability handlers.

This module defines the base handler interface for observability events.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from llmgine.observability.events import BaseEvent

TEvent = TypeVar("TEvent", bound=BaseEvent)


class ObservabilityHandler(Generic[TEvent], ABC):
    """Base class for all observability handlers.
    
    Handlers subscribe to and process events from the ObservabilityBus.
    """
    
    def __init__(self) -> None:
        """Initialize the handler."""
        self.enabled = True
        
    @property
    def event_type(self) -> Type[TEvent]:
        """Get the event type this handler processes.
        
        Returns:
            The event type class
        """
        return self._get_event_type()
    
    @abstractmethod
    def _get_event_type(self) -> Type[TEvent]:
        """Get the event type this handler processes.
        
        Returns:
            The event type class
        """
        pass
        
    @abstractmethod
    async def handle(self, event: TEvent) -> None:
        """Handle the event.
        
        Args:
            event: The event to handle
        """
        pass
    
    def handle_sync(self, event: TEvent) -> None:
        """Handle the event synchronously.
        
        Args:
            event: The event to handle
        """
        if not self.enabled:
            return
            
        try:
            # Convert from sync to async if needed
            if asyncio.iscoroutinefunction(self.handle):
                asyncio.create_task(self.handle(event))
            else:
                # This shouldn't happen since handle is defined as async
                pass
        except Exception as e:
            # Don't let handler errors affect the bus
            print(f"Error in handler {self.__class__.__name__}: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert handler to a dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "handler_type": self.__class__.__name__,
            "event_type": self.event_type.__name__,
            "enabled": self.enabled
        }
    
    def __repr__(self) -> str:
        """Get string representation.
        
        Returns:
            String representation
        """
        return f"{self.__class__.__name__}(enabled={self.enabled})"