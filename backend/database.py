"""
Database connection module using PyMongo
"""

from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure
from bson import ObjectId
from flask import current_app
import os


def get_db():
    """Get MongoDB database instance."""
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/object_tracker")
    client = MongoClient(mongo_uri)
    db_name = mongo_uri.split("/")[-1].split("?")[0]
    return client[db_name]


def get_collection(collection_name: str):
    """Get a specific MongoDB collection."""
    db = get_db()
    return db[collection_name]


def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict."""
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if key == "_id":
            result["id"] = str(value)
        elif isinstance(value, ObjectId):
            result[key] = str(value)
        else:
            result[key] = value
    return result


def serialize_list(docs: list) -> list:
    """Serialize a list of MongoDB documents."""
    return [serialize_doc(d) for d in docs]


def create_indexes():
    """Create MongoDB indexes for performance."""
    db = get_db()

    # Users
    db.users.create_index("email", unique=True)
    db.users.create_index("studentId", unique=True)

    # Items
    db.items.create_index([("status", 1)])
    db.items.create_index([("categoryType", 1)])
    db.items.create_index([("reporterId", 1)])
    db.items.create_index([("createdAt", DESCENDING)])
    db.items.create_index([
        ("name", "text"),
        ("description", "text"),
        ("color", "text"),
        ("brand", "text")
    ])

    # Claims
    db.claims.create_index([("itemId", 1)])
    db.claims.create_index([("claimantId", 1)])
    db.claims.create_index([("status", 1)])

    print("✅ MongoDB indexes created successfully")
