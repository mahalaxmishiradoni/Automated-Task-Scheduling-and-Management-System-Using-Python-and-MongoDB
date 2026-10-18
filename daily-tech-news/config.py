import os


DATABASE_NAME = "Daily_Tech_News"
DEFAULT_MONGODB_URI = "mongodb://localhost:27017"


def load_settings():
    """Load the MongoDB connection settings."""
    return {
        "mongodb_uri": os.getenv("MONGODB_URI", DEFAULT_MONGODB_URI),
        "database_name": DATABASE_NAME,
    }
