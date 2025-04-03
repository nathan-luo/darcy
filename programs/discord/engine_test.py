import os
import discord
import asyncio
from discord.ext import commands
import dotenv
import sys
import uuid
import random
import string
from typing import Dict, Optional

# Add the parent directory to the path so we can import from sibling directories
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Import our engine components
from engines.tool_engine import ToolEngine, ToolEnginePromptCommand
from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
from llmgine.bus.bus import MessageBus
from programs.function_chat import get_weather  # The weather tool we'll use
from dataclasses import dataclass, field

dotenv.load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Global bootstrap instance
bootstrap = None
# Dictionary to track active sessions
active_sessions = {}


def generate_session_id(length=5):
    """Generate a random alphanumeric session ID"""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


@dataclass
class DiscordBotConfig(ApplicationConfig):
    """Configuration for the Discord Bot application."""

    # Application-specific configuration
    name: str = "Discord AI Bot"
    description: str = "A Discord bot with AI capabilities"

    enable_tracing: bool = False
    enable_console_handler: bool = True

    # OpenAI configuration
    model: str = "gpt-4o-mini"


@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Check if the bot was mentioned
    if bot.user.mentioned_in(message):
        await process_ai_message(message)

    await bot.process_commands(message)


async def use_engine(command: ToolEnginePromptCommand, session_id: str):
    """Create and configure a new engine for this command.

    This matches the pattern in function_engine_session.py, creating a new
    engine within a session context for each command.
    """
    # Get the MessageBus singleton
    bus = MessageBus()

    # Create a session for this command
    async with bus.create_session(id=session_id) as session:
        # Create a new engine for this command - using session_id as the engine_id too
        engine = ToolEngine(
            session_id=session_id,  # Use the same session_id for the engine
            system_prompt="You are Darcy, a discord assistant for the Data Science Student Society. Always respond in the same style, grammar, syntax and tone as the prompt.",
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",
        )

        # Register tools
        await engine.register_tool(get_weather)

        # Set the session_id on the command if not already set
        if not command.session_id:
            command.session_id = session_id

        # Process the command and return the result
        result = await engine.handle_prompt_command(command)
        return result


async def process_ai_message(message):
    """Process a message with AI assistance."""
    # Generate a unique session ID
    session_id = generate_session_id()
    while session_id in active_sessions:
        session_id = generate_session_id()

    # Initial response with session ID
    response_msg = await message.channel.send(
        f"🔄 **AI Session {session_id}**: Starting..."
    )

    # Track the session
    active_sessions[session_id] = {
        "message": message,
        "response_msg": response_msg,
        "author": message.author,
        "status": "starting",
    }

    try:
        # Extract the content (remove the mention)
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not content:
            content = "Hello"  # Default greeting if no content

        # Create a command with the user's message
        command = ToolEnginePromptCommand(prompt=content)

        # Update status to show we're processing
        await response_msg.edit(content=f"🔄 **AI Session {session_id}**: Processing...")
        active_sessions[session_id]["status"] = "processing"

        # Use engine to process the command (creates new engine within session)
        result = await use_engine(command, session_id)

        # Update the session status
        active_sessions[session_id]["status"] = "completed"

        # Send the response with session ID
        if result.success:
            await response_msg.edit(
                content=f"✅ **AI Session {session_id}**: {result.result}"
            )
        else:
            await response_msg.edit(
                content=f"❌ **AI Session {session_id} Error**: {result.error}"
            )

    except Exception as e:
        active_sessions[session_id]["status"] = "error"
        await response_msg.edit(content=f"❌ **AI Session {session_id} Error**: {str(e)}")


async def main():
    """Main function to bootstrap the application and run the bot."""
    global bootstrap

    # Bootstrap the application once
    config = DiscordBotConfig()
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()

    # Start the message bus
    bus = MessageBus()
    await bus.start()
    print("Message bus started")

    try:
        # Run the bot
        await bot.start(os.getenv("DARCY_KEY"))
    finally:
        # Ensure the bus is stopped when the application ends
        await bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
