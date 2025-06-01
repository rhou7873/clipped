import discord
from typing import Callable


class OptInButton(discord.ui.Button):
    def __init__(self, member: discord.Member, opt_in_handler: Callable):
        super().__init__(label="Opt In",
                         style=discord.ButtonStyle.primary)
        self.member = member
        self.guild = member.guild
        self.opt_in_handler = opt_in_handler

    async def callback(self, interaction: discord.Interaction):
        await self.opt_in_handler(dm=await self.member.create_dm(),
                                  guild=self.guild,
                                  member=self.member)
        await interaction.response.defer()
