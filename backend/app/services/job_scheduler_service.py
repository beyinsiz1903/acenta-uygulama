"""Platform Job Scheduler Service.

Manages scheduled background jobs using APScheduler:
  - Hourly booking status sync
  - Daily supplier reconciliation
  - Supplier health check (every 15 min)
  - Analytics aggregation (every 30 min)
  - Revenue reconciliation (daily)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("job_scheduler")

# --- Job execution history (in-memory, last 100 runs per job) ---
_job_history: dict[str, list[dict]] = {}
_MAX_HISTORY = 50


def _record_run(job_name: str, status: str, details: str = "", duration_ms: float = 0):
    if job_name not in _job_history:
        _job_history[job_name] = []
    _job_history[job_name].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "details": details,
        "duration_ms": round(duration_ms, 1),
    })
    if len(_job_history[job_name]) > _MAX_HISTORY:
        _job_history[job_name] = _job_history[job_name][-_MAX_HISTORY:]


def get_job_history() -> dict[str, Any]:
    result = {}
    for name, runs in _job_history.items():
        last = runs[-1] if runs else None
        result[name] = {
            "total_runs": len(runs),
            "last_run": last,
            "recent_runs": runs[-5:],
        }
    return result


# ==========================================================================
# Job Implementations
# ==========================================================================

async def job_booking_status_sync():
    """Hourly: Sync booking statuses with supplier systems."""
    import time
    start = time.monotonic()
    try:
        from app.db import get_db
        db = await get_db()

        # Find bookings in last 48h that are confirmed but not finalized
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        bookings = await db["unified_bookings"].find(
            {"status": "confirmed", "created_at": {"$gte": cutoff}},
            {"_id": 0, "internal_booking_id": 1, "supplier_code": 1, "supplier_booking_id": 1},
        ).to_list(500)

        synced = 0
        for b in bookings:
            try:
                from app.suppliers.booking_reconciliation import update_supplier_status
                await update_supplier_status(
                    db, b["internal_booking_id"], "confirmed"
                )
                synced += 1
            except Exception:
                pass

        elapsed = (time.monotonic() - start) * 1000
        _record_run("booking_status_sync", "success", f"Synced {synced}/{len(bookings)} bookings", elapsed)
        logger.info("Booking status sync: %d/%d synced (%.0fms)", synced, len(bookings), elapsed)
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        _record_run("booking_status_sync", "error", str(e), elapsed)
        logger.error("Booking status sync failed: %s", e)


async def job_supplier_reconciliation():
    """Daily: Full supplier reconciliation."""
    import time
    start = time.monotonic()
    try:
        from app.db import get_db
        db = await get_db()

        summary = await db["booking_reconciliation"].aggregate([
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "price_mismatches": {"$sum": {"$cond": ["$price_mismatch", 1, 0]}},
                "status_mismatches": {"$sum": {"$cond": ["$status_mismatch", 1, 0]}},
            }},
        ]).to_list(1)

        stats = summary[0] if summary else {"total": 0, "price_mismatches": 0, "status_mismatches": 0}
        stats.pop("_id", None)

        elapsed = (time.monotonic() - start) * 1000
        _record_run("supplier_reconciliation", "success",
                     f"Total: {stats.get('total', 0)}, Price mismatches: {stats.get('price_mismatches', 0)}", elapsed)
        logger.info("Supplier reconciliation: %s (%.0fms)", stats, elapsed)
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        _record_run("supplier_reconciliation", "error", str(e), elapsed)
        logger.error("Supplier reconciliation failed: %s", e)


async def job_supplier_health_check():
    """Every 15 min: Check supplier health."""
    import time
    start = time.monotonic()
    try:
        from app.suppliers.registry import supplier_registry
        from app.infrastructure.circuit_breaker import get_breaker

        all_adapters = supplier_registry.get_all()
        results = {}
        for adapter in all_adapters:
            breaker = get_breaker(adapter.supplier_code)
            results[adapter.supplier_code] = {
                "circuit_open": not breaker.can_execute(),
            }

        elapsed = (time.monotonic() - start) * 1000
        healthy = sum(1 for v in results.values() if not v["circuit_open"])
        _record_run("supplier_health_check", "success",
                     f"{healthy}/{len(results)} suppliers healthy", elapsed)
        logger.info("Supplier health check: %d/%d healthy (%.0fms)", healthy, len(results), elapsed)
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        _record_run("supplier_health_check", "error", str(e), elapsed)
        logger.error("Supplier health check failed: %s", e)


async def job_analytics_aggregation():
    """Every 30 min: Aggregate analytics data."""
    import time
    start = time.monotonic()
    try:
        from app.db import get_db
        db = await get_db()

        # Count recent search events for analytics
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        search_count = await db["search_analytics"].count_documents(
            {"timestamp": {"$gte": cutoff}}
        )
        booking_count = await db["unified_bookings"].count_documents(
            {"created_at": {"$gte": cutoff}}
        )

        elapsed = (time.monotonic() - start) * 1000
        _record_run("analytics_aggregation", "success",
                     f"Searches: {search_count}, Bookings: {booking_count} (last 1h)", elapsed)
        logger.info("Analytics aggregation: %d searches, %d bookings (%.0fms)", search_count, booking_count, elapsed)
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        _record_run("analytics_aggregation", "error", str(e), elapsed)
        logger.error("Analytics aggregation failed: %s", e)


async def job_revenue_reconciliation():
    """Daily: Revenue reconciliation."""
    import time
    start = time.monotonic()
    try:
        from app.db import get_db
        db = await get_db()

        cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        pipeline = [
            {"$match": {"created_at": {"$gte": cutoff}}},
            {"$group": {
                "_id": None,
                "total_revenue": {"$sum": "$sell_price"},
                "total_cost": {"$sum": "$supplier_cost"},
                "total_margin": {"$sum": "$total_margin"},
                "count": {"$sum": 1},
            }},
        ]
        raw = await db["commission_records"].aggregate(pipeline).to_list(1)
        stats = raw[0] if raw else {"total_revenue": 0, "total_cost": 0, "total_margin": 0, "count": 0}
        stats.pop("_id", None)

        elapsed = (time.monotonic() - start) * 1000
        _record_run("revenue_reconciliation", "success",
                     f"Revenue: {stats.get('total_revenue', 0):.2f}, Margin: {stats.get('total_margin', 0):.2f}", elapsed)
        logger.info("Revenue reconciliation: %s (%.0fms)", stats, elapsed)
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        _record_run("revenue_reconciliation", "error", str(e), elapsed)
        logger.error("Revenue reconciliation failed: %s", e)


# ==========================================================================
# Scheduler Management
# ==========================================================================

_scheduler_started = False
_scheduler = None


def start_scheduler():
    """Start the APScheduler with all configured jobs.

    Uses ``AsyncIOScheduler`` so jobs run on the same event loop as the
    rest of FastAPI. Previously this was a ``BackgroundScheduler`` whose
    thread had its own loop — that produced "Future attached to a
    different loop" errors at every interval, because Motor's
    ``AsyncIOMotorClient`` is bound to the loop on which it was first
    created (FastAPI's main loop). All other schedulers in
    ``app.bootstrap.scheduler_app`` already use ``AsyncIOScheduler``.
    """
    global _scheduler_started, _scheduler
    if _scheduler_started:
        return

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        _scheduler = AsyncIOScheduler(timezone="UTC")

        _scheduler.add_job(
            job_booking_status_sync,
            IntervalTrigger(hours=1), id="booking_status_sync", name="Booking Status Sync",
            replace_existing=True,
        )
        _scheduler.add_job(
            job_supplier_reconciliation,
            IntervalTrigger(hours=24), id="supplier_reconciliation", name="Supplier Reconciliation",
            replace_existing=True,
        )
        _scheduler.add_job(
            job_supplier_health_check,
            IntervalTrigger(minutes=15), id="supplier_health_check", name="Supplier Health Check",
            replace_existing=True,
        )
        _scheduler.add_job(
            job_analytics_aggregation,
            IntervalTrigger(minutes=30), id="analytics_aggregation", name="Analytics Aggregation",
            replace_existing=True,
        )
        _scheduler.add_job(
            job_revenue_reconciliation,
            IntervalTrigger(hours=24), id="revenue_reconciliation", name="Revenue Reconciliation",
            replace_existing=True,
        )

        _scheduler.start()
        _scheduler_started = True
        logger.info("Job scheduler started with 5 scheduled jobs (AsyncIOScheduler)")
    except Exception as e:
        logger.warning("Job scheduler start failed: %s", e)


def get_scheduler_status() -> dict[str, Any]:
    """Return current scheduler state and job info."""
    if not _scheduler:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })

    return {
        "running": _scheduler_started,
        "total_jobs": len(jobs),
        "jobs": jobs,
        "history": get_job_history(),
    }


async def trigger_job_manually(job_name: str) -> dict[str, Any]:
    """Manually trigger a specific job."""
    job_map = {
        "booking_status_sync": job_booking_status_sync,
        "supplier_reconciliation": job_supplier_reconciliation,
        "supplier_health_check": job_supplier_health_check,
        "analytics_aggregation": job_analytics_aggregation,
        "revenue_reconciliation": job_revenue_reconciliation,
    }
    fn = job_map.get(job_name)
    if not fn:
        return {"error": f"Unknown job: {job_name}", "available": list(job_map.keys())}

    await fn()
    return {"triggered": job_name, "timestamp": datetime.now(timezone.utc).isoformat()}
