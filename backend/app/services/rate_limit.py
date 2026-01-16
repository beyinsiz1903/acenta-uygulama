from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException

from app.db import get_db


def _bucket_minute(now: datetime) -> datetime:
    return now.replace(second=0, microsecond=0)


async def enforce_rate_limit(
    *,
    organization_id: str,
    key_id: str,
    ip: str,
    limit_per_minute: int = 60,
) -> None:
    """Enforce simple per-key+ip sliding-window rate limit.

    Uses a Mongo collection `rate_limit_buckets` to count requests per minute.
    """

    if not ip:
        # If IP missing, still count under a pseudo IP to avoid abuse.
        ip = "0.0.0.0"

    db = await get_db()
    now = datetime.now(timezone.utc)
    bucket = _bucket_minute(now)

    key: Dict[str, Any] = {
        "organization_id": organization_id,
        "key_id": key_id,
        "ip": ip,
        "bucket_minute": bucket,
    }

    await db.rate_limit_buckets.update_one(
        key,
        {
            "$inc": {"count": 1},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    doc = await db.rate_limit_buckets.find_one(key)
    if doc and int(doc.get("count", 0)) > limit_per_minute:
        raise HTTPException(status_code=429, detail="RATE_LIMITED")
