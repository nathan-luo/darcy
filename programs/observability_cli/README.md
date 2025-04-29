# LLMgine Log Analysis Tools

A set of tools for analyzing, parsing, and visualizing LLMgine logs and traces with rich terminal output.

## Features

- **Log viewing** with filtering by level, component, event type, etc.
- **Trace visualization** with hierarchical span trees
- **Advanced log search** with field-specific queries and regex support
- **Statistics and metrics** generation from logs
- **Rich terminal output** with color-coding and formatted tables

## Tools

### Main CLI (`logcli.py`)

A unified command-line interface for all tools:

```bash
# View and filter logs
python logcli.py view path/to/logs.json --level WARNING

# Visualize traces
python logcli.py trace path/to/logs.json --trace-id "8607736c-7aa3-4084-aa8b-bb62094ab80b"

# Search logs
python logcli.py search path/to/logs.json --query "error" --context 2

# Generate statistics
python logcli.py stats path/to/logs.json
```

### Log Viewer (`log_viewer.py`)

View and filter logs with rich formatting:

```bash
python log_viewer.py path/to/logs.json
python log_viewer.py path/to/logs.json --level INFO
python log_viewer.py path/to/logs.json --component MessageBus
python log_viewer.py path/to/logs.json --message "error"
```

Options:
- `--level`, `-l`: Filter by log level (INFO, DEBUG, WARNING, ERROR)
- `--event-type`, `-e`: Filter by event type (LogEvent, TraceEvent)
- `--source`, `-s`: Filter by source path
- `--component`, `-c`: Filter by component name
- `--message`, `-m`: Filter logs containing this message text
- `--limit`, `-n`: Limit the number of logs shown
- `--page`, `-p`: Page number for pagination

### Trace Visualizer (`traceviz.py`)

Visualize and explore distributed traces:

```bash
python traceviz.py path/to/logs.json --list-traces
python traceviz.py path/to/logs.json --trace-id "8607736c-7aa3-4084-aa8b-bb62094ab80b"
python traceviz.py path/to/logs.json --sort-by duration
```

Options:
- `--trace-id`, `-t`: Filter by specific trace ID
- `--list-traces`, `-l`: List all available traces
- `--sort-by`, `-s`: Sort traces by field (time, duration, spans)

### Log Search (`log_search.py`)

Search logs with advanced query capabilities:

```bash
python log_search.py path/to/logs.json --query "error"
python log_search.py path/to/logs.json --query "level:WARNING"
python log_search.py path/to/logs.json --regex --query "failed|error"
python log_search.py path/to/logs.json --query "error" --context 2
```

Options:
- `--query`, `-q`: Search query (supports field:value syntax)
- `--regex`, `-r`: Use regular expressions in search
- `--context`, `-c`: Show N lines of context before and after matches
- `--field`, `-f`: Search only in this field (e.g., message, source)
- `--limit`, `-n`: Limit the number of results

### Log Statistics (`log_stats.py`)

Generate statistics and metrics from logs:

```bash
python log_stats.py path/to/logs.json
python log_stats.py path/to/logs.json --time-window 30
python log_stats.py path/to/logs.json --top-n 5
```

Options:
- `--time-window`, `-t`: Time window in seconds for rate calculation
- `--top-n`, `-n`: Show top N items in each category

## Requirements

- Python 3.7+
- Rich library (`pip install rich`)
