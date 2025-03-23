"""Trace handlers for observability events.

This module provides handlers for processing trace events.
"""

import logging
from typing import Any, Dict, List, Optional, Type

from llmgine.observability.events import TraceEvent
from llmgine.observability.handlers.base import ObservabilityHandler

logger = logging.getLogger(__name__)


class ConsoleTraceHandler(ObservabilityHandler[TraceEvent]):
    """Handler for logging traces to console."""
    
    def __init__(self) -> None:
        """Initialize the console trace handler."""
        super().__init__()
        
    def _get_event_type(self) -> Type[TraceEvent]:
        """Get the event type this handler processes.
        
        Returns:
            The TraceEvent class
        """
        return TraceEvent
    
    async def handle(self, event: TraceEvent) -> None:
        """Handle the trace event by logging to console.
        
        Args:
            event: The trace event
        """
        if not self.enabled:
            return
            
        # For span start events
        if event.start_time and not event.end_time:
            logger.info(
                f"TRACE START: {event.name} [trace={event.span_context.trace_id[:8]}] " + 
                f"[span={event.span_context.span_id[:8]}]"
            )
            
        # For span end events
        elif event.end_time:
            duration = ""
            if event.duration_ms is not None:
                duration = f" ({event.duration_ms:.2f}ms)"
                
            logger.info(
                f"TRACE END: {event.name} [trace={event.span_context.trace_id[:8]}] " + 
                f"[span={event.span_context.span_id[:8]}] {event.status}{duration}"
            )


class InMemoryTraceHandler(ObservabilityHandler[TraceEvent]):
    """Handler for storing traces in memory."""
    
    def __init__(self, max_traces: int = 1000):
        """Initialize the in-memory trace handler.
        
        Args:
            max_traces: Maximum number of traces to store
        """
        super().__init__()
        self.max_traces = max_traces
        self._traces: Dict[str, Dict[str, Any]] = {}  # By span ID
        self._trace_trees: Dict[str, Dict[str, Any]] = {}  # By trace ID
        
    def _get_event_type(self) -> Type[TraceEvent]:
        """Get the event type this handler processes.
        
        Returns:
            The TraceEvent class
        """
        return TraceEvent
        
    async def handle(self, event: TraceEvent) -> None:
        """Handle the trace event by storing in memory.
        
        Args:
            event: The trace event
        """
        if not self.enabled:
            return
            
        span_id = event.span_context.span_id
        trace_id = event.span_context.trace_id
        
        # Create or update span
        if span_id not in self._traces:
            self._traces[span_id] = {
                "name": event.name,
                "trace_id": trace_id,
                "span_id": span_id,
                "parent_span_id": event.span_context.parent_span_id,
                "start_time": event.start_time,
                "end_time": None,
                "duration_ms": None,
                "attributes": dict(event.attributes) if event.attributes else {},
                "events": list(event.events) if event.events else [],
                "status": event.status
            }
        
        # Update span with end information
        if event.end_time:
            span = self._traces[span_id]
            span["end_time"] = event.end_time
            span["status"] = event.status
            
            # Calculate duration if possible
            if span["start_time"] and event.end_time:
                from datetime import datetime
                start = datetime.fromisoformat(span["start_time"])
                end = datetime.fromisoformat(event.end_time)
                span["duration_ms"] = (end - start).total_seconds() * 1000
        
        # Maintain trace tree structure
        if trace_id not in self._trace_trees:
            self._trace_trees[trace_id] = {
                "trace_id": trace_id,
                "spans": {},
                "root_spans": []
            }
            
        tree = self._trace_trees[trace_id]
        tree["spans"][span_id] = self._traces[span_id]
        
        # For spans without parents, add to root spans list
        if not event.span_context.parent_span_id and span_id not in tree["root_spans"]:
            tree["root_spans"].append(span_id)
            
        # Limit number of traces
        if len(self._trace_trees) > self.max_traces:
            oldest_trace_id = next(iter(self._trace_trees))
            del self._trace_trees[oldest_trace_id]
            
            # Clean up spans for the deleted trace
            for span_id in list(self._traces.keys()):
                if self._traces[span_id]["trace_id"] == oldest_trace_id:
                    del self._traces[span_id]
    
    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get a trace tree by trace ID.
        
        Args:
            trace_id: The trace ID to retrieve
            
        Returns:
            Trace tree or None if not found
        """
        return self._trace_trees.get(trace_id)
    
    def get_span(self, span_id: str) -> Optional[Dict[str, Any]]:
        """Get a span by span ID.
        
        Args:
            span_id: The span ID to retrieve
            
        Returns:
            Span data or None if not found
        """
        return self._traces.get(span_id)
    
    def get_recent_traces(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent traces.
        
        Args:
            limit: Maximum number of traces to return
            
        Returns:
            List of trace trees
        """
        return list(self._trace_trees.values())[-limit:]