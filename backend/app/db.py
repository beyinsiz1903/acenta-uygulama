from __future__ import annotations

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import require_env


_mongo_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def _mongo_url() -> str:
    return require_env("MONGO_URL")


def _db_name() -> str:
    return require_env("DB_NAME")


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
