import discord
import modules.database as db


class OptOutButton(discord.ui.Button):
    def __init__(self, guild: discord.Guild):
        super().__init__(label="Opt Out",
                         style=discord.ButtonStyle.red)
        self.guild = guild

    async def callback(self, interaction: discord.Interaction):
        db.set_opted_in_status(guild=self.guild,
                               user=interaction.user,
                               opted_in=False)
        await interaction.respond("You are now opted out of voice capture")
