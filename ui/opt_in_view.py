import discord
from ui import OptInButton, OptOutButton


class OptInView(discord.ui.View):
    def __init__(self,
                 guild: discord.Guild,
                 show_opt_in: bool = False,
                 show_opt_out: bool = False):
        super().__init__()

        if show_opt_in:
            self.add_item(OptInButton(guild))
        if show_opt_out:
            self.add_item(OptOutButton(guild))
