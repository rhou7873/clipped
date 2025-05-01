import pymongo as mg
import os
from typing import List

CONN_STRING = os.getenv("MONGO_CONN_STRING")
DB_NAME = os.getenv("MONGO_DB_NAME")

if CONN_STRING is None or DB_NAME is None:
    raise Exception("Invalid DB environment variables "
                    f"(CONN_STRING={CONN_STRING}, DB_NAME={DB_NAME})")

db = mg.MongoClient(CONN_STRING)[DB_NAME]

####### LOW-LEVEL CRUD OPERATIONS #######

def create_document(collection_name: str, obj) -> str:
    if collection_name not in db.list_collection_names():
        raise Exception(f"Collection name '{collection_name}' doesn't exist")

    collection = db[collection_name]
    inserted_id = collection.insert_one(obj).inserted_id

    return inserted_id

def read_document(collection_name: str, filter, projection = None) -> List:
    if collection_name not in db.list_collection_names():
        raise Exception(f"Collection name '{collection_name}' doesn't exist")

    collection = db[collection_name]
    results = [doc for doc in collection.find(filter, projection)]

    return results

def update_document():
    pass

def delete_document(collection_name: str, id: str) -> None:
    if collection_name not in db.list_collection_names():
        raise Exception(f"Collection name '{collection_name}' doesn't exist")
    
    collection = db[collection_name]
    delete_count = collection.delete_one({"_id": id}).deleted_count

    if delete_count < 1:
        raise Exception(f"No documents deleted (collection={collection_name}, id={id})")
