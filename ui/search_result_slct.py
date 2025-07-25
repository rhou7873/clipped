# Clipped modules
from models.clip import Clip

# Pycord modules
from discord import Interaction, SelectOption
from discord.ui import Select

# Other modules
from typing import List


class SearchResultSelect(Select):
    def __init__(self, clips: List[Clip]):
        self.clips = clips

        options = [
            SelectOption(
                label=clip['timestamp_str'],
                description=clip['summary'][:100],  # short preview
                value=str(i)
            )
            for i, clip in enumerate(clips)
        ]

        super().__init__(
            placeholder="Select a clip to fetch",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: Interaction):
        index = int(self.values[0])
        selected_clip = self.clips[index]

        await interaction.response.send_message(
            f"**Timestamp**: {selected_clip['timestamp_str']}\n"
            f"**Summary**: {selected_clip['summary']}\n"
            f"**Clip**: {selected_clip['bucket_location']}",
        )
