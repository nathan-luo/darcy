#!/usr/bin/env python3

import argparse
import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

class LogViewer:
    def __init__(self):
        self.console = Console()
        
    def parse_filter(self, filter_str: str) -> tuple:
        """Parse a filter string in the format 'key = value'"""
        if not filter_str:
            return None, None, None
            
        # Match patterns like "key = value", "key==value", "key!=value", etc.
        pattern = r'^\s*(\w+)\s*([=!<>]=?|=)\s*(.+?)\s*$'
        match = re.match(pattern, filter_str)
        
        if not match:
            self.console.print("[bold red]Invalid filter format. Use 'key = value'[/bold red]")
            sys.exit(1)
            
        key, operator, value = match.groups()
        
        # Remove quotes if present
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
            
        return key, operator, value
    
    def apply_filter(self, log_entry: Dict[str, Any], key: str, operator: str, value: str) -> bool:
        """Apply filter to a log entry"""
        if key not in log_entry:
            return False
            
        log_value = log_entry[key]
        
        # Convert value to appropriate type for comparison
        if isinstance(log_value, int):
            try:
                value = int(value)
            except ValueError:
                pass
        elif isinstance(log_value, float):
            try:
                value = float(value)
            except ValueError:
                pass
        
        # Handle different operators
        if operator == '=' or operator == '==':
            return log_value == value
        elif operator == '!=':
            return log_value != value
        elif operator == '>':
            return log_value > value
        elif operator == '<':
            return log_value < value
        elif operator == '>=':
            return log_value >= value
        elif operator == '<=':
            return log_value <= value
        else:
            return False
    
    def load_logs(self, log_file: Path) -> List[Dict[str, Any]]:
        """Load logs from a file. Each line should be a JSON object."""
        logs = []
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # Skip invalid JSON lines
                        continue
        except FileNotFoundError:
            self.console.print(f"[bold red]Log file not found: {log_file}[/bold red]")
            sys.exit(1)
        
        return logs
    
    def display_logs(self, logs: List[Dict[str, Any]]):
        """Display logs using Rich"""
        if not logs:
            self.console.print("[yellow]No logs matched the filter criteria.[/yellow]")
            return
            
        for i, log in enumerate(logs):
            # Create a panel for each log entry
            json_str = json.dumps(log, indent=2)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
            panel = Panel(
                syntax,
                title=f"Log Entry #{i+1}",
                border_style="blue"
            )
            self.console.print(panel)
            
            # Add a separator between logs
            if i < len(logs) - 1:
                self.console.print("─" * 80)
    
    def display_summary(self, logs: List[Dict[str, Any]], filtered_logs: List[Dict[str, Any]]):
        """Display a summary of the filtered logs"""
        table = Table(title="Log Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total logs", str(len(logs)))
        table.add_row("Filtered logs", str(len(filtered_logs)))
        table.add_row("Filter ratio", f"{len(filtered_logs)/len(logs):.2%}" if logs else "N/A")
        
        self.console.print(table)
        self.console.print()
    
    def run(self, log_file: str, filter_str: Optional[str] = None):
        """Main method to run the log viewer"""
        # Parse filter
        key, operator, value = self.parse_filter(filter_str)
        
        # Load logs
        log_path = Path(log_file)
        logs = self.load_logs(log_path)
        
        # Apply filter
        if key and operator and value:
            filtered_logs = [
                log for log in logs 
                if self.apply_filter(log, key, operator, value)
            ]
        else:
            filtered_logs = logs
        
        # Display summary
        self.display_summary(logs, filtered_logs)
        
        # Display filtered logs
        self.display_logs(filtered_logs)


def main():
    parser = argparse.ArgumentParser(description="Log viewer with filtering capabilities")
    parser.add_argument("log_file", help="Path to the log file")
    parser.add_argument("--filter", help="Filter in format 'key = value'")
    args = parser.parse_args()
    
    viewer = LogViewer()
    viewer.run(args.log_file, args.filter)


if __name__ == "__main__":
    main() 