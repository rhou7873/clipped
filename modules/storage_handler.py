import io
from google.cloud import storage
import pydub
from typing import Dict
import uuid


class StorageHandler:
    @staticmethod
    def store_clip_audio(clip: io.BytesIO) -> str:
        """Stores clip audio bytes into blob storage, returning the object name"""

        # Generate a unique filename
        clip_id = str(uuid.uuid4())
        file_name = f"{clip_id}.wav"

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
    def store_clip_metadata(clip_by_member: Dict[int, pydub.AudioSegment]):
        pass
