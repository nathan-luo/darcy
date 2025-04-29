import json
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Union


def load_logs(file_path: str) -> List[Dict]:
    """Load and parse logs from a file."""
    logs = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return logs


def filter_logs(
    logs: List[Dict],
    level: Optional[str] = None,
    event_type: Optional[str] = None,
    after: Optional[datetime] = None,
    before: Optional[datetime] = None,
    source: Optional[str] = None,
    component: Optional[str] = None,
    message_contains: Optional[str] = None,
) -> List[Dict]:
    """Filter logs based on various criteria."""
    filtered = logs

    if level:
        filtered = [log for log in filtered if log.get("level") == level]

    if event_type:
        filtered = [log for log in filtered if log.get("event_type") == event_type]

    if after:
        filtered = [
            log for log in filtered if datetime.fromisoformat(log["timestamp"]) >= after
        ]

    if before:
        filtered = [
            log for log in filtered if datetime.fromisoformat(log["timestamp"]) <= before
        ]

    if source:
        filtered = [log for log in filtered if source in log.get("source", "")]

    if component:
        filtered = [
            log
            for log in filtered
            if component == log.get("context", {}).get("component", None)
        ]

    if message_contains:
        filtered = [
            log
            for log in filtered
            if message_contains.lower() in log.get("message", "").lower()
        ]

    return filtered


def get_unique_values(logs: List[Dict], field: str) -> Set:
    """Get unique values for a specific field in logs."""
    values = set()
    for log in logs:
        if field in log:
            values.add(log[field])
        elif "." in field:
            # Handle nested fields
            parts = field.split(".")
            current = log
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    current = None
                    break
            if current is not None:
                values.add(current)
    return values


def get_trace_tree(logs: List[Dict], trace_id: str) -> Dict:
    """Build a tree of spans for a specific trace."""
    # Filter logs for the specific trace
    trace_logs = [
        log
        for log in logs
        if log.get("event_type") == "TraceEvent"
        and log.get("span_context", {}).get("trace_id") == trace_id
    ]

    # Create a map of span_id to its logs
    span_map = {}
    for log in trace_logs:
        span_id = log["span_context"]["span_id"]
        if span_id not in span_map:
            span_map[span_id] = []
        span_map[span_id].append(log)

    # Build the tree
    tree = {"spans": {}, "root_spans": []}

    for span_id, span_logs in span_map.items():
        # Combine start and end logs
        start_log = next((log for log in span_logs if log.get("start_time")), None)
        end_log = next((log for log in span_logs if log.get("end_time")), None)

        if start_log:
            span_info = {
                "span_id": span_id,
                "name": start_log.get("name"),
                "start_time": start_log.get("start_time"),
                "end_time": end_log.get("end_time") if end_log else None,
                "duration_ms": _calculate_duration(
                    start_log.get("start_time"),
                    end_log.get("end_time") if end_log else None,
                ),
                "status": end_log.get("status") if end_log else start_log.get("status"),
                "attributes": start_log.get("attributes", {}),
                "children": [],
            }

            parent_span_id = start_log["span_context"].get("parent_span_id")

            tree["spans"][span_id] = span_info

            if parent_span_id:
                if parent_span_id in tree["spans"]:
                    tree["spans"][parent_span_id]["children"].append(span_id)
                # Handle case where parent might be processed later
                else:
                    if "pending_children" not in tree:
                        tree["pending_children"] = {}
                    if parent_span_id not in tree["pending_children"]:
                        tree["pending_children"][parent_span_id] = []
                    tree["pending_children"][parent_span_id].append(span_id)
            else:
                tree["root_spans"].append(span_id)

    # Handle pending children
    if "pending_children" in tree:
        for parent_id, children in tree["pending_children"].items():
            if parent_id in tree["spans"]:
                tree["spans"][parent_id]["children"].extend(children)
            else:
                # If parent is not found, consider these as root spans
                tree["root_spans"].extend(children)

    return tree


def _calculate_duration(
    start_time: Optional[str], end_time: Optional[str]
) -> Optional[float]:
    """Calculate duration between start and end times in milliseconds."""
    if not start_time or not end_time:
        return None

    start = datetime.fromisoformat(start_time)
    end = datetime.fromisoformat(end_time)
    return (end - start).total_seconds() * 1000


def calculate_metrics(logs: List[Dict]) -> Dict[str, Any]:
    """Calculate various metrics from logs."""
    metrics = {
        "total_logs": len(logs),
        "log_levels": {},
        "event_types": {},
        "components": {},
        "traces": {},
        "errors": [],
        "warnings": [],
    }

    # Count log levels
    for log in logs:
        level = log.get("level")
        if level:
            metrics["log_levels"][level] = metrics["log_levels"].get(level, 0) + 1

    # Count event types
    for log in logs:
        event_type = log.get("event_type")
        if event_type:
            metrics["event_types"][event_type] = (
                metrics["event_types"].get(event_type, 0) + 1
            )

    # Count components
    for log in logs:
        component = log.get("context", {}).get("component")
        if component:
            metrics["components"][component] = metrics["components"].get(component, 0) + 1

    # Collect trace information
    trace_ids = set()
    for log in logs:
        if log.get("event_type") == "TraceEvent":
            trace_id = log.get("span_context", {}).get("trace_id")
            if trace_id:
                trace_ids.add(trace_id)
                if trace_id not in metrics["traces"]:
                    metrics["traces"][trace_id] = {"span_count": 0, "status": {}}
                metrics["traces"][trace_id]["span_count"] += 1

                status = log.get("status")
                if status:
                    metrics["traces"][trace_id]["status"][status] = (
                        metrics["traces"][trace_id]["status"].get(status, 0) + 1
                    )

    # Collect errors and warnings
    for log in logs:
        if log.get("level") == "ERROR":
            metrics["errors"].append({
                "timestamp": log.get("timestamp"),
                "message": log.get("message"),
                "source": log.get("source"),
            })
        elif log.get("level") == "WARNING":
            metrics["warnings"].append({
                "timestamp": log.get("timestamp"),
                "message": log.get("message"),
                "source": log.get("source"),
            })

    return metrics


def get_all_traces(logs: List[Dict]) -> Dict[str, Dict]:
    """Get information about all traces in the logs."""
    trace_logs = [log for log in logs if log.get("event_type") == "TraceEvent"]
    trace_ids = set(
        log.get("span_context", {}).get("trace_id")
        for log in trace_logs
        if log.get("span_context")
    )

    trace_info = {}
    for tid in trace_ids:
        trace_spans = [
            log
            for log in trace_logs
            if log.get("span_context", {}).get("trace_id") == tid
        ]

        # Find root spans (no parent_span_id)
        root_spans = [
            span
            for span in trace_spans
            if not span.get("span_context", {}).get("parent_span_id")
        ]

        if root_spans:
            trace_name = root_spans[0].get("name", "Unknown")
            start_times = [
                datetime.fromisoformat(span.get("start_time"))
                for span in trace_spans
                if span.get("start_time")
            ]

            if start_times:
                start_time = min(start_times)

                # Find end_time for spans that have it
                end_spans = [span for span in trace_spans if span.get("end_time")]
                end_times = [
                    datetime.fromisoformat(span.get("end_time")) for span in end_spans
                ]
                end_time = max(end_times) if end_times else None

                duration = (
                    (end_time - start_time).total_seconds() * 1000 if end_time else None
                )

                trace_info[tid] = {
                    "name": trace_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration,
                    "span_count": len(trace_spans),
                }

    return trace_info


def extract_time_part(timestamp: str) -> str:
    """Extract the time part from an ISO timestamp."""
    if not timestamp:
        return ""
    parts = timestamp.split("T")
    if len(parts) > 1:
        time_part = parts[1].split(".")[0]
        return time_part
    return timestamp
