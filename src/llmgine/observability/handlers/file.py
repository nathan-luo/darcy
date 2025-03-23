"""File handlers for observability events.

This module provides handlers for logging events to files.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from dataclasses import asdict

from llmgine.observability.events import BaseEvent
from llmgine.observability.handlers.base import ObservabilityHandler

logger = logging.getLogger(__name__)


class JsonFileHandler(ObservabilityHandler[BaseEvent]):
    """Handler for logging all events to a JSON file."""

    def __init__(self, log_dir: str = "logs", filename: Optional[str] = None):
        """Initialize the JSON file handler.

        Args:
            log_dir: Directory to write log files
            filename: Optional specific filename, if None uses timestamp
        """
        super().__init__()
        self.log_dir = Path(log_dir)

        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)

        # Create a log file
        if filename:
            self.log_file = self.log_dir / filename
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = self.log_dir / f"llmgine_{timestamp}.jsonl"

        # Create a lock for file access
        self._file_lock = asyncio.Lock()

        logger.info(f"JsonFileHandler initialized with log file: {self.log_file}")

    def _get_event_type(self) -> Type[BaseEvent]:
        """Get the event type this handler processes.

        Returns:
            The BaseEvent class
        """
        return BaseEvent

    async def handle(self, event: BaseEvent) -> None:
        """Handle the event by writing to a JSON file.

        Args:
            event: The event to handle
        """
        if not self.enabled:
            return

        try:
            # Convert the event to a dictionary
            event_dict = self._event_to_dict(event)

            # Add event type to the dictionary
            event_dict["event_type"] = type(event).__name__

            # Write to file with proper locking to avoid conflicts
            async with self._file_lock:
                with open(self.log_file, "a") as f:
                    f.write(json.dumps(event_dict) + "\n")
        except Exception as e:
            logger.exception(f"Error writing event to file: {e}")

    def _event_to_dict(self, event: Any) -> Dict[str, Any]:
        """Convert an event to a dictionary for serialization.

        Args:
            event: The event to convert

        Returns:
            Dictionary representation of the event
        """
        if hasattr(event, "__dict__"):
            # Handle basic attributes
            result = dict(event.__dict__)

            # Handle enum values and nested objects
            for key, value in list(result.items()):
                if isinstance(value, Enum):
                    result[key] = value.value
                elif hasattr(value, "__dict__"):
                    # Handle nested objects
                    result[key] = self._event_to_dict(value)
                elif isinstance(value, list):
                    # Handle lists of objects
                    result[key] = [
                        self._event_to_dict(item) if hasattr(item, "__dict__") else item
                        for item in value
                    ]

            return result

        # For dataclasses that don't use __dict__
        try:
            return asdict(event)
        except:
            pass

        # Fallback
        return {"type": str(type(event))}

    def to_dict(self) -> Dict[str, Any]:
        """Convert handler to a dictionary for serialization.

        Returns:
            Dictionary representation
        """
        base_dict = super().to_dict()
        base_dict["log_dir"] = str(self.log_dir)
        base_dict["log_file"] = str(self.log_file)
        return base_dict
