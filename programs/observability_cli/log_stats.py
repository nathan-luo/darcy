#!/usr/bin/env python3
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Make sure we can import log_parser.py from the same directory
sys.path.insert(0, str(Path(__file__).parent))
import log_parser

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate statistics and metrics from logs."
    )
    parser.add_argument("log_file", type=str, help="Path to log file")
    parser.add_argument(
        "--time-window",
        "-t",
        type=int,
        default=60,
        help="Time window in seconds for rate calculation",
    )
    parser.add_argument(
        "--top-n", "-n", type=int, default=10, help="Show top N items in each category"
    )
    return parser.parse_args()


def generate_stats(args):
    # Load logs
    logs = log_parser.load_logs(args.log_file)
    console.print(f"[bold]Loaded [green]{len(logs)}[/green] log entries[/bold]")

    # Calculate metrics
    metrics = log_parser.calculate_metrics(logs)

    # Header
    header_text = Text()
    header_text.append("\n📊 Log Statistics Summary\n", style="bold blue")
    header_text.append(f"Total logs: {metrics['total_logs']}", style="green")
    console.print(header_text)

    # Calculate log rate over time
    log_times = [datetime.fromisoformat(log["timestamp"]) for log in logs]
    log_times.sort()

    if log_times:
        start_time = log_times[0]
        end_time = log_times[-1]
        duration = (end_time - start_time).total_seconds()
        overall_rate = len(logs) / duration if duration > 0 else 0

        # Calculate rates in time windows
        window_rates = []
        current_time = start_time
        while current_time <= end_time:
            window_end = current_time + timedelta(seconds=args.time_window)
            window_logs = [
                log
                for log in logs
                if current_time <= datetime.fromisoformat(log["timestamp"]) < window_end
            ]
            window_rates.append((current_time, len(window_logs) / args.time_window))
            current_time = window_end

        # Create rate panel with simple bars
        rate_lines = []
        if window_rates:
            max_rate = max(rate for _, rate in window_rates)

            # Only take the last 10 windows to show recent activity
            display_rates = window_rates[-10:] if len(window_rates) > 10 else window_rates

            for time, rate in display_rates:
                bar_width = 40
                filled_width = int((rate / max_rate) * bar_width) if max_rate > 0 else 0
                bar = f"[{'=' * filled_width}{' ' * (bar_width - filled_width)}]"
                rate_lines.append(f"{time.strftime('%H:%M:%S')} {bar} {rate:.2f}/s")

        rate_text = "\n".join(rate_lines)
        console.print(
            Panel(
                f"Overall rate: [bold green]{overall_rate:.2f}[/bold green] logs/second over "
                f"[bold]{duration:.1f}[/bold] seconds\n\n{rate_text}",
                title=f"📈 Log Rate (per {args.time_window}s window)",
                expand=False,
            )
        )

    # Log levels table
    levels_table = Table(title="📋 Log Levels", show_header=True, header_style="bold")
    levels_table.add_column("Level", style="dim")
    levels_table.add_column("Count", justify="right")
    levels_table.add_column("Percentage", justify="right")
    levels_table.add_column("Distribution", width=30)

    # Create a progress bar for each level
    total_logs = metrics["total_logs"]
    for level, count in sorted(
        metrics["log_levels"].items(), key=lambda x: x[1], reverse=True
    ):
        if not level:
            continue
        percentage = count / total_logs * 100
        level_style = {
            "INFO": "green",
            "DEBUG": "blue",
            "WARNING": "yellow",
            "ERROR": "red",
        }.get(level, "white")

        # Create a simple progress bar
        bar_width = 30
        filled_width = int((count / total_logs) * bar_width)
        bar = f"[{level_style}]{'█' * filled_width}[/{level_style}]{' ' * (bar_width - filled_width)}"

        levels_table.add_row(
            Text(level, style=level_style), str(count), f"{percentage:.1f}%", bar
        )

    console.print(levels_table)

    # Event types table
    event_types_table = Table(
        title="🔄 Event Types", show_header=True, header_style="bold"
    )
    event_types_table.add_column("Event Type", style="dim")
    event_types_table.add_column("Count", justify="right")
    event_types_table.add_column("Percentage", justify="right")

    for event_type, count in sorted(
        metrics["event_types"].items(), key=lambda x: x[1], reverse=True
    ):
        if not event_type:
            continue
        percentage = count / total_logs * 100
        event_types_table.add_row(event_type, str(count), f"{percentage:.1f}%")

    console.print(event_types_table)

    # Components table
    components_table = Table(title="🧩 Components", show_header=True, header_style="bold")
    components_table.add_column("Component", style="dim")
    components_table.add_column("Count", justify="right")
    components_table.add_column("Percentage", justify="right")

    for component, count in sorted(
        metrics["components"].items(), key=lambda x: x[1], reverse=True
    )[: args.top_n]:
        if not component:
            continue
        percentage = count / total_logs * 100
        components_table.add_row(component, str(count), f"{percentage:.1f}%")

    console.print(components_table)

    # Traces table
    traces_table = Table(
        title=f"🔍 Top {args.top_n} Traces", show_header=True, header_style="bold"
    )
    traces_table.add_column("Trace ID", style="dim", width=36)
    traces_table.add_column("Spans", justify="right")
    traces_table.add_column("Status", width=30)

    # Sort traces by span count
    sorted_traces = sorted(
        metrics["traces"].items(), key=lambda x: x[1]["span_count"], reverse=True
    )[: args.top_n]

    for trace_id, trace_info in sorted_traces:
        status_text = ""
        for status, count in trace_info["status"].items():
            status_style = {
                "OK": "green",
                "success": "green",
                "warning": "yellow",
                "error": "red",
            }.get(status, "white")
            status_text += f"[{status_style}]{status}: {count}[/{status_style}] "

        traces_table.add_row(
            trace_id, str(trace_info["span_count"]), Text.from_markup(status_text)
        )

    console.print(traces_table)

    # Warnings and errors
    if metrics["warnings"]:
        warnings_text = "\n".join([
            f"[yellow]{log_parser.extract_time_part(w['timestamp'])}[/yellow] "
            f"[yellow bold]{w['source'].split('/')[-1] if w['source'] else ''}:[/yellow bold] {w['message']}"
            for w in metrics["warnings"][:5]
        ])
        console.print(
            Panel(
                warnings_text,
                title=f"⚠️ Recent Warnings ({len(metrics['warnings'])} total)",
                style="yellow",
            )
        )

    if metrics["errors"]:
        errors_text = "\n".join([
            f"[red]{log_parser.extract_time_part(e['timestamp'])}[/red] "
            f"[red bold]{e['source'].split('/')[-1] if e['source'] else ''}:[/red bold] {e['message']}"
            for e in metrics["errors"][:5]
        ])
        console.print(
            Panel(
                errors_text,
                title=f"🔴 Recent Errors ({len(metrics['errors'])} total)",
                style="red",
            )
        )

    # Summary footer
    console.print("\n[bold blue]📝 Summary:[/bold blue]")
    if log_times:
        console.print(f"• Log span: {start_time.isoformat()} to {end_time.isoformat()}")
        console.print(f"• Duration: {duration:.2f} seconds")
    console.print(f"• Log types: {len(metrics['event_types'])} different event types")
    console.print(f"• Components: {len(metrics['components'])} different components")
    console.print(f"• Traces: {len(metrics['traces'])} distinct trace IDs")


def main():
    args = parse_args()
    generate_stats(args)


if __name__ == "__main__":
    main()
