import json
import sys
import os
from pathlib import Path
from datetime import datetime
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel
from rich.text import Text
from rich.table import Table


@dataclass
class SpanInfo:
    """Information about a trace span."""

    name: str
    span_id: str
    trace_id: str
    parent_span_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str = "unknown"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    children: List["SpanInfo"] = field(default_factory=list)

    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate the duration in milliseconds."""
        if not self.start_time or not self.end_time:
            return None

        try:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            return (end - start).total_seconds() * 1000
        except (ValueError, TypeError):
            return None

    @property
    def short_id(self) -> str:
        """Get short version of span ID."""
        return self.span_id[:8] if self.span_id else "unknown"

    @property
    def short_trace_id(self) -> str:
        """Get short version of trace ID."""
        return self.trace_id[:8] if self.trace_id else "unknown"


class TraceVisualizer:
    """Visualize traces from LLMgine logs with rich hierarchical display."""

    def __init__(self, log_path: Optional[str] = None):
        """Initialize with a log file path."""
        self.log_path = Path(log_path) if log_path else None
        self.traces: Dict[str, Dict[str, SpanInfo]] = {}
        self.trace_trees: Dict[str, List[SpanInfo]] = {}
        self.console = Console()

    def find_latest_log(self, directory: str = "multilevel_trace_logs") -> Optional[Path]:
        """Find the most recent log file in the specified directory."""
        log_dir = Path(directory)
        if not log_dir.exists():
            return None

        log_files = list(log_dir.glob("*.jsonl"))
        if not log_files:
            return None

        return max(log_files, key=lambda p: p.stat().st_mtime)

    def parse_logs(self, log_path: Optional[str] = None):
        """Parse the log file and extract trace information."""
        if log_path:
            self.log_path = Path(log_path)

        if not self.log_path:
            # Try to find the latest log file
            self.log_path = self.find_latest_log()
            if not self.log_path:
                self.console.print("[bold red]Error:[/bold red] No log file found")
                return self

        self.console.print(f"Parsing log file: [bold cyan]{self.log_path}[/bold cyan]")

        # Read the log file
        try:
            with open(self.log_path, "r") as f:
                log_content = f.read()

                # Remove trailing comma if present
                log_content = log_content.rstrip(",\n")

                # Handle empty file
                if not log_content.strip():
                    self.console.print(
                        "[bold yellow]Warning:[/bold yellow] Log file is empty"
                    )
                    return self

                # Format as array for easier parsing
                log_json = f"[{log_content}]"

                # Parse the log entries
                try:
                    logs = json.loads(log_json)

                    # Extract trace events
                    trace_count = 0
                    for entry in logs:
                        if entry.get("event_type") == "TraceEvent":
                            self._process_trace_event(entry)
                            trace_count += 1

                    self.console.print(
                        f"Extracted [bold green]{trace_count}[/bold green] trace events"
                    )

                except json.JSONDecodeError as e:
                    self.console.print(
                        f"[bold red]Error:[/bold red] Failed to parse JSON: {e}"
                    )

                    # Try to find where the JSON is malformed
                    line_num = e.lineno
                    line = (
                        log_content.split("\n")[line_num - 1]
                        if line_num <= len(log_content.split("\n"))
                        else ""
                    )
                    self.console.print(f"Problem near line {line_num}: {line[:100]}...")

                    # Try to fix common issues
                    self.console.print("Attempting to fix JSON format...")
                    fixed_content = self._fix_json_content(log_content)
                    logs = json.loads(f"[{fixed_content}]")

                    # Extract trace events from fixed content
                    trace_count = 0
                    for entry in logs:
                        if entry.get("event_type") == "TraceEvent":
                            self._process_trace_event(entry)
                            trace_count += 1

                    self.console.print(
                        f"Extracted [bold green]{trace_count}[/bold green] trace events after fixing JSON"
                    )

        except Exception as e:
            self.console.print(f"[bold red]Error:[/bold red] {str(e)}")

        return self

    def _fix_json_content(self, content: str) -> str:
        """Attempt to fix common JSON formatting issues in log files."""
        # Remove trailing commas
        content = re.sub(r",\s*}", "}", content)
        content = re.sub(r",\s*\]", "]", content)

        # Ensure every entry ends with a comma except the last one
        lines = content.split("\n")
        for i in range(len(lines) - 1):
            if lines[i].strip().endswith("}"):
                lines[i] = lines[i] + ","

        return "\n".join(lines)

    def _process_trace_event(self, event: Dict[str, Any]):
        """Process a trace event."""
        span_ctx = event.get("span_context", {})
        span_id = span_ctx.get("span_id")
        trace_id = span_ctx.get("trace_id")
        parent_span_id = span_ctx.get("parent_span_id")

        if not span_id or not trace_id:
            return

        # Initialize trace dictionary if needed
        if trace_id not in self.traces:
            self.traces[trace_id] = {}

        # Create or update span info
        if span_id not in self.traces[trace_id]:
            self.traces[trace_id][span_id] = SpanInfo(
                name=event.get("name", "unknown"),
                span_id=span_id,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                start_time=event.get("start_time"),
                end_time=event.get("end_time"),
                status=event.get("status", "unknown"),
                attributes=event.get("attributes", {}),
                events=event.get("events", []),
            )
        else:
            # Update existing span
            span = self.traces[trace_id][span_id]

            # Don't update name if this is just an "end_span" event
            if event.get("name") and event.get("name") != "end_span":
                span.name = event.get("name")

            # Update times
            if event.get("start_time"):
                span.start_time = event.get("start_time")
            if event.get("end_time"):
                span.end_time = event.get("end_time")

            # Update status
            if event.get("status"):
                span.status = event.get("status")

            # Merge attributes
            if event.get("attributes"):
                span.attributes.update(event.get("attributes"))

            # Add events
            if event.get("events"):
                span.events.extend(event.get("events"))

    def build_trace_trees(self):
        """Build trace trees based on parent-child relationships."""
        self.trace_trees = {}
        orphans_count = 0

        for trace_id, spans in self.traces.items():
            # Find root spans (no parent or parent not in this trace)
            root_spans = []
            for span_id, span in spans.items():
                if not span.parent_span_id or span.parent_span_id not in spans:
                    root_spans.append(span)

            # Build trees for each root span
            for root_span in root_spans:
                self._add_children(root_span, spans)

            self.trace_trees[trace_id] = root_spans

            # Count orphans (spans with parent_span_id that doesn't exist)
            orphans = [
                s
                for s in spans.values()
                if s.parent_span_id and s.parent_span_id not in spans
            ]
            orphans_count += len(orphans)

        self.console.print(
            f"Built [bold green]{len(self.trace_trees)}[/bold green] trace trees"
        )
        if orphans_count > 0:
            self.console.print(
                f"[bold yellow]Warning:[/bold yellow] Found {orphans_count} orphaned spans (parent ID not found)"
            )

        return self

    def _add_children(self, parent: SpanInfo, all_spans: Dict[str, SpanInfo]):
        """Recursively add children to a span."""
        for span_id, span in all_spans.items():
            if span.parent_span_id == parent.span_id:
                parent.children.append(span)
                self._add_children(span, all_spans)

    def visualize_traces(self):
        """Visualize the trace trees using rich formatting."""
        if not self.trace_trees:
            self.console.print(
                "[bold yellow]No trace trees to display.[/bold yellow] Run parse_logs() and build_trace_trees() first."
            )
            return

        total_spans = sum(len(spans) for spans in self.traces.values())
        self.console.print(
            f"\n[bold]===== TRACE VISUALIZATION ({len(self.trace_trees)} traces, {total_spans} spans) ====="
        )

        # Find the top 5 traces by span count
        sorted_traces = sorted(
            [(tid, len(spans)) for tid, spans in self.traces.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        # Show trace selection menu
        self.console.print("\n[bold cyan]Available Traces:[/bold cyan]")

        trace_table = Table(show_header=True, header_style="bold magenta")
        trace_table.add_column("#", style="dim", width=4)
        trace_table.add_column("Trace ID", style="cyan")
        trace_table.add_column("Spans", justify="right")
        trace_table.add_column("Root Spans", justify="right")
        trace_table.add_column("Max Depth", justify="right")

        for i, (trace_id, span_count) in enumerate(sorted_traces[:10], 1):
            root_count = len(self.trace_trees.get(trace_id, []))
            max_depth = self._calculate_max_depth(self.trace_trees.get(trace_id, []))
            trace_table.add_row(
                str(i),
                f"{trace_id[:12]}...",
                str(span_count),
                str(root_count),
                str(max_depth),
            )

        self.console.print(trace_table)
        self.console.print("")

        # Get user input for which trace to visualize
        selected = None
        while selected is None:
            try:
                choice = input("Select a trace to visualize (1-10) or 'a' for all: ")
                if choice.lower() == "a":
                    # Visualize all traces
                    selected = "all"
                else:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(sorted_traces):
                        selected = sorted_traces[choice_idx][0]
                    else:
                        self.console.print(
                            "[bold red]Invalid selection. Try again.[/bold red]"
                        )
            except ValueError:
                self.console.print("[bold red]Please enter a number or 'a'.[/bold red]")

        # Visualize the selected trace(s)
        if selected == "all":
            for i, (trace_id, _) in enumerate(sorted_traces[:5], 1):
                self._visualize_trace(trace_id, i)
        else:
            self._visualize_trace(selected)

        return self

    def _calculate_max_depth(self, spans: List[SpanInfo], current_depth: int = 1) -> int:
        """Calculate the maximum depth of the trace tree."""
        if not spans:
            return current_depth - 1

        child_depths = [
            self._calculate_max_depth(span.children, current_depth + 1) for span in spans
        ]

        return max(child_depths) if child_depths else current_depth

    def _get_span_style(self, span: SpanInfo) -> str:
        """Get a rich style string based on span status."""
        status_styles = {
            "success": "green",
            "error": "red",
            "warning": "yellow",
            "unknown": "blue",
        }
        return status_styles.get(span.status.lower(), "white")

    def _format_duration(self, duration_ms: Optional[float]) -> str:
        """Format duration for display."""
        if duration_ms is None:
            return "n/a"

        if duration_ms < 1:
            return f"{duration_ms * 1000:.2f}μs"
        elif duration_ms < 1000:
            return f"{duration_ms:.2f}ms"
        else:
            return f"{duration_ms / 1000:.2f}s"

    def _visualize_trace(self, trace_id: str, index: int = 1):
        """Visualize a specific trace."""
        if trace_id not in self.trace_trees:
            self.console.print(f"[bold red]Trace {trace_id} not found[/bold red]")
            return

        root_spans = self.trace_trees[trace_id]
        span_count = len(self.traces[trace_id])

        # Create a root tree node
        trace_tree = Tree(
            f"[bold]Trace {index}: {trace_id[:12]}... ({span_count} spans)[/bold]"
        )

        # Add each root span as a branch
        for root_span in root_spans:
            self._add_span_to_tree(root_span, trace_tree)

        # Display the tree
        self.console.print()
        self.console.print(trace_tree)

        # Display stats for this trace
        total_time = sum(span.duration_ms or 0 for span in self.traces[trace_id].values())
        avg_time = total_time / span_count if span_count > 0 else 0

        stats_table = Table(show_header=True, header_style="bold")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", justify="right")

        stats_table.add_row("Total Spans", str(span_count))
        stats_table.add_row("Total Time", self._format_duration(total_time))
        stats_table.add_row("Average Span Time", self._format_duration(avg_time))

        # Count spans by status
        status_counts = {}
        for span in self.traces[trace_id].values():
            status = span.status.lower()
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in status_counts.items():
            stats_table.add_row(f"Status: {status.capitalize()}", str(count))

        self.console.print(stats_table)

    def _add_span_to_tree(self, span: SpanInfo, tree: Tree):
        """Add a span and its children to the tree."""
        # Format span info
        status_color = self._get_span_style(span)
        duration = self._format_duration(span.duration_ms)

        # Create label with timing info
        label = Text()
        label.append(f"{span.name} ", style=f"bold {status_color}")
        label.append(f"[{duration}] ", style="dim")
        label.append(f"{span.status}", style=status_color)

        # Add extra info if available
        if span.attributes:
            attrs = " ".join(f"{k}={v}" for k, v in span.attributes.items())
            if len(attrs) > 50:
                attrs = attrs[:47] + "..."
            label.append(f" ({attrs})", style="italic")

        # Create branch
        branch = tree.add(label)

        # Add span details as child nodes
        details = branch.add(
            f"[dim]ID: {span.short_id} | Trace: {span.short_trace_id}[/dim]"
        )

        # Add timing details if available
        if span.start_time and span.end_time:
            start = datetime.fromisoformat(span.start_time)
            end = datetime.fromisoformat(span.end_time)
            details.add(
                f"[dim]Start: {start.strftime('%H:%M:%S.%f')[:-3]} | End: {end.strftime('%H:%M:%S.%f')[:-3]}[/dim]"
            )

        # Add all children
        for child in span.children:
            self._add_span_to_tree(child, branch)

    def generate_report(self, output_path: Optional[str] = None):
        """Generate an HTML report of all traces."""
        # This would generate an interactive HTML report
        # Out of scope for this demo, but would be useful for a real implementation
        pass


def main():
    """Main entry point for trace visualization."""
    # Parse command line arguments
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    else:
        # Try to find the most recent log file
        log_file = None

    # Create console
    console = Console()
    console.print("[bold cyan]LLMgine Hierarchical Trace Visualizer[/bold cyan]")
    console.print("=" * 50)

    # Create and run visualizer
    visualizer = TraceVisualizer(log_file)
    visualizer.parse_logs().build_trace_trees().visualize_traces()


if __name__ == "__main__":
    main()
