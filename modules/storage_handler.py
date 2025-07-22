import io
import pydub
from typing import Dict

class StorageHandler:
    @staticmethod
    def store_clip_audio(clip: io.BytesIO):
        pass

    @staticmethod
    def store_clip_metadata(clip_by_member: Dict[int, pydub.AudioSegment]):
        pass

