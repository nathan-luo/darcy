#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Make sure we can import log_parser.py from the same directory
sys.path.insert(0, str(Path(__file__).parent))
import log_parser

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Search logs with advanced query capabilities."
    )
    parser.add_argument("log_file", type=str, help="Path to log file")
    parser.add_argument(
        "--query", "-q", help="Search query (supports field:value syntax)"
    )
    parser.add_argument(
        "--regex", "-r", action="store_true", help="Use regular expressions in search"
    )
    parser.add_argument(
        "--context",
        "-c",
        type=int,
        default=0,
        help="Show N lines of context before and after matches",
    )
    parser.add_argument(
        "--field", "-f", help="Search only in this field (e.g., message, source)"
    )
    parser.add_argument(
        "--limit", "-n", type=int, default=100, help="Limit the number of results"
    )
    return parser.parse_args()


def search_logs(args):
    # Load logs
    logs = log_parser.load_logs(args.log_file)
    console.print(f"[bold]Loaded [green]{len(logs)}[/green] log entries[/bold]")

    # Parse query
    field_queries = {}
    text_query = args.query

    if args.query and ":" in args.query and not args.field:
        # Parse field:value syntax
        parts = re.findall(r"(\w+):([^\s]+)", args.query)
        for field_name, value in parts:
            field_queries[field_name] = value
            text_query = text_query.replace(f"{field_name}:{value}", "").strip()

    # Filter logs
    if not args.query:
        console.print("[yellow]No search query provided. Showing sample logs:[/yellow]")
        results = logs[: args.limit]
    else:
        results = []
        for log in logs:
            match = True

            # Check field queries
            for field_name, value in field_queries.items():
                field_value = None

                # Handle nested fields
                if "." in field_name:
                    parts = field_name.split(".")
                    current = log
                    for part in parts:
                        if isinstance(current, dict) and part in current:
                            current = current[part]
                        else:
                            current = None
                            break
                    field_value = str(current) if current is not None else ""
                elif field_name in log:
                    field_value = str(log[field_name])

                if field_value is None:
                    match = False
                    break

                if args.regex:
                    try:
                        if not re.search(value, field_value):
                            match = False
                            break
                    except re.error:
                        # Invalid regex pattern
                        match = False
                        break
                elif value not in field_value:
                    match = False
                    break

            # Check text query
            if match and text_query:
                if args.field:
                    # Search in specific field
                    field_value = None

                    # Handle nested fields
                    if "." in args.field:
                        parts = args.field.split(".")
                        current = log
                        for part in parts:
                            if isinstance(current, dict) and part in current:
                                current = current[part]
                            else:
                                current = None
                                break
                        field_value = str(current) if current is not None else ""
                    elif args.field in log:
                        field_value = str(log[args.field])

                    if field_value is None:
                        match = False
                    elif args.regex:
                        try:
                            if not re.search(text_query, field_value):
                                match = False
                        except re.error:
                            # Invalid regex pattern
                            match = False
                    elif text_query.lower() not in field_value.lower():
                        match = False
                else:
                    # Search in all text fields
                    log_text = str(log)
                    if args.regex:
                        try:
                            if not re.search(text_query, log_text):
                                match = False
                        except re.error:
                            # Invalid regex pattern
                            match = False
                    elif text_query.lower() not in log_text.lower():
                        match = False

            if match:
                results.append(log)
                if len(results) >= args.limit:
                    break

    console.print(f"[bold]Found [green]{len(results)}[/green] matching logs[/bold]")

    # Display results
    if not results:
        console.print("[yellow]No matching logs found.[/yellow]")
        console.print("\n[bold]Search Tips:[/bold]")
        console.print(
            "- Use field:value syntax to search specific fields (e.g., level:WARNING)"
        )
        console.print("- Use --field to search only in a specific field")
        console.print("- Use --regex to enable regular expression matching")
        console.print("- Use --context to show surrounding log entries")
        return

    # Show results with context
    context_logs = []
    if args.context > 0:
        log_indices = []
        for result in results:
            try:
                log_indices.append(logs.index(result))
            except ValueError:
                # This shouldn't happen normally, but just in case
                continue

        for idx in log_indices:
            start = max(0, idx - args.context)
            end = min(len(logs), idx + args.context + 1)
            for i in range(start, end):
                entry = (logs[i], i == idx)
                if entry not in context_logs:
                    context_logs.append(entry)
    else:
        context_logs = [(log, True) for log in results]

    # Display in a table
    table = Table(show_header=True, header_style="bold", expand=True)
    table.add_column("Time", width=12)
    table.add_column("Level", width=8)
    table.add_column("Source", width=25)
    table.add_column("Message", ratio=2)

    current_match = False
    for log, is_match in context_logs:
        if is_match != current_match:
            current_match = is_match
            if is_match:
                table.add_row("", "", "", "", style="on dark_blue")

        timestamp = log_parser.extract_time_part(log.get("timestamp", ""))

        level = log.get("level", "")
        level_style = {
            "INFO": "green",
            "DEBUG": "blue",
            "WARNING": "yellow",
            "ERROR": "red",
        }.get(level, "white")

        source = log.get("source", "").split("/")[-1] if log.get("source") else ""
        message = log.get("message", "")

        row_style = "bold" if is_match else ""

        table.add_row(
            timestamp, Text(level, style=level_style), source, message, style=row_style
        )

        if is_match and args.context > 0 and is_match != context_logs[-1][1]:
            table.add_row("", "", "", "", style="on dark_blue")

    console.print(table)

    # Show field summary for the first result
    if results:
        first_result = results[0]
        console.print("\n[bold]Sample Match Fields:[/bold]")
        fields_panel = Panel.fit(
            "\n".join([
                f"[bold]{k}:[/bold] {v}"
                for k, v in first_result.items()
                if k not in ("context", "attributes") and v is not None
            ]),
            title="Fields available for searching",
        )
        console.print(fields_panel)


def main():
    args = parse_args()
    search_logs(args)


if __name__ == "__main__":
    main()
