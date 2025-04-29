#!/usr/bin/env python3
import argparse
from datetime import datetime

import log_parser
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="View and filter logs with rich formatting."
    )
    parser.add_argument("log_file", type=str, help="Path to log file")
    parser.add_argument(
        "--level", "-l", help="Filter by log level (INFO, DEBUG, WARNING, ERROR)"
    )
    parser.add_argument(
        "--event-type", "-e", help="Filter by event type (LogEvent, TraceEvent)"
    )
    parser.add_argument("--after", help="Show logs after this time (YYYY-MM-DDTHH:MM:SS)")
    parser.add_argument(
        "--before", help="Show logs before this time (YYYY-MM-DDTHH:MM:SS)"
    )
    parser.add_argument("--source", "-s", help="Filter by source path")
    parser.add_argument("--component", "-c", help="Filter by component name")
    parser.add_argument(
        "--message", "-m", help="Filter logs containing this message text"
    )
    parser.add_argument(
        "--limit", "-n", type=int, default=100, help="Limit the number of logs shown"
    )
    parser.add_argument(
        "--page", "-p", type=int, default=1, help="Page number for pagination"
    )
    return parser.parse_args()


def view_logs(args):
    # Load logs
    logs = log_parser.load_logs(args.log_file)
    console.print(f"[bold]Loaded [green]{len(logs)}[/green] log entries[/bold]")

    # Parse datetime filters
    after_dt = datetime.fromisoformat(args.after) if args.after else None
    before_dt = datetime.fromisoformat(args.before) if args.before else None

    # Filter logs
    filtered_logs = log_parser.filter_logs(
        logs,
        args.level,
        args.event_type,
        after_dt,
        before_dt,
        args.source,
        args.component,
        args.message,
    )

    # Paginate
    start_idx = (args.page - 1) * args.limit
    end_idx = min(start_idx + args.limit, len(filtered_logs))
    paginated_logs = filtered_logs[start_idx:end_idx]

    console.print(
        f"[bold]Showing [green]{len(paginated_logs)}[/green] of [blue]{len(filtered_logs)}[/blue] filtered logs[/bold]"
    )

    # Display logs
    table = Table(show_header=True, header_style="bold", expand=True)
    table.add_column("Time", width=12, no_wrap=True)
    table.add_column("Level", width=8, no_wrap=True)
    table.add_column("Component", width=15)
    table.add_column("Message", ratio=3)
    table.add_column("Event Type", width=12, no_wrap=True)

    for log in paginated_logs:
        timestamp = log_parser.extract_time_part(log.get("timestamp", ""))

        # Style based on level
        level_val = log.get("level", "")
        level_style = {
            "INFO": "green",
            "DEBUG": "blue",
            "WARNING": "yellow",
            "ERROR": "red",
        }.get(level_val, "white")

        component = log.get("context", {}).get("component", "")
        message = log.get("message", "")
        event_type_val = log.get("event_type", "")

        table.add_row(
            timestamp,
            Text(level_val, style=level_style),
            component,
            message,
            event_type_val,
        )

    console.print(table)

    # Display pagination info
    total_pages = (
        (len(filtered_logs) + args.limit - 1) // args.limit if args.limit > 0 else 1
    )
    console.print(f"[italic]Page {args.page} of {total_pages}[/italic]")

    if (
        args.level is None
        and args.event_type is None
        and args.source is None
        and args.component is None
        and args.message is None
    ):
        # Show quick stats
        levels = log_parser.get_unique_values(logs, "level")
        components = log_parser.get_unique_values(logs, "context.component")
        event_types = log_parser.get_unique_values(logs, "event_type")

        console.print("\n[bold]Available filters:[/bold]")
        console.print(
            Panel(
                f"Levels: {', '.join(sorted([l for l in levels if l]))}\n"
                f"Components: {', '.join(sorted([c for c in components if c]))}\n"
                f"Event Types: {', '.join(sorted([e for e in event_types if e]))}"
            )
        )

        console.print("[bold]Usage tips:[/bold]")
        console.print("  - Use --level to filter by log level")
        console.print("  - Use --event-type to filter by event type")
        console.print("  - Use --component to filter by component")
        console.print("  - Use --message to search in message text")
        console.print(
            "  - Use --after/--before to filter by time (format: YYYY-MM-DDTHH:MM:SS)"
        )


def main() -> None:
    args = parse_args()
    view_logs(args)


if __name__ == "__main__":
    main()
