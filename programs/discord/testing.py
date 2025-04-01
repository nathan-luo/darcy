import discord 
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os

load_dotenv()

DARCY_KEY = os.getenv('DARCY_KEY')
TEST_SERVER_ID = int(os.getenv('TEST_SERVER_ID'))
GUILD_OBJECT = discord.Object(id=TEST_SERVER_ID)

class Client(commands.Bot):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.sessions = {}

    async def on_ready(self):
        print(f'Logged in as {self.user}')

        try:
            synced = await self.tree.sync(guild=GUILD_OBJECT)
            print(f'Synced {len(synced)} commands')
        except Exception as e:
            print(f'Error syncing commands: {e}')

    async def on_message(self, message):
        if message.author == self.user:
            return

         # Check if Darcy was mentioned in the message
        if self.user.mentioned_in(message):
            # Start a session for the user
            user_id = message.author.id
            if user_id not in self.sessions:
                self.sessions[user_id] = {"booms": 0}
                await message.channel.send(f"Session started for {message.author.name}. You have 0 big boom.")
            else:
                await message.channel.send(f"{message.author.name}, you already have an active session. Get working on those booms.")

    async def setup_hook(self):
        """Registers all slash commands for the guild."""
        guild = GUILD_OBJECT  # Discord server ID
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


client = Client()

# --- SLASH COMMANDS ---
@client.tree.command(name="one_big_boom", description="Increase your BOOM count!", guild=GUILD_OBJECT)
async def one_big_boom(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id in client.sessions:
        client.sessions[user_id]["booms"] += 1
        await interaction.response.send_message(f"Now at {client.sessions[user_id]['booms']} big BOOMS!")
    else:
        await interaction.response.send_message("Start a session first by mentioning me (@bot_name).")

@client.tree.command(name="boom_status", description="Check your BOOM count.", guild=GUILD_OBJECT)
async def boom_status(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id in client.sessions:
        boom_count = client.sessions[user_id]["booms"]
        response = f"You're currently at {boom_count} big BOOMS.\n" + ("BOOM!\n" * boom_count)
        await interaction.response.send_message(response)
    else:
        await interaction.response.send_message("You don't have an active session.")

@client.tree.command(name="end", description="End your BOOM session.", guild=GUILD_OBJECT)
async def end(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id in client.sessions:
        del client.sessions[user_id]
        await interaction.response.send_message("Your session has been ended.")
    else:
        await interaction.response.send_message("You don't have an active session.")

client.run(DARCY_KEY)
