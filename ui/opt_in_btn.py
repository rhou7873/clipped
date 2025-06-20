from discord import ButtonStyle, Interaction, Member
from discord.ui import Button
from typing import Callable


class OptInButton(Button):
    def __init__(self, member: Member, opt_in_handler: Callable):
        super().__init__(label="Opt In",
                         style=ButtonStyle.primary)
        self.member = member
        self.guild = member.guild
        self.opt_in_handler = opt_in_handler

    async def callback(self, interaction: Interaction):
        await self.opt_in_handler(dm=await self.member.create_dm(),
                                  guild=self.guild,
                                  member=self.member)
        await interaction.response.defer()
