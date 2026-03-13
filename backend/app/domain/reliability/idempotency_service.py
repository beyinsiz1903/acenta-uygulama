"""P4 — Identity & Idempotency Service.

Prevents duplicate bookings with idempotency keys and request deduplication.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.domain.reliability.models import IDEMPOTENCY_TTL_SECONDS, IDEMPOTENT_OPERATIONS

logger = logging.getLogger("reliability.idempotency")


async def check_idempotency(
    db, org_id: str, idempotency_key: str, operation: str
) -> dict[str, Any] | None:
    """Check if an operation with this key was already processed.

    Returns the cached result if found, None if first time.
    """
    doc = await db.rel_idempotency_store.find_one(
        {"organization_id": org_id, "idempotency_key": idempotency_key, "operation": operation},
        {"_id": 0},
    )
    if doc and doc.get("status") == "completed":
        return doc.get("result")
    return None


async def store_idempotency(
    db, org_id: str, idempotency_key: str, operation: str, result: dict
) -> None:
    """Store the result of an idempotent operation."""
    now = datetime.now(timezone.utc).isoformat()
    await db.rel_idempotency_store.update_one(
        {"organization_id": org_id, "idempotency_key": idempotency_key, "operation": operation},
        {
            "$set": {
                "result": result,
                "status": "completed",
                "completed_at": now,
                "updated_at": now,
            },
            "$setOnInsert": {
                "organization_id": org_id,
                "idempotency_key": idempotency_key,
                "operation": operation,
                "created_at": now,
            },
        },
        upsert=True,
    )


async def lock_idempotency(
    db, org_id: str, idempotency_key: str, operation: str
) -> bool:
    """Try to acquire an idempotency lock (prevent concurrent duplicate execution)."""
    now = datetime.now(timezone.utc).isoformat()
    result = await db.rel_idempotency_store.update_one(
        {
            "organization_id": org_id,
            "idempotency_key": idempotency_key,
            "operation": operation,
            "status": {"$ne": "completed"},
        },
        {
            "$setOnInsert": {
                "organization_id": org_id,
                "idempotency_key": idempotency_key,
                "operation": operation,
                "status": "processing",
                "created_at": now,
            },
            "$set": {"updated_at": now},
        },
        upsert=True,
    )
    return result.upserted_id is not None or result.modified_count > 0


def generate_idempotency_key(*parts: str) -> str:
    """Generate a deterministic idempotency key from input parts."""
    content = "|".join(str(p) for p in parts)
    return hashlib.sha256(content.encode()).hexdigest()[:32]


async def deduplicate_request(
    db, org_id: str, request_hash: str, ttl_seconds: int = 5
) -> bool:
    """Check if this exact request was made in the last N seconds (dedup)."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(seconds=ttl_seconds)).isoformat()

    existing = await db.rel_request_dedup.find_one({
        "organization_id": org_id,
        "request_hash": request_hash,
        "created_at": {"$gte": cutoff},
    })
    if existing:
        return True  # duplicate

    await db.rel_request_dedup.insert_one({
        "organization_id": org_id,
        "request_hash": request_hash,
        "created_at": now.isoformat(),
    })
    return False


async def get_idempotency_stats(db, org_id: str) -> dict[str, Any]:
    """Get idempotency store statistics."""
    pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {
            "_id": {"operation": "$operation", "status": "$status"},
            "count": {"$sum": 1},
        }},
    ]
    results = await db.rel_idempotency_store.aggregate(pipeline).to_list(100)
    stats: dict[str, dict] = {}
    for r in results:
        op = r["_id"]["operation"]
        status = r["_id"]["status"]
        if op not in stats:
            stats[op] = {"operation": op, "completed": 0, "processing": 0, "total": 0}
        stats[op][status] = r["count"]
        stats[op]["total"] += r["count"]
    return {
        "operations": list(stats.values()),
        "supported_operations": IDEMPOTENT_OPERATIONS,
        "ttl_seconds": IDEMPOTENCY_TTL_SECONDS,
    }
