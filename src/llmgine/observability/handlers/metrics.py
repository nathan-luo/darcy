"""Metrics handlers for observability events.

This module provides handlers for processing metric events.
"""

import logging
from typing import Any, Dict, List, Optional, Type

from llmgine.observability.events import MetricEvent
from llmgine.observability.handlers.base import ObservabilityHandler

logger = logging.getLogger(__name__)


class ConsoleMetricsHandler(ObservabilityHandler[MetricEvent]):
    """Handler for logging metrics to console."""
    
    def __init__(self) -> None:
        """Initialize the console metrics handler."""
        super().__init__()
        
    def _get_event_type(self) -> Type[MetricEvent]:
        """Get the event type this handler processes.
        
        Returns:
            The MetricEvent class
        """
        return MetricEvent
    
    async def handle(self, event: MetricEvent) -> None:
        """Handle the metric event by logging to console.
        
        Args:
            event: The metric event
        """
        if not self.enabled:
            return
            
        for metric in event.metrics:
            unit_str = f" {metric.unit}" if metric.unit else ""
            tags_str = " " + " ".join(f"{k}={v}" for k, v in metric.tags.items()) if metric.tags else ""
            
            # Format: METRIC name=value unit [tags...]
            logger.info(f"METRIC {metric.name}={metric.value}{unit_str}{tags_str}")


class InMemoryMetricsHandler(ObservabilityHandler[MetricEvent]):
    """Handler for storing metrics in memory."""
    
    def __init__(self, max_metrics: int = 1000):
        """Initialize the in-memory metrics handler.
        
        Args:
            max_metrics: Maximum number of metrics to store
        """
        super().__init__()
        self.max_metrics = max_metrics
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}
        
    def _get_event_type(self) -> Type[MetricEvent]:
        """Get the event type this handler processes.
        
        Returns:
            The MetricEvent class
        """
        return MetricEvent
        
    async def handle(self, event: MetricEvent) -> None:
        """Handle the metric event by storing in memory.
        
        Args:
            event: The metric event
        """
        if not self.enabled:
            return
            
        for metric in event.metrics:
            # Create a unique key based on name and tags
            tags_key = frozenset(sorted(metric.tags.items())) if metric.tags else None
            metric_key = f"{metric.name}:{tags_key}"
            
            # Store current value
            self._metrics[metric_key] = {
                "name": metric.name,
                "value": metric.value,
                "unit": metric.unit,
                "tags": dict(metric.tags) if metric.tags else {},
                "timestamp": event.timestamp
            }
            
            # Store history
            if metric_key not in self._history:
                self._history[metric_key] = []
                
            history = self._history[metric_key]
            history.append(self._metrics[metric_key])
            
            # Trim history if needed
            if len(history) > self.max_metrics:
                history.pop(0)
    
    def get_metric(self, name: str, tags: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Get the current value of a metric.
        
        Args:
            name: Metric name
            tags: Optional tags to match
            
        Returns:
            Metric data or None if not found
        """
        tags_key = frozenset(sorted(tags.items())) if tags else None
        metric_key = f"{name}:{tags_key}"
        return self._metrics.get(metric_key)
    
    def get_metric_history(self, name: str, tags: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Get the history of a metric.
        
        Args:
            name: Metric name
            tags: Optional tags to match
            
        Returns:
            List of metric data points
        """
        tags_key = frozenset(sorted(tags.items())) if tags else None
        metric_key = f"{name}:{tags_key}"
        return self._history.get(metric_key, [])