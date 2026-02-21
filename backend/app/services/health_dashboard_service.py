"""Health Check Dashboard Service.

Provides comprehensive health checks:
- Service status
- Database connection
- Worker status
- Cache status
- System metrics
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import get_db

logger = logging.getLogger("health_dashboard")

_start_time = time.time()


async def get_health_dashboard() -> dict[str, Any]:
    """Generate comprehensive health dashboard."""
    now = datetime.now(timezone.utc)
    uptime_seconds = time.time() - _start_time

    dashboard: dict[str, Any] = {
        "status": "healthy",
        "timestamp": str(now),
        "uptime_seconds": round(uptime_seconds, 1),
        "version": os.environ.get("APP_VERSION", "1.0.0"),
        "checks": {},
    }

    # 1. MongoDB connection
    try:
        db = await get_db()
        await db.command("ping")
        dashboard["checks"]["mongodb"] = {
            "status": "healthy",
            "latency_ms": 0,
        }
        # Get DB stats
        try:
            stats = await db.command("dbStats")
            dashboard["checks"]["mongodb"]["collections"] = stats.get("collections", 0)
            dashboard["checks"]["mongodb"]["data_size_mb"] = round(
                stats.get("dataSize", 0) / (1024 * 1024), 2
            )
            dashboard["checks"]["mongodb"]["index_size_mb"] = round(
                stats.get("indexSize", 0) / (1024 * 1024), 2
            )
        except Exception:
            pass
    except Exception as e:
        dashboard["checks"]["mongodb"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        dashboard["status"] = "degraded"

    # 2. Workers / Background Jobs
    try:
        db = await get_db()
        recent_jobs = await db.jobs.count_documents({
            "status": {"$in": ["pending", "running"]},
        })
        failed_jobs = await db.jobs.count_documents({
            "status": "failed",
            "updated_at": {"$gte": now - timedelta(hours=1)},
        })
        dashboard["checks"]["workers"] = {
            "status": "healthy" if failed_jobs < 5 else "degraded",
            "pending_jobs": recent_jobs,
            "failed_jobs_1h": failed_jobs,
        }
    except Exception as e:
        dashboard["checks"]["workers"] = {
            "status": "unknown",
            "error": str(e),
        }

    # 3. Cache status
    try:
        db = await get_db()
        cache_total = await db.cache_entries.count_documents({})
        cache_active = await db.cache_entries.count_documents(
            {"expires_at": {"$gt": now}}
        )
        dashboard["checks"]["cache"] = {
            "status": "healthy",
            "type": "mongodb_ttl",
            "total_entries": cache_total,
            "active_entries": cache_active,
        }
    except Exception:
        dashboard["checks"]["cache"] = {
            "status": "healthy",
            "type": "mongodb_ttl",
            "total_entries": 0,
        }

    # 4. Active sessions
    try:
        db = await get_db()
        active_sessions = await db.refresh_tokens.count_documents({
            "is_revoked": False,
            "expires_at": {"$gt": now},
        })
        dashboard["checks"]["sessions"] = {
            "status": "healthy",
            "active_sessions": active_sessions,
        }
    except Exception:
        dashboard["checks"]["sessions"] = {"status": "unknown"}

    # 5. Distributed locks
    try:
        db = await get_db()
        active_locks = await db.distributed_locks.count_documents(
            {"expires_at": {"$gt": now}}
        )
        dashboard["checks"]["locks"] = {
            "status": "healthy",
            "active_locks": active_locks,
        }
    except Exception:
        dashboard["checks"]["locks"] = {"status": "unknown"}

    # 6. Rate limiting
    try:
        db = await get_db()
        recent_rate_limits = await db.rate_limits.count_documents({
            "created_at": {"$gte": now - timedelta(minutes=5)},
        })
        dashboard["checks"]["rate_limiting"] = {
            "status": "healthy",
            "requests_5m": recent_rate_limits,
        }
    except Exception:
        dashboard["checks"]["rate_limiting"] = {"status": "unknown"}

    # 7. Booking stats (last 24h)
    try:
        db = await get_db()
        day_ago = now - timedelta(hours=24)
        new_bookings = await db.bookings.count_documents({
            "created_at": {"$gte": day_ago},
        })
        confirmed_bookings = await db.bookings.count_documents({
            "confirmed_at": {"$gte": day_ago},
        })
        cancelled_bookings = await db.bookings.count_documents({
            "status": "cancelled",
            "updated_at": {"$gte": day_ago},
        })
        dashboard["checks"]["bookings_24h"] = {
            "new": new_bookings,
            "confirmed": confirmed_bookings,
            "cancelled": cancelled_bookings,
        }
    except Exception:
        pass

    # Overall status
    unhealthy = sum(
        1 for c in dashboard["checks"].values()
        if isinstance(c, dict) and c.get("status") == "unhealthy"
    )
    degraded = sum(
        1 for c in dashboard["checks"].values()
        if isinstance(c, dict) and c.get("status") == "degraded"
    )
    if unhealthy > 0:
        dashboard["status"] = "unhealthy"
    elif degraded > 0:
        dashboard["status"] = "degraded"

    return dashboard
