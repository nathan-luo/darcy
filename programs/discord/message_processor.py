"""
This module processes messages from the discord server.
It processes: 
- mentions
- author payload
- chat history
- reply payload
"""

import discord
import sys
import os

from config import DiscordBotConfig
from session_manager import SessionManager

# Add the parent directory to the path so we can import from sibling directories
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from tools.notion.data import DISCORD_TO_NOTION_USER_MAP

class MessageProcessor:
    def __init__(self, config: DiscordBotConfig, session_manager: SessionManager):
        self.config = config
        self.session_manager = session_manager

    async def process_mention(self, message: discord.Message) -> None:
        """Process a message where the bot is mentioned."""
        session_id = await self.session_manager.create_session(message, expire_after_minutes=1)
        
        # Process user mentions
        user_mentions = self._process_mentions(message)
        author_payload = self._create_author_payload(message)
        chat_history = await self._get_chat_history(message)
        reply_payload = await self._process_reply(message)

        # Combine all payloads
        message.content = (
            message.content
            + f"\n\n{reply_payload}\n\n{author_payload}\n\n{user_mentions}\n\n{chat_history}"
        )

        return message, session_id

    def _process_mentions(self, message: discord.Message) -> str:
        """Process user mentions in the message."""
        user_mentions = [user.id for user in message.mentions]
        mentions_payload = []
        for user_mention in user_mentions:
            if user_mention == self.config.bot_id:
                continue
            mentions_payload.append({
                user_mention: DISCORD_TO_NOTION_USER_MAP[str(user_mention)]
            })
        return str(mentions_payload)

    def _create_author_payload(self, message: discord.Message) -> str:
        """Create payload for the message author."""
        return "The Author of this message is:" + str({
            message.author.id: DISCORD_TO_NOTION_USER_MAP[str(message.author.id)]
        })

    async def _get_chat_history(self, message: discord.Message) -> str:
        """Get recent chat history from the channel."""
        chat_history = []
        async for msg in message.channel.history(limit=20):
            if msg.author.id == self.config.bot_id:
                if "Result" not in msg.content:
                    continue
            chat_history.append(f"{msg.author.display_name}: {msg.content}")

        chat_history.reverse()
        return "Chat History:\n" + "\n".join(chat_history)

    async def _process_reply(self, message: discord.Message) -> str:
        """Process message replies."""
        if message.reference is None:
            return ""

        replied_message = await message.channel.fetch_message(
            message.reference.message_id
        )
        return f"The current request is responding to a message, and that message is: {replied_message.author.display_name}: {replied_message.content}" 