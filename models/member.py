import discord
import pymongo

from modules import database as db
from bw_secrets import BOT_USER_ID, MEMBERS_COLLECTION

from typing import Dict, List


class ClippedMember:
    def __init__(self,
                 member: discord.Member,
                 opted_in: bool):
        self.guild = member.guild

        # Fields of database document
        self.fields = {
            "_id": {"member_id": member.id, "guild_id": self.guild.id},
            "name": member.name,
            "guild_name": self.guild.name,
            "opted_in": opted_in
        }
        self.db_client = pymongo.MongoClient()

    def create_member_document_in_db(self):
        db.create_document(collection_name=MEMBERS_COLLECTION,
                           obj=self.fields)

    @staticmethod
    def member_exists(guild_id: int, member_id: int) -> bool:
        filter = {"_id": {"member_id": member_id, "guild_id": guild_id}}
        projection = {"_id": 1}

        results = db.read_document(collection_name=MEMBERS_COLLECTION,
                                   filter=filter,
                                   projection=projection)

        return len(results) >= 1

    @staticmethod
    def get_opted_in_members(members: List[discord.Member]) -> List[discord.Member]:
        statuses = ClippedMember.get_opted_in_statuses(members)
        opted_in = [member for member, opted_in in statuses.items()
                    if opted_in]
        return opted_in

    @staticmethod
    def get_opted_in_statuses(members: List[discord.Member]) -> Dict[discord.Member, bool]:
        statuses = {}

        for member in members:
            if member.id == BOT_USER_ID:  # skip the Clipped bot
                continue

            # Fetch members' `opt_in` status from DB
            guild = member.guild
            filter = {"_id": {"member_id": member.id, "guild_id": guild.id}}
            projection = {"_id": 0, "opted_in": 1}
            query_results = db.read_document(collection_name=MEMBERS_COLLECTION,
                                             filter=filter,
                                             projection=projection)

            # If member doesn't exist in DB, create new member document
            opted_in = True  # default to opt-in status
            if len(query_results) == 0:
                ClippedMember.set_opted_in_status(guild=member.guild,
                                                  member=member,
                                                  opted_in=opted_in)
            else:
                opted_in = query_results[0]["opted_in"]

            statuses[member] = opted_in

        return statuses

    @staticmethod
    def set_opted_in_status(guild: discord.Guild,
                            member: discord.Member,
                            opted_in: bool) -> None:
        unique_id = {"member_id": member.id, "guild_id": guild.id}

        # Check if members's opt-in preference for this server already exists
        results = db.read_document(collection_name=MEMBERS_COLLECTION,
                                   filter={"_id": unique_id},
                                   projection={"_id": 1})

        if len(results) < 1:  # create new document if not
            clipped_member = ClippedMember(member, opted_in)
            clipped_member.create_member_document_in_db()
        else:  # otherwise, update existing document
            db.update_document(collection_name=MEMBERS_COLLECTION,
                               filter={"_id": unique_id},
                               update_query={"$set": {"opted_in": opted_in}})
