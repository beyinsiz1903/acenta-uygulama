"""MongoDB-based distributed lock for multi-instance workers.

Provides distributed locking using MongoDB atomic operations.
Replaces Redis-based distributed locks.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.db import get_db

logger = logging.getLogger("distributed_lock")

COLLECTION = "distributed_locks"
DEFAULT_LOCK_TTL = 300  # 5 minutes


async def acquire_lock(
    lock_key: str,
    owner_id: Optional[str] = None,
    ttl_seconds: int = DEFAULT_LOCK_TTL,
) -> Optional[str]:
    """Try to acquire a distributed lock.

    Returns lock_id if acquired, None if lock is already held.
    Uses MongoDB's upsert with unique key for atomic acquisition.
    """
    db = await get_db()
    now = datetime.now(timezone.utc)
    lock_id = owner_id or str(uuid.uuid4())
    expires_at = now + timedelta(seconds=ttl_seconds)

    try:
        # First, clean up expired locks
        await db[COLLECTION].delete_many({
            "lock_key": lock_key,
            "expires_at": {"$lt": now},
        })

        # Try to acquire
        result = await db[COLLECTION].update_one(
            {
                "lock_key": lock_key,
                "$or": [
                    {"expires_at": {"$lt": now}},  # Expired
                    {"lock_key": {"$exists": False}},  # Doesn't exist (won't match but needed for upsert)
                ],
            },
            {
                "$set": {
                    "lock_key": lock_key,
                    "lock_id": lock_id,
                    "acquired_at": now,
                    "expires_at": expires_at,
                },
            },
            upsert=True,
        )

        if result.upserted_id or result.modified_count:
            logger.debug("Lock acquired: key=%s owner=%s", lock_key, lock_id)
            return lock_id
    except Exception as e:
        # DuplicateKeyError means lock is already held
        if "duplicate key" in str(e).lower() or "E11000" in str(e):
            logger.debug("Lock already held: key=%s", lock_key)
            return None
        logger.error("Lock acquisition error: %s", e)

    return None


async def release_lock(lock_key: str, lock_id: str) -> bool:
    """Release a distributed lock."""
    db = await get_db()
    result = await db[COLLECTION].delete_one({
        "lock_key": lock_key,
        "lock_id": lock_id,
    })
    released = result.deleted_count > 0
    if released:
        logger.debug("Lock released: key=%s", lock_key)
    return released


async def extend_lock(lock_key: str, lock_id: str, ttl_seconds: int = DEFAULT_LOCK_TTL) -> bool:
    """Extend the TTL of a held lock."""
    db = await get_db()
    now = datetime.now(timezone.utc)
    result = await db[COLLECTION].update_one(
        {"lock_key": lock_key, "lock_id": lock_id},
        {"$set": {"expires_at": now + timedelta(seconds=ttl_seconds)}},
    )
    return result.modified_count > 0


async def is_locked(lock_key: str) -> bool:
    """Check if a lock is currently held."""
    db = await get_db()
    now = datetime.now(timezone.utc)
    doc = await db[COLLECTION].find_one({
        "lock_key": lock_key,
        "expires_at": {"$gt": now},
    })
    return doc is not None


async def list_active_locks() -> list[dict]:
    """List all currently held locks."""
    db = await get_db()
    now = datetime.now(timezone.utc)
    docs = await db[COLLECTION].find(
        {"expires_at": {"$gt": now}}
    ).to_list(200)
    return [
        {
            "lock_key": d.get("lock_key"),
            "lock_id": d.get("lock_id"),
            "acquired_at": d.get("acquired_at"),
            "expires_at": d.get("expires_at"),
        }
        for d in docs
    ]


async def ensure_lock_indexes() -> None:
    """Create indexes for distributed locks."""
    db = await get_db()
    try:
        await db[COLLECTION].create_index(
            "lock_key", unique=True, name="idx_lock_key"
        )
        await db[COLLECTION].create_index(
            "expires_at", expireAfterSeconds=0, name="ttl_locks"
        )
    except Exception as e:
        logger.warning("Lock index creation warning: %s", e)
