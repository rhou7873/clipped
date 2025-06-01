import discord
import pymongo as mg
from typing import List, Dict
from bw_secrets import (MONGO_CONN_STRING, MONGO_DB_NAME,
                        CLIPPED_SESSIONS_COLLECTION, USERS_COLLECTION)

db = mg.MongoClient(MONGO_CONN_STRING)[MONGO_DB_NAME]


#########################################################################
######################## HIGHER-LEVEL OPERATIONS ########################
#########################################################################


def get_opted_in_statuses(bot: discord.Bot,
                          members: List[discord.Member]) -> Dict[discord.Member, bool]:
    statuses = {}

    for member in members:
        if member.id == bot.user.id:  # skip the Clipped bot
            continue

        # Fetch users' `opt_in` status from DB
        query_results = _read_document(collection_name=USERS_COLLECTION,
                                      filter={"_id": member.id},
                                      projection={"_id": 0, "opted_in": 1})

        # If user doesn't exist in DB, create new user document
        opted_in = True  # default to opt-in status
        if len(query_results) == 0:
            set_opted_in_status(member, opted_in)
        else:
            opted_in = query_results[0]["opted_in"]

        statuses[member] = opted_in

    return statuses


def set_opted_in_status(member: discord.Member, opted_in: bool) -> None:
    guild = member.guild
    unique_id = {"user_id": member.id, "guild_id": guild.id}

    # Check if user's opt-in preference for this server already exists
    results = _read_document(collection_name=USERS_COLLECTION,
                            filter={"_id": unique_id},
                            projection={"_id": 1})

    if len(results) < 1:  # create new document if not
        _create_document(collection_name=USERS_COLLECTION,
                        obj={
                            "_id": unique_id,
                            "user_name": member.name,
                            "guild_name": guild.name,
                            "opted_in": opted_in
                        })
    else:  # otherwise, update existing document
        _update_document(collection_name=USERS_COLLECTION,
                        filter={"_id": unique_id},
                        update_query={"$set": {"opted_in": opted_in}})


def update_clipped_sessions(guild: discord.Guild,
                            voice_channel: discord.VoiceChannel,
                            bot_joined_vc: bool,
                            bot_left_vc: bool) -> None:
    if voice_channel is None:
        raise Exception("Voice channel should not be None")

    if bot_joined_vc:
        # Register voice session in DB
        _create_document(collection_name=CLIPPED_SESSIONS_COLLECTION,
                        obj={"_id": guild.id,
                             "guild_name": guild.name,
                             "channel_id": voice_channel.id,
                             "channel_name": voice_channel.name})
    elif bot_left_vc:
        # Remove voice session from DB
        _delete_document(collection_name=CLIPPED_SESSIONS_COLLECTION,
                        id=guild.id)


#########################################################################
####################### LOW-LEVEL CRUD OPERATIONS #######################
#########################################################################


def _create_document(collection_name: str, obj) -> str:
    if collection_name not in db.list_collection_names():
        raise Exception(f"Collection name '{collection_name}' doesn't exist")

    collection = db[collection_name]
    inserted_id = collection.insert_one(obj).inserted_id

    return inserted_id


def _read_document(collection_name: str, filter, projection=None) -> List:
    if collection_name not in db.list_collection_names():
        raise Exception(f"Collection name '{collection_name}' doesn't exist")

    collection = db[collection_name]
    results = [doc for doc in collection.find(filter, projection)]

    return results


def _update_document(collection_name: str, filter, update_query) -> None:
    if collection_name not in db.list_collection_names():
        raise Exception(f"Collection name '{collection_name}' doesn't exist")

    collection = db[collection_name]
    result = collection.update_one(filter, update_query)

    if result.matched_count < 1:
        raise Exception(
            f"No documents were updated (collection={collection_name}, filter={filter})")


def _delete_document(collection_name: str, id: str) -> None:
    if collection_name not in db.list_collection_names():
        raise Exception(f"Collection name '{collection_name}' doesn't exist")

    collection = db[collection_name]
    delete_count = collection.delete_one({"_id": id}).deleted_count

    if delete_count < 1:
        raise Exception(
            f"No documents deleted (collection={collection_name}, id={id})")
