from discord import ButtonStyle, Interaction
from discord.ui import button, Button, View
from typing import Callable


class ControlsView(View):
    def __init__(self, clip_that_func: Callable, leave_vc_func: Callable):
        super().__init__()
        self.clip_that_func = clip_that_func
        self.leave_vc_func = leave_vc_func

    @button(label="Clip That",
            style=ButtonStyle.primary)
    async def btn_clip_that(self, button: Button, interaction: Interaction):
        await self.clip_that_func(respond_func=interaction.respond,
                                  guild=interaction.guild,
                                  user=interaction.user)

    @button(label="Leave",
            style=ButtonStyle.danger)
    async def btn_leave_vc(self, button: Button, interaction: Interaction):
        await self.leave_vc_func(respond_func=interaction.respond,
                                 guild=interaction.guild,
                                 user=interaction.user)
