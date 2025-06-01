import discord
from typing import Callable


class ControlsView(discord.ui.View):
    def __init__(self, clip_that_func: Callable, leave_vc_func: Callable):
        super().__init__()
        self.clip_that_func = clip_that_func
        self.leave_vc_func = leave_vc_func

    @discord.ui.button(label="Clip That",
                       style=discord.ButtonStyle.primary)
    async def btn_clip_that(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.clip_that_func()

    @discord.ui.button(label="Leave",
                       style=discord.ButtonStyle.danger)
    async def btn_leave_vc(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.leave_vc_func(respond_func=interaction.respond,
                                 guild=interaction.guild)
