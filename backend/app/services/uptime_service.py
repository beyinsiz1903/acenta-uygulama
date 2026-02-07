"""O5 - Uptime Tracking Service.

Tracks system uptime by periodic health checks.
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from app.db import get_db
from app.utils import now_utc


async def check_and_log_uptime() -> dict[str, Any]:
    """Perform internal health check and log status."""
    db = await get_db()
    status = "up"

    try:
        # Check MongoDB
        await db.command("ping")
    except Exception:
        status = "down"

    doc = {
        "_id": str(uuid.uuid4()),
        "timestamp": now_utc(),
        "status": status,
    }
    await db.system_uptime.insert_one(doc)
    return doc


async def get_uptime_stats(days: int = 30) -> dict[str, Any]:
    """Calculate uptime statistics for the given number of days."""
    db = await get_db()
    cutoff = now_utc() - timedelta(days=days)

    total = await db.system_uptime.count_documents(
        {"timestamp": {"$gte": cutoff}}
    )
    down = await db.system_uptime.count_documents(
        {"timestamp": {"$gte": cutoff}, "status": "down"}
    )
    up = total - down

    uptime_percent = round((up / total) * 100, 4) if total > 0 else 100.0

    return {
        "uptime_percent": uptime_percent,
        "total_minutes": total,
        "downtime_minutes": down,
        "up_minutes": up,
        "period_days": days,
        "computed_at": now_utc().isoformat(),
    }
