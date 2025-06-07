import discord
import pymongo

class ClippedUser:
    def __init__(self,
                 member: discord.Member,
                 opted_in: bool):
        # Fields of database document
        self.fields = {
            "_id": {"user_id": member.id, "guild_id": member.guild.id},
            "user_name": member.name,
            "guild_name": member.guild.name,
            "opted_in": opted_in
        }
        self.db_client = pymongo.MongoClient()

    def write_to_db(self):
        pass
