from discord.ui import View
from typing import Callable


class SearchResultView(View):
    def __init__(self, clip_that_func: Callable, leave_vc_func: Callable):
        super().__init__()
        self.clip_that_func = clip_that_func
        self.leave_vc_func = leave_vc_func
