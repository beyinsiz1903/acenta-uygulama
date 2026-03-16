"""Sync Stability Service — P4.2.

Provides:
  1. Partial failure handling — preserve successful records on partial sync failure
  2. Retry window — automatic retry for failed/partial jobs with backoff
  3. Supplier downtime behavior — circuit breaker + stale-while-revalidate
  4. Partial region sync recovery — retry only failed regions
  5. Stability reporting — aggregated job health metrics

Endpoints exposed via inventory_sync_router.py:
  POST /api/inventory/sync/retry/{job_id}
  POST /api/inventory/sync/retry-region/{supplier}/{region_id}
  GET  /api/inventory/sync/stability-report
  POST /api/inventory/sync/cancel/{job_id}
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any

from app.db import get_db
from app.services.sync_job_state import (
    SyncJobStatus,
    RETRY_CONFIG,
    REGION_SYNC_CONFIG,
    can_transition,
    is_retryable,
)

logger = logging.getLogger("sync.stability")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── 1. Partial Failure Handling ──────────────────────────────────────

async def finalize_sync_job(
    job_oid,
    *,
    total_records: int,
    successful_records: int,
    failed_records: int,
    errors: list[dict],
    region_results: list[dict] | None = None,
    sync_duration_ms: float,
    extra_fields: dict | None = None,
) -> str:
    """Finalize a sync job with partial failure awareness.

    Returns the computed final status.
    """
    db = await get_db()

    if failed_records == 0 and total_records > 0:
        status = SyncJobStatus.COMPLETED
    elif successful_records > 0 and failed_records > 0:
        status = SyncJobStatus.COMPLETED_WITH_PARTIAL_ERRORS
    elif total_records == 0:
        status = SyncJobStatus.COMPLETED
    else:
        status = SyncJobStatus.FAILED

    update_doc = {
        "status": status,
        "finished_at": _ts(),
        "duration_ms": sync_duration_ms,
        "records_total": total_records,
        "records_succeeded": successful_records,
        "records_failed": failed_records,
        "errors": errors[:50],
        "error_count": len(errors),
    }

    if region_results:
        update_doc["region_results"] = region_results

    if extra_fields:
        update_doc.update(extra_fields)

    # If partial errors, compute retry eligibility
    if status == SyncJobStatus.COMPLETED_WITH_PARTIAL_ERRORS:
        job = await db.inventory_sync_jobs.find_one({"_id": job_oid}, {"_id": 0, "retry_count": 1})
        retry_count = (job.get("retry_count", 0) if job else 0)
        if retry_count < RETRY_CONFIG["max_retries"]:
            update_doc["retry_eligible"] = True
            update_doc["failed_items"] = [
                {"hotel_id": e.get("hotel_id"), "region": e.get("region"), "error": e.get("error")}
                for e in errors[:100]
                if e.get("hotel_id")
            ]
        else:
            update_doc["retry_eligible"] = False

    await db.inventory_sync_jobs.update_one(
        {"_id": job_oid},
        {"$set": update_doc},
    )

    logger.info(
        "Sync job finalized: status=%s, total=%d, ok=%d, fail=%d",
        status, total_records, successful_records, failed_records,
    )
    return status


# ── 2. Retry Window ─────────────────────────────────────────────────

async def schedule_retry(job_id: str) -> dict[str, Any]:
    """Schedule a retry for a failed or partial-error sync job.

    Uses exponential backoff based on retry_count.
    """
    db = await get_db()

    from bson import ObjectId
    try:
        job_oid = ObjectId(job_id)
    except Exception:
        return {"error": "Invalid job_id format", "job_id": job_id}

    job = await db.inventory_sync_jobs.find_one({"_id": job_oid})
    if not job:
        return {"error": "Job not found", "job_id": job_id}

    current_status = job.get("status")
    if not is_retryable(current_status):
        return {
            "error": f"Job status '{current_status}' is not retryable",
            "retryable_statuses": SyncJobStatus.RETRYABLE,
        }

    retry_count = job.get("retry_count", 0)
    if retry_count >= RETRY_CONFIG["max_retries"]:
        return {
            "error": f"Max retries ({RETRY_CONFIG['max_retries']}) exceeded",
            "retry_count": retry_count,
        }

    # Calculate retry delay with backoff
    delay = min(
        RETRY_CONFIG["retry_delay_seconds"] * (RETRY_CONFIG["retry_backoff_multiplier"] ** retry_count),
        RETRY_CONFIG["max_retry_delay_seconds"],
    )
    retry_at = _now() + timedelta(seconds=delay)

    if not can_transition(current_status, SyncJobStatus.RETRY_SCHEDULED):
        return {"error": f"Cannot transition from '{current_status}' to 'retry_scheduled'"}

    await db.inventory_sync_jobs.update_one(
        {"_id": job_oid},
        {"$set": {
            "status": SyncJobStatus.RETRY_SCHEDULED,
            "retry_count": retry_count + 1,
            "retry_scheduled_at": retry_at.isoformat(),
            "retry_delay_seconds": delay,
            "retry_reason": f"Auto-retry #{retry_count + 1} after {current_status}",
        }},
    )

    logger.info(
        "Retry scheduled for job %s: attempt=%d, delay=%.0fs",
        job_id, retry_count + 1, delay,
    )

    return {
        "status": "retry_scheduled",
        "job_id": job_id,
        "supplier": job.get("supplier"),
        "retry_count": retry_count + 1,
        "retry_at": retry_at.isoformat(),
        "delay_seconds": delay,
    }


async def execute_scheduled_retries() -> dict[str, Any]:
    """Execute all sync jobs that are due for retry.

    Called by scheduler or manually via API.
    """
    db = await get_db()
    now = _now().isoformat()

    due_jobs = []
    cursor = db.inventory_sync_jobs.find(
        {
            "status": SyncJobStatus.RETRY_SCHEDULED,
            "retry_scheduled_at": {"$lte": now},
        },
        {"_id": 1, "supplier": 1, "retry_count": 1, "failed_items": 1},
    )
    async for job in cursor:
        due_jobs.append(job)

    results = []
    for job in due_jobs:
        supplier = job.get("supplier")
        job_oid = job["_id"]

        # Transition to running
        await db.inventory_sync_jobs.update_one(
            {"_id": job_oid},
            {"$set": {"status": SyncJobStatus.RUNNING, "started_at": _ts()}},
        )

        # Trigger the sync
        from app.services.inventory_sync_service import trigger_supplier_sync
        result = await trigger_supplier_sync(supplier)
        results.append({
            "job_id": str(job_oid),
            "supplier": supplier,
            "retry_count": job.get("retry_count", 0),
            "result_status": result.get("status"),
        })

    return {
        "executed": len(results),
        "results": results,
        "timestamp": _ts(),
    }


# ── 3. Supplier Downtime Behavior ───────────────────────────────────

async def check_supplier_downtime(supplier: str) -> dict[str, Any]:
    """Check if supplier is currently down and return circuit breaker status.

    Returns:
      - is_down: bool
      - circuit_state: str (closed/open/half_open)
      - last_successful_sync: timestamp
      - stale_cache_available: bool
    """
    from app.infrastructure.circuit_breaker import get_breaker
    breaker = get_breaker(f"supplier_{supplier}")
    cb_status = breaker.get_status()

    db = await get_db()

    # Last successful sync
    last_success = await db.inventory_sync_jobs.find_one(
        {"supplier": supplier, "status": {"$in": [SyncJobStatus.COMPLETED, SyncJobStatus.COMPLETED_WITH_PARTIAL_ERRORS]}},
        {"_id": 0, "finished_at": 1, "records_updated": 1, "records_succeeded": 1},
        sort=[("finished_at", -1)],
    )

    # Check if we have stale cache
    cache_count = await db.inventory_index.count_documents({"supplier": supplier})

    # Recent failure streak
    recent_jobs = []
    cursor = db.inventory_sync_jobs.find(
        {"supplier": supplier},
        {"_id": 0, "status": 1, "finished_at": 1},
    ).sort("started_at", -1).limit(5)
    async for j in cursor:
        recent_jobs.append(j)

    consecutive_failures = 0
    for j in recent_jobs:
        if j.get("status") in [SyncJobStatus.FAILED, SyncJobStatus.STUCK]:
            consecutive_failures += 1
        else:
            break

    is_down = cb_status["state"] == "open" or consecutive_failures >= 3

    return {
        "supplier": supplier,
        "is_down": is_down,
        "circuit_state": cb_status["state"],
        "circuit_details": cb_status,
        "consecutive_failures": consecutive_failures,
        "last_successful_sync": last_success.get("finished_at") if last_success else None,
        "stale_cache_available": cache_count > 0,
        "stale_cache_entries": cache_count,
        "recommendation": _downtime_recommendation(is_down, cache_count, consecutive_failures),
    }


def _downtime_recommendation(is_down: bool, cache_count: int, failures: int) -> str:
    if not is_down:
        return "Supplier is healthy. Normal operations."
    if cache_count > 0:
        return "Supplier is down. Serving from stale cache. Search results may be outdated."
    return "Supplier is down with no cached data. Search results unavailable for this supplier."


async def record_sync_outcome_to_breaker(supplier: str, success: bool) -> None:
    """Record sync outcome to the circuit breaker for this supplier."""
    from app.infrastructure.circuit_breaker import get_breaker
    breaker = get_breaker(f"supplier_{supplier}")
    if success:
        breaker.record_success()
    else:
        breaker.record_failure()


async def should_skip_sync_due_to_downtime(supplier: str) -> tuple[bool, str]:
    """Check if sync should be skipped because the supplier circuit is open.

    Returns (should_skip, reason).
    """
    from app.infrastructure.circuit_breaker import get_breaker
    breaker = get_breaker(f"supplier_{supplier}")
    if not breaker.can_execute():
        return True, f"Circuit breaker OPEN for {supplier}. Skipping sync to avoid cascading failures."
    return False, ""


# ── 4. Partial Region Sync Recovery ─────────────────────────────────

async def retry_failed_region(supplier: str, region_id: str) -> dict[str, Any]:
    """Retry sync for a specific region that failed.

    Only re-syncs hotels in the target region, preserving successful data from other regions.
    """
    regions = REGION_SYNC_CONFIG.get(supplier, [])
    target_region = next((r for r in regions if r["id"] == region_id), None)

    if not target_region:
        return {
            "error": f"Region '{region_id}' not found for supplier '{supplier}'",
            "available_regions": [r["id"] for r in regions],
        }

    db = await get_db()
    sync_start = time.monotonic()

    # Create a region-specific job
    job_doc = {
        "supplier": supplier,
        "job_type": "region_retry",
        "region_id": region_id,
        "region_name": target_region["name"],
        "status": SyncJobStatus.RUNNING,
        "started_at": _ts(),
        "finished_at": None,
        "records_updated": 0,
        "errors": [],
        "sync_mode": "simulation",
    }
    result = await db.inventory_sync_jobs.insert_one(job_doc)
    job_oid = result.inserted_id
    job_id = str(job_oid)

    # Perform region-specific sync (simulation mode for now)
    from app.services.inventory_sync_service import _determine_sync_mode
    sync_mode, _ = await _determine_sync_mode(supplier)

    inventory_count = 0
    errors = []

    try:
        # Sync only hotels in the target region/city
        from app.services.inventory_sync_service import _SIMULATED_HOTELS

        region_hotels = [h for h in _SIMULATED_HOTELS if h["city"].lower() == target_region["name"].lower()]
        if not region_hotels:
            region_hotels = _SIMULATED_HOTELS[:3]

        for idx, hotel_template in enumerate(region_hotels):
            try:
                hotel_id = f"{supplier[:2]}_{target_region['id']}_{idx + 1:04d}"
                inventory_doc = {
                    "supplier": supplier,
                    "hotel_id": hotel_id,
                    "name": hotel_template["name"],
                    "city": target_region["name"],
                    "country": target_region["country"],
                    "stars": hotel_template["stars"],
                    "rooms": hotel_template["rooms"],
                    "updated_at": _ts(),
                    "sync_job_id": job_id,
                    "region_id": region_id,
                }
                await db.supplier_inventory.update_one(
                    {"supplier": supplier, "hotel_id": hotel_id},
                    {"$set": inventory_doc},
                    upsert=True,
                )
                inventory_count += 1
            except Exception as e:
                errors.append({"hotel_id": hotel_id, "region": region_id, "error": str(e)})

        # Rebuild search index for this region
        from app.services.inventory_sync_service import _build_search_index
        await _build_search_index(db, supplier)

        status = await finalize_sync_job(
            job_oid,
            total_records=len(region_hotels),
            successful_records=inventory_count,
            failed_records=len(errors),
            errors=errors,
            sync_duration_ms=round((time.monotonic() - sync_start) * 1000, 1),
            extra_fields={"region_id": region_id, "region_name": target_region["name"]},
        )
    except Exception as e:
        logger.error("Region retry failed: %s/%s: %s", supplier, region_id, e)
        status = SyncJobStatus.FAILED
        await db.inventory_sync_jobs.update_one(
            {"_id": job_oid},
            {"$set": {
                "status": status,
                "finished_at": _ts(),
                "errors": [{"error": str(e), "phase": "region_retry"}],
            }},
        )

    return {
        "job_id": job_id,
        "supplier": supplier,
        "region_id": region_id,
        "region_name": target_region["name"],
        "status": status,
        "records_updated": inventory_count,
        "errors": errors,
        "duration_ms": round((time.monotonic() - sync_start) * 1000, 1),
        "timestamp": _ts(),
    }


async def get_region_sync_status(supplier: str) -> dict[str, Any]:
    """Get per-region sync status for a supplier."""
    db = await get_db()
    regions = REGION_SYNC_CONFIG.get(supplier, [])

    region_status = []
    for region in regions:
        # Count inventory for this region
        count = await db.supplier_inventory.count_documents({
            "supplier": supplier,
            "city": {"$regex": f"^{region['name']}$", "$options": "i"},
        })

        # Last region-specific job
        last_job = await db.inventory_sync_jobs.find_one(
            {"supplier": supplier, "region_id": region["id"]},
            {"_id": 0, "status": 1, "finished_at": 1, "records_updated": 1, "errors": 1},
            sort=[("started_at", -1)],
        )

        region_status.append({
            "region_id": region["id"],
            "name": region["name"],
            "country": region["country"],
            "hotel_count": count,
            "last_sync_status": last_job.get("status") if last_job else "never",
            "last_sync_at": last_job.get("finished_at") if last_job else None,
            "errors": len(last_job.get("errors", [])) if last_job else 0,
        })

    return {
        "supplier": supplier,
        "regions": region_status,
        "total_regions": len(regions),
        "timestamp": _ts(),
    }


# ── 5. Stability Report ────────────────────────────────────────────

async def get_stability_report(supplier: str | None = None) -> dict[str, Any]:
    """Generate a comprehensive sync stability report.

    Aggregates job health, failure rates, retry effectiveness, and downtime.
    """
    db = await get_db()
    query: dict[str, Any] = {}
    if supplier:
        query["supplier"] = supplier

    # Job stats (last 24h)
    cutoff = (_now() - timedelta(hours=24)).isoformat()
    recent_query = {**query, "started_at": {"$gte": cutoff}}

    total_jobs = await db.inventory_sync_jobs.count_documents(recent_query)
    completed_jobs = await db.inventory_sync_jobs.count_documents({**recent_query, "status": SyncJobStatus.COMPLETED})
    partial_jobs = await db.inventory_sync_jobs.count_documents({**recent_query, "status": SyncJobStatus.COMPLETED_WITH_PARTIAL_ERRORS})
    failed_jobs = await db.inventory_sync_jobs.count_documents({**recent_query, "status": SyncJobStatus.FAILED})
    stuck_jobs = await db.inventory_sync_jobs.count_documents({**recent_query, "status": SyncJobStatus.STUCK})
    retry_jobs = await db.inventory_sync_jobs.count_documents({**recent_query, "status": SyncJobStatus.RETRY_SCHEDULED})

    # Success rate
    success_rate = round(((completed_jobs + partial_jobs) / max(total_jobs, 1)) * 100, 2)

    # Average duration
    duration_pipeline = [
        {"$match": {**recent_query, "duration_ms": {"$exists": True}}},
        {"$group": {"_id": None, "avg": {"$avg": "$duration_ms"}, "max": {"$max": "$duration_ms"}}},
    ]
    dur_result = await db.inventory_sync_jobs.aggregate(duration_pipeline).to_list(1)
    avg_duration = round(dur_result[0]["avg"], 1) if dur_result else 0
    max_duration = round(dur_result[0]["max"], 1) if dur_result else 0

    # Per-supplier breakdown
    supplier_breakdown = {}
    from app.services.inventory_sync_service import SUPPLIER_SYNC_CONFIG
    suppliers_list = [supplier] if supplier else list(SUPPLIER_SYNC_CONFIG.keys())

    for sup in suppliers_list:
        sup_query = {"supplier": sup, "started_at": {"$gte": cutoff}}
        sup_total = await db.inventory_sync_jobs.count_documents(sup_query)
        sup_ok = await db.inventory_sync_jobs.count_documents({**sup_query, "status": SyncJobStatus.COMPLETED})
        sup_partial = await db.inventory_sync_jobs.count_documents({**sup_query, "status": SyncJobStatus.COMPLETED_WITH_PARTIAL_ERRORS})
        sup_failed = await db.inventory_sync_jobs.count_documents({**sup_query, "status": SyncJobStatus.FAILED})

        # Downtime check
        downtime = await check_supplier_downtime(sup)

        supplier_breakdown[sup] = {
            "total_jobs_24h": sup_total,
            "completed": sup_ok,
            "partial_errors": sup_partial,
            "failed": sup_failed,
            "success_rate": round(((sup_ok + sup_partial) / max(sup_total, 1)) * 100, 2),
            "is_down": downtime["is_down"],
            "circuit_state": downtime["circuit_state"],
            "stale_cache_entries": downtime["stale_cache_entries"],
        }

    # Retry effectiveness
    retry_pipeline = [
        {"$match": {**query, "retry_count": {"$gt": 0}}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
        }},
    ]
    retry_stats = {}
    async for doc in db.inventory_sync_jobs.aggregate(retry_pipeline):
        retry_stats[doc["_id"]] = doc["count"]

    retries_succeeded = retry_stats.get(SyncJobStatus.COMPLETED, 0) + retry_stats.get(SyncJobStatus.COMPLETED_WITH_PARTIAL_ERRORS, 0)
    retries_total = sum(retry_stats.values())

    return {
        "period": "last_24h",
        "total_jobs": total_jobs,
        "job_breakdown": {
            "completed": completed_jobs,
            "partial_errors": partial_jobs,
            "failed": failed_jobs,
            "stuck": stuck_jobs,
            "retry_scheduled": retry_jobs,
        },
        "success_rate": success_rate,
        "avg_duration_ms": avg_duration,
        "max_duration_ms": max_duration,
        "supplier_breakdown": supplier_breakdown,
        "retry_effectiveness": {
            "total_retries": retries_total,
            "retries_succeeded": retries_succeeded,
            "retry_success_rate": round((retries_succeeded / max(retries_total, 1)) * 100, 2),
        },
        "timestamp": _ts(),
    }


# ── Guard: Stuck Job Detection (Enhanced) ───────────────────────────

async def detect_and_handle_stuck_jobs() -> dict[str, Any]:
    """Detect stuck jobs and either mark them or schedule retries.

    A job is stuck if status=running and started_at > threshold ago.
    """
    db = await get_db()
    threshold = (_now() - timedelta(minutes=RETRY_CONFIG["stuck_threshold_minutes"])).isoformat()

    stuck_cursor = db.inventory_sync_jobs.find(
        {"status": SyncJobStatus.RUNNING, "started_at": {"$lt": threshold}},
    )

    handled = []
    async for job in stuck_cursor:
        job_oid = job["_id"]
        supplier = job.get("supplier", "unknown")
        retry_count = job.get("retry_count", 0)

        if retry_count < RETRY_CONFIG["max_retries"]:
            # Schedule retry
            new_status = SyncJobStatus.RETRY_SCHEDULED
            delay = min(
                RETRY_CONFIG["retry_delay_seconds"] * (RETRY_CONFIG["retry_backoff_multiplier"] ** retry_count),
                RETRY_CONFIG["max_retry_delay_seconds"],
            )
            retry_at = _now() + timedelta(seconds=delay)

            await db.inventory_sync_jobs.update_one(
                {"_id": job_oid},
                {"$set": {
                    "status": new_status,
                    "finished_at": _ts(),
                    "error_note": "Stuck job detected — retry scheduled",
                    "retry_count": retry_count + 1,
                    "retry_scheduled_at": retry_at.isoformat(),
                }},
            )
        else:
            # Max retries exceeded — mark as stuck (terminal for now)
            new_status = SyncJobStatus.STUCK
            await db.inventory_sync_jobs.update_one(
                {"_id": job_oid},
                {"$set": {
                    "status": new_status,
                    "finished_at": _ts(),
                    "error_note": f"Stuck job — max retries ({RETRY_CONFIG['max_retries']}) exceeded",
                }},
            )

        # Record failure to circuit breaker
        await record_sync_outcome_to_breaker(supplier, success=False)

        handled.append({
            "job_id": str(job_oid),
            "supplier": supplier,
            "new_status": new_status,
            "retry_count": retry_count,
        })

    if handled:
        logger.warning("Handled %d stuck jobs", len(handled))

    return {"handled": len(handled), "jobs": handled, "timestamp": _ts()}


async def cancel_sync_job(job_id: str) -> dict[str, Any]:
    """Cancel a sync job (only if in a cancellable state)."""
    db = await get_db()

    from bson import ObjectId
    try:
        job_oid = ObjectId(job_id)
    except Exception:
        return {"error": "Invalid job_id format"}

    job = await db.inventory_sync_jobs.find_one({"_id": job_oid})
    if not job:
        return {"error": "Job not found"}

    current_status = job.get("status")
    if not can_transition(current_status, SyncJobStatus.CANCELLED):
        return {"error": f"Cannot cancel job in status '{current_status}'"}

    await db.inventory_sync_jobs.update_one(
        {"_id": job_oid},
        {"$set": {
            "status": SyncJobStatus.CANCELLED,
            "finished_at": _ts(),
            "cancelled_by": "operator",
            "cancel_reason": "Manual cancellation",
        }},
    )

    return {
        "status": "cancelled",
        "job_id": job_id,
        "supplier": job.get("supplier"),
        "previous_status": current_status,
        "timestamp": _ts(),
    }
