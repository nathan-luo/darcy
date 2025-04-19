"""
This module contains the configuration for Darcy:
- Name
- Description
- Enable tracing
- Enable console handler
- LLM Model
- Maximum response length
- Discord bot key
- Bot ID

It also loads Darcy's key from the environment variables.
"""

from dataclasses import dataclass
import os
import dotenv
import sys

# Add the parent directory to the path so we can import from sibling directories
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from llmgine.bootstrap import ApplicationConfig

@dataclass
class DiscordBotConfig(ApplicationConfig):
    """Configuration for the Discord Bot application."""
    # Application-specific configuration
    name: str = "Discord AI Bot"
    description: str = "A Discord bot with AI capabilities"
    enable_tracing: bool = False
    enable_console_handler: bool = False

    # OpenAI configuration
    model: str = "gpt-4o"
    
    # Discord configuration
    max_response_length: int = 1900
    bot_key: str = ''
    bot_id: int = 1358692586000355409

    @classmethod
    def load_from_env(cls) -> 'DiscordBotConfig':
        """Load configuration from environment variables."""
        dotenv.load_dotenv(override=True)
        config = cls()
        config.bot_key = os.getenv("DARYL_KEY")
        return config 