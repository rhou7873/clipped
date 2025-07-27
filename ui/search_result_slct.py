# Clipped modules
from bw_secrets import GCS_BUCKET_NAME
from models.clip import Clip

# Pycord modules
from discord import File, Interaction, SelectOption
from discord.ui import Select

# Other modules
from google.cloud import storage
import io
from typing import List


class SearchResultSelect(Select):
    def __init__(self, clips: List[Clip]):
        self.clips = clips

        options = [
            SelectOption(
                label=clip.timestamp_str,
                # have to truncate
                description=f"{clip.transcription_summary[:97]}...",
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

        # Fetch the actual clip file from blob storage
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(selected_clip.blob_filename)

        clip_bytes = io.BytesIO()
        blob.download_to_file(clip_bytes)
        clip_bytes.seek(0)

        # Escapes the Discord markdown when there are underscores in the
        # transcription (primarily coming from Discord usernames)
        summary = selected_clip.transcription_summary.replace("_", "\\_")

        await interaction.response.send_message(
            f"**{selected_clip.timestamp_str}**\n"
            f"{summary}",
            file=File(clip_bytes, filename="clip.wav")
        )
