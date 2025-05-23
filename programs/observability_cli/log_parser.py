import json
from datetime import datetime

# types
from typing import Any, List, NewType, Optional, Set

span_id_type = NewType("span_id_type", str)
trace_id_type = NewType("trace_id_type", str)


log_dict_type = NewType("log_dict_type", dict[str, Any])
trace_dict_type = NewType("trace_dict_type", dict[str, Any])


trace_map_type = NewType("trace_map_type", dict[trace_id_type, trace_dict_type])
span_map_type = NewType("span_map_type", dict[span_id_type, list[log_dict_type]])


span_tree_type = NewType("span_tree_type", dict[str, Any])


def load_logs(file_path: str) -> List[log_dict_type]:
    """Load and parse logs from a file."""
    logs: list[log_dict_type] = []
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
    logs: List[log_dict_type],
    level: Optional[str] = None,
    event_type: Optional[str] = None,
    after: Optional[datetime] = None,
    before: Optional[datetime] = None,
    source: Optional[str] = None,
    component: Optional[str] = None,
    message_contains: Optional[str] = None,
) -> List[log_dict_type]:
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


# TODO add types to this function
def get_unique_values(logs: List[log_dict_type], field: str) -> Set[Any]:
    """Get unique values for a specific field in logs."""
    values: Set[Any] = set()
    for log in logs:
        if field in log:
            values.add(log[field])
        elif "." in field:
            # Handle nested fields
            parts = field.split(".")
            current: Any = log
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    current = None
                    break
            if current is not None:
                values.add(current)
    return values


def get_trace_tree(logs: List[log_dict_type], trace_id: str) -> span_tree_type:
    """Build a tree of spans for a specific trace."""
    # Filter logs for the specific trace
    trace_logs: list[log_dict_type] = [
        log
        for log in logs
        if log.get("event_type") == "TraceEvent"
        and log.get("span_context", {}).get("trace_id") == trace_id
    ]

    # Create a map of span_id to its logs
    span_map: span_map_type = span_map_type({})
    for log in trace_logs:
        span_id: span_id_type = log["span_context"]["span_id"]
        if span_id not in span_map:
            span_map[span_id] = []
        span_map[span_id].append(log)

    # Build the tree
    tree: span_tree_type = span_tree_type({"spans": {}, "root_spans": []})

    for span_id, span_logs in span_map.items():
        # Combine start and end logs
        start_log = next((log for log in span_logs if log.get("start_time")), None)
        end_log = next((log for log in span_logs if log.get("end_time")), None)

        if start_log:
            span_info: dict[str, Any] = {
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


def calculate_metrics(logs: List[log_dict_type]) -> dict[str, Any]:
    """Calculate various metrics from logs."""
    metrics: dict[str, Any] = {
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
        level: Optional[str] = log.get("level")
        if level:
            metrics["log_levels"][level] = metrics["log_levels"].get(level, 0) + 1

    # Count event types
    for log in logs:
        event_type: Optional[str] = log.get("event_type")
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
    trace_ids: set[trace_id_type] = set()
    for log in logs:
        if log.get("event_type") == "TraceEvent":
            trace_id: trace_id_type = log.get("span_context", {}).get("trace_id")
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


def get_all_traces(logs: List[log_dict_type]) -> trace_map_type:
    """Get information about all traces in the logs."""
    trace_logs: list[log_dict_type] = [
        log for log in logs if log.get("event_type") == "TraceEvent"
    ]
    trace_ids: set[trace_id_type] = set(
        log.get("span_context", {}).get("trace_id")
        for log in trace_logs
        if log.get("span_context")
    )

    trace_info: trace_map_type = trace_map_type({})
    for tid in trace_ids:
        trace_spans: list[log_dict_type] = [
            log
            for log in trace_logs
            if log.get("span_context", {}).get("trace_id") == tid
        ]

        # Find root spans (no parent_span_id)
        root_spans: list[log_dict_type] = [
            span
            for span in trace_spans
            if not span.get("span_context", {}).get("parent_span_id")
        ]

        if root_spans:
            trace_name = root_spans[0].get("name", "Unknown")
            start_times = [
                datetime.fromisoformat(span.get("start_time", ""))
                for span in trace_spans
                if span.get("start_time")
            ]

            if start_times:
                start_time = min(start_times)

                # Find end_time for spans that have it
                end_spans: list[log_dict_type] = [
                    span for span in trace_spans if span.get("end_time")
                ]

                end_times: list[datetime] = [
                    datetime.fromisoformat(span.get("end_time", None))
                    for span in end_spans
                    if span.get("end_time", None)
                ]

                end_time: Optional[datetime] = max(end_times) if end_times else None

                duration: Optional[float] = (
                    (end_time - start_time).total_seconds() * 1000 if end_time else None
                )

                trace_tmp: trace_dict_type = trace_dict_type({
                    "name": trace_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration,
                    "span_count": len(trace_spans),
                })

                trace_info[tid] = trace_tmp

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
