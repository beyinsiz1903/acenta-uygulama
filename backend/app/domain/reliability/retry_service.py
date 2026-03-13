"""P3 — Retry Strategy & Dead Letter Queue Service.

Exponential backoff with jitter for supplier calls, payments, voucher generation.
Dead-letter queue for failed operations.
"""
from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from app.domain.reliability.models import DLQ_CATEGORIES, RETRY_CATEGORIES

logger = logging.getLogger("reliability.retry")


def compute_retry_delay(category: str, attempt: int) -> float:
    """Compute delay in seconds using exponential backoff with jitter."""
    cfg = RETRY_CATEGORIES.get(category, RETRY_CATEGORIES["supplier_call"])
    base_ms = cfg["base_delay_ms"]
    max_ms = cfg["max_delay_ms"]
    multiplier = cfg["backoff_multiplier"]

    delay_ms = min(base_ms * (multiplier ** (attempt - 1)), max_ms)
    if cfg.get("jitter"):
        delay_ms = delay_ms * (0.5 + random.random() * 0.5)
    return delay_ms / 1000.0


def should_retry(category: str, attempt: int, error_code: str) -> bool:
    """Check if the operation should be retried."""
    cfg = RETRY_CATEGORIES.get(category, RETRY_CATEGORIES["supplier_call"])
    if attempt >= cfg["max_retries"]:
        return False
    return error_code in cfg.get("retryable_errors", [])


async def get_retry_config(db, org_id: str) -> dict[str, Any]:
    """Get retry configuration."""
    doc = await db.rel_retry_config.find_one({"organization_id": org_id}, {"_id": 0})
    if not doc:
        return {
            "organization_id": org_id,
            "categories": RETRY_CATEGORIES,
            "dlq_categories": DLQ_CATEGORIES,
        }
    return doc


async def enqueue_dlq(
    db, org_id: str, category: str, operation: str, payload: dict,
    error: str, attempts: int, supplier_code: str = ""
) -> dict[str, Any]:
    """Add a failed operation to the dead-letter queue."""
    now = datetime.now(timezone.utc).isoformat()
    entry_id = str(uuid.uuid4())
    doc = {
        "entry_id": entry_id,
        "organization_id": org_id,
        "category": category,
        "operation": operation,
        "supplier_code": supplier_code,
        "payload": payload,
        "error": error,
        "attempts": attempts,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    await db.rel_dead_letter_queue.insert_one(doc)
    logger.warning("DLQ enqueued: %s/%s for %s (attempts=%d)", category, operation, supplier_code, attempts)
    return {"entry_id": entry_id, "status": "enqueued"}


async def list_dlq(
    db, org_id: str, category: str | None = None,
    status: str = "pending", skip: int = 0, limit: int = 50
) -> dict[str, Any]:
    """List dead-letter queue entries."""
    match: dict[str, Any] = {"organization_id": org_id}
    if category:
        match["category"] = category
    if status:
        match["status"] = status
    total = await db.rel_dead_letter_queue.count_documents(match)
    cursor = db.rel_dead_letter_queue.find(match, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(limit)
    return {"total": total, "items": items, "skip": skip, "limit": limit}


async def retry_dlq_entry(db, org_id: str, entry_id: str) -> dict[str, Any]:
    """Mark a DLQ entry for retry."""
    now = datetime.now(timezone.utc).isoformat()
    result = await db.rel_dead_letter_queue.update_one(
        {"organization_id": org_id, "entry_id": entry_id, "status": "pending"},
        {"$set": {"status": "retrying", "updated_at": now}, "$inc": {"attempts": 1}},
    )
    if result.modified_count == 0:
        return {"status": "not_found_or_already_retrying"}
    return {"status": "retrying", "entry_id": entry_id}


async def discard_dlq_entry(db, org_id: str, entry_id: str, reason: str = "") -> dict[str, Any]:
    """Discard a DLQ entry (mark as dead)."""
    now = datetime.now(timezone.utc).isoformat()
    result = await db.rel_dead_letter_queue.update_one(
        {"organization_id": org_id, "entry_id": entry_id},
        {"$set": {"status": "discarded", "discard_reason": reason, "updated_at": now}},
    )
    if result.modified_count == 0:
        return {"status": "not_found"}
    return {"status": "discarded", "entry_id": entry_id}


async def get_dlq_stats(db, org_id: str) -> dict[str, Any]:
    """Aggregate DLQ statistics."""
    pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {
            "_id": {"category": "$category", "status": "$status"},
            "count": {"$sum": 1},
        }},
    ]
    results = await db.rel_dead_letter_queue.aggregate(pipeline).to_list(100)
    stats: dict[str, dict] = {}
    for r in results:
        cat = r["_id"]["category"]
        status = r["_id"]["status"]
        if cat not in stats:
            stats[cat] = {"category": cat, "pending": 0, "retrying": 0, "discarded": 0, "completed": 0, "total": 0}
        stats[cat][status] = r["count"]
        stats[cat]["total"] += r["count"]
    return {"categories": list(stats.values())}
