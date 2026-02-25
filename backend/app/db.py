from __future__ import annotations

import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


_mongo_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def _mongo_url() -> str:
    # Deployment-safe: fallback to localhost (will fail gracefully at runtime if Atlas not available)
    return os.environ.get("MONGO_URL", "mongodb://localhost:27017")


def _db_name() -> str:
    """Resolve database name.

    Priority:
      1. DB_NAME env var (explicit)
      2. Database name from MONGO_URL path (e.g. mongodb+srv://.../<dbname>?...)
      3. Fallback to 'app_database'
    """
    name = os.environ.get("DB_NAME", "")
    if name:
        return name

    # Try to extract DB name from MONGO_URL
    mongo_url = os.environ.get("MONGO_URL", "")
    if mongo_url:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(mongo_url)
            path_db = (parsed.path or "").lstrip("/").split("?")[0]
            if path_db:
                return path_db
        except Exception:
            pass

    import logging
    logging.getLogger("db").warning(
        "DB_NAME not set and could not extract from MONGO_URL — "
        "falling back to 'app_database'."
    )
    return "app_database"


async def connect_mongo() -> None:
    global _mongo_client, _db

    if _mongo_client is not None and _db is not None:
        return

    # DEPLOYMENT FIX: Short timeout to fail fast if MongoDB unreachable
    # Prevents hanging on startup in production
    _mongo_client = AsyncIOMotorClient(
        _mongo_url(),
        serverSelectionTimeoutMS=5000  # 5 second timeout instead of default 30s
    )
    _db = _mongo_client[_db_name()]


async def close_mongo() -> None:
    global _mongo_client, _db

    if _mongo_client is not None:
        _mongo_client.close()

    _mongo_client = None
    _db = None


async def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        await connect_mongo()
    assert _db is not None
    return _db
