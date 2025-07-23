from bw_secrets import CLIPS_METADATA_COLLECTION
import discord
from datetime import datetime
import modules.database as db
import pymongo

class Clip:
    def __init__(self,
                 guild: discord.Guild,
                 timestamp: datetime,
                 transcription: str,
                 embedding: str,
                 summary: str,
                 bucket_location: str):
        # Fields of database document
        self.fields = {
            "_id": {"guild_id": guild.id, "timestamp": timestamp},
            "transcription": transcription,
            "embedding": embedding,
            "summary": summary,
            "bucket_location": bucket_location
        }
        self.db_client = pymongo.MongoClient()

    def create_clip_metadata_in_db(self):
        db.create_document(collection_name=CLIPS_METADATA_COLLECTION,
                           obj=self.fields)
