# Clipped modules
from models.clip import Clip
from ui.search_result_slct import SearchResultSelect

# Pycord modules
from discord.ui import View

# Other modules
from typing import List


class SearchResultView(View):
    def __init__(self, clips: List[Clip]):
        super().__init__()
        self.add_item(SearchResultSelect(clips))
