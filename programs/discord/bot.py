"""
This module creates and assembles the discord bot.
Components include:
- Configuration
- Session manager
- Message processor
- Engine manager

The bot is started here.
"""

import asyncio
import discord
from discord.ext import commands
import logging

from config import DiscordBotConfig
from session_manager import SessionManager
from message_processor import MessageProcessor
from engine_manager import EngineManager
from llmgine.bootstrap import ApplicationBootstrap
from llmgine.bus.bus import MessageBus

# Configure logging
logging.basicConfig(level=logging.INFO)
class DarcyBot:
    def __init__(self):
        # Load configuration
        self.config = DiscordBotConfig.load_from_env()
        
        # Initialize Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        # Initialize managers
        self.session_manager = SessionManager(self.bot)
        self.message_processor = MessageProcessor(self.config, self.session_manager)
        self.engine_manager = EngineManager(self.config, self.session_manager)
        
        # Set up event handlers
        self.bot.event(self.on_ready)
        self.bot.event(self.on_message)

    async def on_ready(self):
        """Called when the bot is ready to start."""
        print(f"Logged in as {self.bot.user}")

    async def on_message(self, message):
        """Handle incoming messages."""
        if message.author == self.bot.user:
            return

        if self.bot.user.mentioned_in(message):
            # Process the message
            processed_message, session_id = await self.message_processor.process_mention(message)
            
            # Create command and use engine
            from engines.notion_crud_engine_v2 import NotionCRUDEnginePromptCommand
            command = NotionCRUDEnginePromptCommand(prompt=processed_message.content)
            result = await self.engine_manager.use_engine(command, session_id)
            
            # Send response
            if result.result:
                await message.channel.send(
                    f"🎁 **Session {session_id} Result**: \n\n{result.result[:self.config.max_response_length]}"
                )
            else:
                await message.channel.send(
                    f"❌ **Session {session_id} Error**: An error occurred, please be more specific. Or I just messed up Lol."
                )
            
            # Complete the session
            await self.session_manager.complete_session(session_id, "Session completed")

        await self.bot.process_commands(message)

    async def start(self):
        """Start the bot and all necessary services."""
        # Bootstrap the application
        bootstrap = ApplicationBootstrap(self.config)
        await bootstrap.bootstrap()

        # Start the message bus
        bus = MessageBus()
        await bus.start()

        try:
            # Run the bot
            await self.bot.start(self.config.bot_key)
        finally:
            # Ensure the bus is stopped when the application ends
            await bus.stop()

async def main():
    """Main entry point for the bot."""
    bot = DarcyBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main()) 