import asyncio
from bw_secrets import CLIPPED_SESSIONS_COLLECTION
import discord
from modules.data_processor import DataProcessor
from modules.data_streamer import DataStreamer
import modules.database as db


class ClippedSession:
    def __init__(self,
                 voice: discord.VoiceClient,
                 started_by: discord.Member,
                 clip_size: int = 30,
                 chunk_size: int = 1):
        self.guild_id = voice.guild.id
        self.guild_name = voice.guild.name
        self.channel_id = voice.channel.id
        self.channel_name = voice.channel.name
        self.started_by = started_by

        self.streamer = DataStreamer(voice,
                                     clip_size=clip_size,
                                     chunk_size=chunk_size)
        asyncio.create_task(self.streamer.start(),
                            name="ClippedSession > stream task")
        self.processor = DataProcessor(voice, self.streamer)

        self.last_ui_message: discord.InteractionMessage = None
        self.voice = voice

        # Fields of database document
        self.db_fields = {"_id": self.guild_id,
                          "guild_name": self.guild_name,
                          "channel_id": self.channel_id,
                          "channel_name": self.channel_name,
                          "started_by": {
                              "user_id": self.started_by.id,
                              "user_name": self.started_by.name
                          }}
        db.create_document(collection_name=CLIPPED_SESSIONS_COLLECTION,
                           obj=self.db_fields)

    def stop_session(self):
        self.streamer.stop()
        db.delete_document(collection_name=CLIPPED_SESSIONS_COLLECTION,
                           id=self.guild_id)
