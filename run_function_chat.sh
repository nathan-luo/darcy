#!/bin/bash

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "OPENAI_API_KEY environment variable is not set."
    echo "Please set it using: export OPENAI_API_KEY=your-api-key"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Create sessions directory if it doesn't exist
mkdir -p sessions

# Print help if requested
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: ./run_function_chat.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --list-sessions       List all available sessions"
    echo "  --session <id>        Resume a specific session"
    echo "  --session-name <name> Create a new session with this name"
    echo "  --model <model>       Specify the OpenAI model to use (default: gpt-4o-mini)"
    echo "  --system-prompt <text> Set a custom system prompt"
    echo "  --log-level <level>   Set the log level (debug, info, warning, error, critical)"
    echo "  --log-dir <dir>       Specify the directory for log files"
    echo "  --no-console          Disable console output for events"
    echo "  --help, -h            Show this help message"
    exit 0
fi

# Run the function chat application
python programs/function_chat.py "$@" 