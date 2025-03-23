#!/usr/bin/env python3
"""Command-line script to run the LLMgine chatbot using the bootstrap pattern."""

import argparse
import asyncio
import logging
import sys

from llmgine.ui.cli.bootstrap import ChatbotConfig, create_and_run_chatbot


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="LLMgine Chatbot")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="chatbot.log",
        help="Path to log file"
    )
    parser.add_argument(
        "--no-event-logging",
        action="store_true",
        help="Disable event logging"
    )
    parser.add_argument(
        "--logs-dir",
        type=str,
        default="logs",
        help="Directory for log files"
    )
    parser.add_argument(
        "--system-prompt",
        type=str,
        help="Custom system prompt for the chatbot"
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Parse arguments
    args = parse_args()

    # Configure the chatbot
    config = ChatbotConfig(
        log_level=logging.DEBUG if args.debug else logging.INFO,
        log_file=args.log_file,
        logs_dir=args.logs_dir,
        event_logging_enabled=not args.no_event_logging,
    )
    
    # Set custom system prompt if provided
    if args.system_prompt:
        config.system_prompt = args.system_prompt

    # Run the chatbot
    asyncio.run(create_and_run_chatbot(config))
