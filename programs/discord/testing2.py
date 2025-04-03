import os
import discord
import asyncio
from discord.ext import commands
import dotenv

dotenv.load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
# Remove the incorrect line: intents.mentions = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Check if the bot was mentioned
    if bot.user.mentioned_in(message):
        await start_ai_session(message)

    await bot.process_commands(message)


async def start_ai_session(message):
    # Initial response to create the session
    session_msg = await message.channel.send("🔄 **AI Session starting...**")

    # Simulate processing with a "typing" indicator and status updates
    async with message.channel.typing():
        await asyncio.sleep(1.5)
        await session_msg.edit(content="🔄 **AI Session**: Loading data...")
        await asyncio.sleep(1.5)
        await session_msg.edit(content="🔄 **AI Session**: Processing request...")
        await asyncio.sleep(1.5)

    # Now ask for user input with buttons
    view = YesNoView(timeout=60, original_author=message.author)
    prompt_msg = await message.channel.send(
        content=f"⚠️ **AI Session requires input**: {message.author.mention}, do you want to proceed?",
        view=view,
    )

    # Wait for the user to respond
    await view.wait()

    # Check the result and continue the session
    if view.value is None:
        await session_msg.edit(
            content="❌ **AI Session**: Timed out - no response received"
        )
        await prompt_msg.edit(view=None)
    elif view.value:
        await prompt_msg.edit(content="✅ User confirmed: Proceeding", view=None)
        await session_msg.edit(content="🔄 **AI Session**: Continuing with process...")
        await asyncio.sleep(1.5)
        await session_msg.edit(
            content="✅ **AI Session complete**: Here are your results..."
        )
        # Add your actual response logic here
    else:
        await prompt_msg.edit(content="❌ User declined", view=None)
        await session_msg.edit(content="❌ **AI Session**: Canceled by user")


class YesNoView(discord.ui.View):
    def __init__(self, timeout, original_author):
        super().__init__(timeout=timeout)
        self.value = None
        self.original_author = original_author

    # Check that only the original message author can interact with buttons
    async def interaction_check(self, interaction):
        return interaction.user == self.original_author

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction, button):
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(self, interaction, button):
        self.value = False
        await interaction.response.defer()
        self.stop()


bot.run(os.getenv("DARCY_KEY"))
