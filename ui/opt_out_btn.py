from discord import ButtonStyle, Member, Interaction
from discord.ui import Button
from typing import Callable


class OptOutButton(Button):
    def __init__(self, member: Member, opt_out_handler: Callable):
        super().__init__(label="Opt Out",
                         style=ButtonStyle.red)
        self.member = member
        self.guild = member.guild
        self.opt_out_handler = opt_out_handler

    async def callback(self, interaction: Interaction):
        await self.opt_out_handler(dm=await self.member.create_dm(),
                                   guild=self.guild,
                                   member=self.member)
        await interaction.response.defer()
