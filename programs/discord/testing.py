import discord 
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os

load_dotenv()

DARCY_KEY = os.getenv('DARCY_KEY')
TEST_SERVER_ID = os.getenv('TEST_SERVER_ID')

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

        try:
            synced = await self.tree.sync(guild=GUILD_ID)
            print(f'Synced {len(synced)} commands')
        except Exception as e:
            print(f'Error syncing commands: {e}')

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.startswith('ping'):
            await message.channel.send('pong')

intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix='!', intents=intents)

GUILD_ID = discord.Object(TEST_SERVER_ID)  # Test server ID

@client.tree.command(name="test", description="Test command", guild=GUILD_ID)
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Test command executed!")

client.run(DARCY_KEY)
