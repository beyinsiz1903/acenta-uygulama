from __future__ import annotations

import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


_mongo_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def _mongo_url() -> str:
    return os.environ["MONGO_URL"]


def _db_name() -> str:
    return os.environ.get("DB_NAME", "test_database")


async def connect_mongo() -> None:
    global _mongo_client, _db

    if _mongo_client is not None and _db is not None:
        return

    _mongo_client = AsyncIOMotorClient(_mongo_url())
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
