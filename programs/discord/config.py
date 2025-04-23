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





import os
import dotenv

dotenv.load_dotenv()

def validate_env_keys() :

  assert(os.getenv("NOT A KEY") == None)

  # TODO move this somewhere else
  required_keys = [
    "NOTION_API_KEY", 
    "NOTION_TESTING_DATABASE_ID", 
    "NOTION_PRODUCTION_DATABASE_ID_TASKS",
    "NOTION_PRODUCTION_DATABASE_ID_PROJECTS",
    "DARCY_KEY", 
    "DARCY_ID",
    "DARYL_KEY",
    "DARYL_ID",
    "TEST_SERVER_ID",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY"
  ]


  for key in required_keys :
    val = os.getenv(key)
    if (val == None) :
      raise Exception(f"{key} is not in env keys")








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
    bot_id: int = os.getenv("BOT_ID")

    @classmethod
    def load_from_env(cls) -> 'DiscordBotConfig':
        """Load configuration from environment variables."""
        validate_env_keys()
        dotenv.load_dotenv(override=True)
        config = cls()
        config.bot_key = os.getenv("BOT_KEY")
        return config 