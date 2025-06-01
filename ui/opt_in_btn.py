import discord
import modules.database as db


class OptInButton(discord.ui.Button):
    def __init__(self, guild: discord.Guild):
        super().__init__(label="Opt In",
                         style=discord.ButtonStyle.primary)
        self.guild = guild

    async def callback(self, interaction: discord.Interaction):
        db.set_opted_in_status(guild=self.guild,
                               user=interaction.user,
                               opted_in=True)
        await interaction.respond("You are now opted in to voice capture")
