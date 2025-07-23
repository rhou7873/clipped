# Clipped modules
from models.clip import Clip

# Pycord modules
import discord

# Other modules
from datetime import datetime
import io
from google.cloud import storage
import pydub
from typing import Dict
import uuid


class StorageHandler:
    @staticmethod
    def store_clip_audio(guild: discord.Guild, clip: io.BytesIO) -> str:
        """
        Stores clip audio bytes into blob storage, returning the 
        storage bucket location.
        """

        # Generate a unique filename
        clip_id = str(uuid.uuid4())
        file_name = f"{guild.name}-{guild.id}-{clip_id}.wav"

        # Rewind the BytesIO buffer
        clip.seek(0)

        # Initialize GCS client and bucket
        client = storage.Client()
        BUCKET_NAME = "clipped"
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_name)

        # Upload the audio clip
        blob.upload_from_file(clip, content_type="audio/wav")

        return f"gs://{BUCKET_NAME}/{file_name}"

    @staticmethod
    def store_clip_metadata(guild: discord.Guild,
                            bucket_location: str, 
                            clip_by_member: Dict[int, pydub.AudioSegment]):
        clip = Clip(guild=guild,
                    timestamp=datetime.now(),
                    transcription=None,
                    embedding=None,
                    summary=None,
                    bucket_location=bucket_location)
        clip.create_clip_metadata_in_db()
