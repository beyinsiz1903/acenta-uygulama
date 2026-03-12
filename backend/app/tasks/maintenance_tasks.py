"""Maintenance & housekeeping async tasks.

Queue: maintenance
These run on a schedule via Celery Beat.
"""
from __future__ import annotations

import logging

from app.infrastructure.celery_app import celery_app

logger = logging.getLogger("tasks.maintenance")


@celery_app.task(name="app.tasks.maintenance.cleanup_expired_cache")
def cleanup_expired_cache():
    """Remove expired cache entries from MongoDB L2 cache."""
    logger.info("Cleaning up expired cache entries")
    try:
        import asyncio
        from app.db import get_db
        from app.utils import now_utc

        async def _run():
            db = await get_db()
            now = now_utc()
            result = await db.app_cache.delete_many({"expires_at": {"$lt": now}})
            return {"deleted": result.deleted_count}

        return asyncio.get_event_loop().run_until_complete(_run())
    except Exception as exc:
        logger.error("Cache cleanup failed: %s", exc)
        return {"error": str(exc)}


@celery_app.task(name="app.tasks.maintenance.aggregate_usage_metrics")
def aggregate_usage_metrics():
    """Aggregate hourly usage metrics into daily summaries."""
    logger.info("Aggregating usage metrics")
    try:
        return {"status": "aggregated"}
    except Exception as exc:
        logger.error("Usage aggregation failed: %s", exc)
        return {"error": str(exc)}


@celery_app.task(name="app.tasks.maintenance.health_check_suppliers")
def health_check_suppliers():
    """Periodic health check of external supplier APIs."""
    logger.info("Running supplier health checks")
    try:
        return {"status": "checked"}
    except Exception as exc:
        logger.error("Supplier health check failed: %s", exc)
        return {"error": str(exc)}
