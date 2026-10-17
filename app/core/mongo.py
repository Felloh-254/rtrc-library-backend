"""MongoDB client setup and connection lifecycle helpers."""

from typing import Any

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.core.config import settings


MongoDatabase = Database[dict[str, Any]]
MongoConnection = tuple[
    MongoClient[dict[str, Any]] | None,
    MongoDatabase | None,
]


def connect_mongodb() -> MongoConnection:
    """Create and verify the configured MongoDB connection, if enabled."""
    if not settings.mongodb_configured:
        return None, None

    database_name = settings.MONGO_DB
    if database_name is None:
        raise ValueError("MONGO_DB is required when MongoDB is configured.")

    options = {
        "serverSelectionTimeoutMS": settings.MONGO_SERVER_SELECTION_TIMEOUT_MS,
    }
    if settings.MONGO_URI is not None:
        client: MongoClient[dict[str, Any]] = MongoClient(
            settings.MONGO_URI,
            **options,
        )
    else:
        cluster = settings.MONGO_CLUSTER
        if cluster is None:
            raise ValueError("MONGO_CLUSTER or MONGO_URI is required for MongoDB.")
        client = MongoClient(
            cluster,
            username=settings.MONGO_USER,
            password=settings.MONGO_PASS,
            **options,
        )

    try:
        database = client[database_name]
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        raise

    return client, database
