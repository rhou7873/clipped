from discord import Guild, Member, User
import pymongo as mg
from typing import List, Dict
from bw_secrets import (MONGO_CONN_STRING, MONGO_DB_NAME,
                        CLIPPED_SESSIONS_COLLECTION, USERS_COLLECTION,
                        BOT_USER_ID)

db = mg.MongoClient(MONGO_CONN_STRING)[MONGO_DB_NAME]


#########################################################################
######################## HIGHER-LEVEL OPERATIONS ########################
#########################################################################


def clear_all_clipped_sessions() -> None:
    delete_all_documents(collection_name=CLIPPED_SESSIONS_COLLECTION)


def member_exists(guild_id: int, user_id: int) -> bool:
    filter = {"_id": {"user_id": user_id, "guild_id": guild_id}}
    projection = {"_id": 1}

    results = read_document(collection_name=USERS_COLLECTION,
                            filter=filter,
                            projection=projection)

    return len(results) >= 1


def get_opted_in_members(members: List[Member]) -> List[Member]:
    statuses = get_opted_in_statuses(members)
    opted_in = [member for member, opted_in in statuses.items() if opted_in]
    return opted_in


def get_opted_in_statuses(members: List[Member]) -> Dict[Member, bool]:
    statuses = {}

    for member in members:
        if member.id == BOT_USER_ID:  # skip the Clipped bot
            continue

        # Fetch users' `opt_in` status from DB
        guild = member.guild
        filter = {"_id": {"user_id": member.id, "guild_id": guild.id}}
        projection = {"_id": 0, "opted_in": 1}
        query_results = read_document(collection_name=USERS_COLLECTION,
                                      filter=filter,
                                      projection=projection)

        # If user doesn't exist in DB, create new user document
        opted_in = True  # default to opt-in status
        if len(query_results) == 0:
            set_opted_in_status(guild=member.guild,
                                user=member,
                                opted_in=opted_in)
        else:
            opted_in = query_results[0]["opted_in"]

        statuses[member] = opted_in

    return statuses


def set_opted_in_status(guild: Guild,
                        user: User | Member,
                        opted_in: bool) -> None:
    unique_id = {"user_id": user.id, "guild_id": guild.id}

    # Check if user's opt-in preference for this server already exists
    results = read_document(collection_name=USERS_COLLECTION,
                            filter={"_id": unique_id},
                            projection={"_id": 1})

    if len(results) < 1:  # create new document if not
        create_document(collection_name=USERS_COLLECTION,
                        obj={
                            "_id": unique_id,
                            "user_name": user.name,
                            "guild_name": guild.name,
                            "opted_in": opted_in
                        })
    else:  # otherwise, update existing document
        update_document(collection_name=USERS_COLLECTION,
                        filter={"_id": unique_id},
                        update_query={"$set": {"opted_in": opted_in}})


#########################################################################
####################### LOW-LEVEL CRUD OPERATIONS #######################
#########################################################################


def create_document(collection_name: str, obj) -> str:
    if collection_name not in db.list_collection_names():
        raise Exception(f"Collection name '{collection_name}' doesn't exist")

    collection = db[collection_name]
    inserted_id = collection.insert_one(obj).inserted_id

    return inserted_id


def read_document(collection_name: str, filter, projection=None) -> List:
    if collection_name not in db.list_collection_names():
        raise Exception(f"Collection name '{collection_name}' doesn't exist")

    collection = db[collection_name]
    results = [doc for doc in collection.find(filter, projection)]

    return results


def update_document(collection_name: str, filter, update_query) -> None:
    if collection_name not in db.list_collection_names():
        raise Exception(f"Collection name '{collection_name}' doesn't exist")

    collection = db[collection_name]
    result = collection.update_one(filter, update_query)

    if result.matched_count < 1:
        raise Exception(
            f"No documents were updated (collection={collection_name}, "
            f"filter={filter})")


def delete_document(collection_name: str, id: str) -> None:
    if collection_name not in db.list_collection_names():
        raise Exception(f"Collection name '{collection_name}' doesn't exist")

    collection = db[collection_name]
    delete_count = collection.delete_one({"_id": id}).deleted_count

    if delete_count < 1:
        raise Exception(
            f"No documents deleted (collection={collection_name}, id={id})")


def delete_all_documents(collection_name: str) -> None:
    if collection_name not in db.list_collection_names():
        raise Exception(f"Collection name '{collection_name}' doesn't exist")

    collection = db[collection_name]
    result = collection.delete_many({})

    if not result.acknowledged:
        raise Exception(
            "There was a problem deleting all documents "
            f"(collection={collection_name})")
