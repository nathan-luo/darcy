#!/usr/bin/env python3
import argparse
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

# Make sure we can import log_parser.py from the same directory
sys.path.insert(0, str(Path(__file__).parent))
import log_parser

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Visualize and explore distributed traces."
    )
    parser.add_argument("log_file", type=str, help="Path to log file")
    parser.add_argument("--trace-id", "-t", help="Filter by specific trace ID")
    parser.add_argument(
        "--list-traces", "-l", action="store_true", help="List all available traces"
    )
    parser.add_argument(
        "--sort-by",
        "-s",
        type=str,
        choices=["time", "duration", "spans"],
        default="time",
        help="Sort traces by field",
    )
    return parser.parse_args()


def visualize_traces(args):
    # Load logs
    logs = log_parser.load_logs(args.log_file)
    console.print(f"[bold]Loaded [green]{len(logs)}[/green] log entries[/bold]")

    # Get trace information
    trace_info = log_parser.get_all_traces(logs)

    if args.list_traces or not args.trace_id:
        # Show a list of traces
        console.print(f"[bold]Found [green]{len(trace_info)}[/green] traces[/bold]")

        # Sort traces based on criteria
        if args.sort_by == "time":
            sorted_traces = sorted(
                trace_info.items(),
                key=lambda x: x[1]["start_time"] if x[1]["start_time"] else datetime.min,
            )
        elif args.sort_by == "duration":
            sorted_traces = sorted(
                trace_info.items(),
                key=lambda x: x[1]["duration"] if x[1]["duration"] else 0,
                reverse=True,
            )
        else:  # sort_by == 'spans'
            sorted_traces = sorted(
                trace_info.items(), key=lambda x: x[1]["span_count"], reverse=True
            )

        # Display in a table
        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("Trace ID", width=36)
        table.add_column("Name", width=30)
        table.add_column("Start Time", width=12)
        table.add_column("Duration (ms)", width=12, justify="right")
        table.add_column("Spans", width=6, justify="right")

        for tid, info in sorted_traces:
            start_time_str = (
                info["start_time"].strftime("%H:%M:%S")
                if info["start_time"]
                else "Unknown"
            )

            duration_str = f"{info['duration']:.2f}" if info["duration"] else "?"

            table.add_row(
                tid, info["name"], start_time_str, duration_str, str(info["span_count"])
            )

        console.print(table)
        console.print("\nUse --trace-id to visualize a specific trace")
        return

    # Visualize a specific trace
    if args.trace_id not in trace_info:
        console.print(f"[bold red]Trace ID '{args.trace_id}' not found![/bold red]")
        return

    trace_tree = log_parser.get_trace_tree(logs, args.trace_id)

    # Display trace information
    console.print(
        Panel(
            f"[bold]Trace:[/bold] {args.trace_id}\n"
            f"[bold]Name:[/bold] {trace_info[args.trace_id]['name']}\n"
            f"[bold]Start Time:[/bold] {trace_info[args.trace_id]['start_time']}\n"
            f"[bold]Duration:[/bold] {trace_info[args.trace_id]['duration']:.2f}ms\n"
            f"[bold]Spans:[/bold] {trace_info[args.trace_id]['span_count']}"
        )
    )

    # Create a rich Tree visualization
    rich_tree = Tree(f"[bold]Trace: {args.trace_id}[/bold]")

    def add_spans_to_tree(tree_node, span_id, depth=0):
        span = trace_tree["spans"][span_id]

        # Calculate duration
        duration_text = ""
        if span["duration_ms"] is not None:
            duration_text = f" [cyan]{span['duration_ms']:.2f}ms[/cyan]"

        # Style based on status
        status_style = {
            "OK": "green",
            "success": "green",
            "warning": "yellow",
            "error": "red",
        }.get(span.get("status", ""), "white")

        # Format attributes as a string
        attrs = []
        for k, v in span.get("attributes", {}).items():
            attrs.append(f"{k}={v}")
        attrs_text = f" [dim]{', '.join(attrs)}[/dim]" if attrs else ""

        # Create node text
        span_text = f"[bold]{span['name']}[/bold]{duration_text} [bold {status_style}]({span.get('status', 'unknown')})[/bold {status_style}]{attrs_text}"

        # Add to tree
        child_node = tree_node.add(span_text)

        # Add children recursively
        for child_id in span.get("children", []):
            add_spans_to_tree(child_node, child_id, depth + 1)

    # Add all root spans
    for root_span_id in trace_tree["root_spans"]:
        add_spans_to_tree(rich_tree, root_span_id)

    console.print(rich_tree)

    # Display span count by status
    status_counts = {}
    for span_id, span in trace_tree["spans"].items():
        status = span.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    status_table = Table(
        title="Span Status Summary", show_header=True, header_style="bold"
    )
    status_table.add_column("Status")
    status_table.add_column("Count")

    for status, count in status_counts.items():
        status_style = {
            "OK": "green",
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "unknown": "dim",
        }.get(status, "white")

        status_table.add_row(Text(status, style=status_style), str(count))

    console.print(status_table)


def main():
    args = parse_args()
    visualize_traces(args)


if __name__ == "__main__":
    main()
