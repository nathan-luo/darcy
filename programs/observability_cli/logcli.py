#!/usr/bin/env python3
import argparse
import os
import sys

# Import the individual tools
import log_search
import log_stats
import log_viewer
import traceviz


def parse_args():
    parser = argparse.ArgumentParser(
        description="LLMgine log analysis toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  logcli view logs/trace_2023.json --level WARNING
  logcli trace logs/trace_2023.json --trace-id "8607736c-7aa3-4084-aa8b-bb62094ab80b"
  logcli search logs/trace_2023.json --query "error" --context 2
  logcli stats logs/trace_2023.json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # View command
    view_parser = subparsers.add_parser("view", help="View and filter logs")
    view_parser.add_argument("log_file", help="Path to log file")
    view_parser.add_argument(
        "--level", "-l", help="Filter by log level (INFO, DEBUG, WARNING, ERROR)"
    )
    view_parser.add_argument(
        "--event-type", "-e", help="Filter by event type (LogEvent, TraceEvent)"
    )
    view_parser.add_argument(
        "--after", help="Show logs after this time (YYYY-MM-DDTHH:MM:SS)"
    )
    view_parser.add_argument(
        "--before", help="Show logs before this time (YYYY-MM-DDTHH:MM:SS)"
    )
    view_parser.add_argument("--source", "-s", help="Filter by source path")
    view_parser.add_argument("--component", "-c", help="Filter by component name")
    view_parser.add_argument(
        "--message", "-m", help="Filter logs containing this message text"
    )
    view_parser.add_argument(
        "--limit", "-n", type=int, default=100, help="Limit the number of logs shown"
    )
    view_parser.add_argument(
        "--page", "-p", type=int, default=1, help="Page number for pagination"
    )

    # Trace command
    trace_parser = subparsers.add_parser("trace", help="Visualize and explore traces")
    trace_parser.add_argument("log_file", help="Path to log file")
    trace_parser.add_argument("--trace-id", "-t", help="Filter by specific trace ID")
    trace_parser.add_argument(
        "--list-traces", "-l", action="store_true", help="List all available traces"
    )
    trace_parser.add_argument(
        "--sort-by",
        "-s",
        choices=["time", "duration", "spans"],
        default="time",
        help="Sort traces by field",
    )

    # Search command
    search_parser = subparsers.add_parser(
        "search", help="Search logs with advanced queries"
    )
    search_parser.add_argument("log_file", help="Path to log file")
    search_parser.add_argument(
        "--query", "-q", help="Search query (supports field:value syntax)"
    )
    search_parser.add_argument(
        "--regex", "-r", action="store_true", help="Use regular expressions in search"
    )
    search_parser.add_argument(
        "--context",
        "-c",
        type=int,
        default=0,
        help="Show N lines of context before and after matches",
    )
    search_parser.add_argument(
        "--field", "-f", help="Search only in this field (e.g., message, source)"
    )
    search_parser.add_argument(
        "--limit", "-n", type=int, default=100, help="Limit the number of results"
    )

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Generate statistics from logs")
    stats_parser.add_argument("log_file", help="Path to log file")
    stats_parser.add_argument(
        "--time-window",
        "-t",
        type=int,
        default=60,
        help="Time window in seconds for rate calculation",
    )
    stats_parser.add_argument(
        "--top-n", "-n", type=int, default=10, help="Show top N items in each category"
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.command:
        print("Error: You must specify a command.")
        print("Run 'logcli --help' for usage information.")
        sys.exit(1)

    if not os.path.exists(args.log_file):
        print(f"Error: Log file '{args.log_file}' not found.")
        sys.exit(1)

    if args.command == "view":
        log_viewer.view_logs(args)
    elif args.command == "trace":
        traceviz.visualize_traces(args)
    elif args.command == "search":
        log_search.search_logs(args)
    elif args.command == "stats":
        log_stats.generate_stats(args)


if __name__ == "__main__":
    main()
