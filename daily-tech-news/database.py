from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config import load_settings


def connect_to_database():
    """Connect to MongoDB and return the client and existing database."""
    settings = load_settings()
    client = None

    try:
        client = MongoClient(
            settings["mongodb_uri"],
            serverSelectionTimeoutMS=5000,
        )
        client.admin.command("ping")
    except PyMongoError as error:
        if client is not None:
            client.close()
        raise ConnectionError(
            "Could not connect to MongoDB. Check that MongoDB is running "
            "and that MONGODB_URI is correct. "
            f"MongoDB error: {error}"
        ) from error

    database = client[settings["database_name"]]
    return client, database


def get_collections(database):
    """Return the news and daily briefing collections."""
    return database["news"], database["daily_briefings"]
