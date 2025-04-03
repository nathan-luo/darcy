import discord
import asyncio
import random
import string
from discord.ext import commands
import os
import dotenv

dotenv.load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store active sessions
active_sessions = {}


def generate_session_id(length=5):
    """Generate a random alphanumeric session ID"""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message):
        await start_ai_session(message)

    await bot.process_commands(message)


async def start_ai_session(message):
    # Generate a unique session ID
    session_id = generate_session_id()
    while session_id in active_sessions:
        session_id = generate_session_id()

    # Create session message with ID
    session_msg = await message.channel.send(
        f"🔄 **AI Session {session_id} starting...**"
    )

    # Store session information
    active_sessions[session_id] = {
        "message": message,
        "session_msg": session_msg,
        "author": message.author,
        "channel": message.channel,
        "status": "starting",
        "result": None,
    }

    # Simulate initial processing
    async with message.channel.typing():
        await asyncio.sleep(1.5)
        await session_msg.edit(content=f"🔄 **AI Session {session_id}**: Loading data...")
        active_sessions[session_id]["status"] = "loading"
        await asyncio.sleep(1.5)
        await session_msg.edit(
            content=f"🔄 **AI Session {session_id}**: Processing request..."
        )
        active_sessions[session_id]["status"] = "processing"
        await asyncio.sleep(1.5)

    # Update status to waiting for input - your external program would check for this
    await session_msg.edit(
        content=f"⏳ **AI Session {session_id}**: Waiting for external input..."
    )
    active_sessions[session_id]["status"] = "waiting_for_input"

    # Your external program would call request_user_input() at this point


async def request_user_input(session_id, prompt_text):
    """Function to be called by your external program to request user input"""
    if session_id not in active_sessions:
        return {"error": "Session not found"}

    session = active_sessions[session_id]
    if session["status"] != "waiting_for_input":
        return {"error": f"Session in wrong state: {session['status']}"}

    # Update status
    session["status"] = "requesting_input"
    await session["session_msg"].edit(
        content=f"🔄 **AI Session {session_id}**: User input requested..."
    )

    # Create the view for Yes/No input
    view = YesNoView(timeout=60, original_author=session["author"])
    prompt_msg = await session["channel"].send(
        content=f"⚠️ **AI Session {session_id}**: {session['author'].mention}, {prompt_text}",
        view=view,
    )

    # Wait for the user to respond
    await view.wait()

    # Process the result
    if view.value is None:
        result = {"response": "timeout"}
        await session["session_msg"].edit(
            content=f"❌ **AI Session {session_id}**: Timed out - no response received"
        )
    else:
        result = {"response": "yes" if view.value else "no"}
        resp_text = "✅ User confirmed" if view.value else "❌ User declined"
        await prompt_msg.edit(content=f"{resp_text}", view=None)

    # Update session status and return result
    session["status"] = "input_received"
    session["result"] = result
    return result


async def continue_session(session_id, final_text=None):
    """Function to continue or complete a session after receiving input"""
    if session_id not in active_sessions:
        return {"error": "Session not found"}

    session = active_sessions[session_id]

    # Update status to continuing
    session["status"] = "continuing"
    await session["session_msg"].edit(
        content=f"🔄 **AI Session {session_id}**: Processing response..."
    )

    # Simulate some processing
    async with session["channel"].typing():
        await asyncio.sleep(2)

    # Complete the session
    if final_text:
        await session["session_msg"].edit(
            content=f"✅ **AI Session {session_id} complete**: {final_text}"
        )
    else:
        await session["session_msg"].edit(
            content=f"✅ **AI Session {session_id} complete**"
        )

    # Mark session as completed (or you could remove it from active_sessions)
    session["status"] = "completed"
    return {"status": "completed"}


class YesNoView(discord.ui.View):
    def __init__(self, timeout, original_author):
        super().__init__(timeout=timeout)
        self.value = None
        self.original_author = original_author

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


# Example command to control sessions from Discord (for testing)
@bot.command(name="input")
async def request_input_command(ctx, session_id):
    """Test command to request input for a specific session"""
    if session_id in active_sessions:
        await ctx.send(f"Requesting input for session {session_id}")
        result = await request_user_input(session_id, "Do you want to proceed?")
        await ctx.send(f"Input result: {result}")

        if result.get("response") == "yes":
            await continue_session(session_id, "Process completed successfully!")
        else:
            await continue_session(session_id, "Process canceled by user")
    else:
        await ctx.send(f"Session {session_id} not found")


bot.run(os.getenv("DARCY_KEY"))
