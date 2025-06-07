from bw_secrets import CLIPPED_SESSIONS_COLLECTION
import discord
import modules.database as db
import pymongo


class ClippedSession:
    def __init__(self,
                 voice_channel: discord.VoiceChannel,
                 started_by: discord.Member):
        # Fields of database document
        self.fields = {"_id": voice_channel.guild.id,
                       "guild_name": voice_channel.guild.name,
                       "channel_id": voice_channel.id,
                       "channel_name": voice_channel.name,
                       "started_by": {
                           "user_id": started_by.id,
                           "user_name": started_by.name
                       }}
        self.db_client = pymongo.MongoClient()
        self.collection = CLIPPED_SESSIONS_COLLECTION

    def update_clipped_sessions(self,
                                bot_joined_vc: bool,
                                bot_left_vc: bool) -> None:
        if bot_joined_vc:
            # Register voice session in DB
            db.create_document(collection_name=self.collection,
                               obj=self.fields)
        elif bot_left_vc:
            # Remove voice session from DB
            db.delete_document(collection_name=self.collection,
                               id=self.fields["_id"])
