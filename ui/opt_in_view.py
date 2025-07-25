from discord import Member
from discord.ui import View
from ui.opt_in_btn import OptInButton
from ui.opt_out_btn import OptOutButton
from typing import Callable


class OptInView(View):
    def __init__(self,
                 member: Member,
                 opt_in_handler: Callable,
                 opt_out_handler: Callable,
                 show_opt_in: bool = False,
                 show_opt_out: bool = False):
        super().__init__()

        if show_opt_in:
            self.add_item(OptInButton(member, opt_in_handler))
        if show_opt_out:
            self.add_item(OptOutButton(member, opt_out_handler))
