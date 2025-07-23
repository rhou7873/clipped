from bw_secrets import CLIPS_METADATA_COLLECTION
import discord
from datetime import datetime
import modules.database as db
import pydub
import pymongo
from typing import Dict


class Clip:
    def __init__(self,
                 guild: discord.Guild,
                 timestamp: datetime,
                 clip_by_member: Dict[int, pydub.AudioSegment],
                 bucket_location: str):
        self.db_client = pymongo.MongoClient()
        self.guild = guild
        self.timestamp = timestamp
        self.clip_by_member = clip_by_member
        self.bucket_location = bucket_location

        self.transcription = None
        self.transcription_summary = None
        self.summary_embedding = None

    def create_clip_metadata_in_db(self):
        self.transcription = self._generate_transcription()
        self.transcription_summary = self._generate_transcription_summary()
        self.summary_embedding = self._generate_summary_embedding()

        # Fields of database document
        self.fields = {
            "_id": {"guild_id": self.guild.id, "timestamp": self.timestamp},
            "transcription": self.transcription,
            "summary": self.transcription_summary,
            "summary_embedding": self.summary_embedding,
            "bucket_location": self.bucket_location
        }

        db.create_document(collection_name=CLIPS_METADATA_COLLECTION,
                           obj=self.fields)

    def _generate_transcription(self) -> str:
        pass

    def _generate_transcription_summary(self) -> str:
        if self.transcription is None:
            raise Exception("Transcription hasn't been generated yet. "
                            "Call _generate_transcription() first")
        
    def _generate_summary_embedding(self):
        if self.transcription_summary is None:
            raise Exception("Transcription summary hasn't been generated yet. "
                            "Call _generate_transcription_summary() first")
