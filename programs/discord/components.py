import discord


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
