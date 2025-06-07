import discord
from datetime import datetime
import pymongo

class Clip:
    def __init__(self,
                 guild: discord.Guild,
                 timestamp: datetime,
                 transcription: str,
                 embedding: str,
                 summary: str,
                 file_location: str):
        # Fields of database document
        self.fields = {
            "_id": {"guild_id": guild.id, "timestamp": timestamp},
            "transcription": transcription,
            "embedding": embedding,
            "summary": summary,
            "file_location": file_location
        }
        self.db_client = pymongo.MongoClient()

    def write_to_db(self):
        pass
