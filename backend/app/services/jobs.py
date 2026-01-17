from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from pymongo import ReturnDocument

from app.db import get_db

logger = logging.getLogger(__name__)

JobHandler = Callable[[Any, Dict[str, Any]], Awaitable[None]]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def enqueue_job(
    db,
    *,
    organization_id: str,
    type: str,
    payload: Dict[str, Any],
    max_attempts: int = 3,
    run_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Insert a new job document into the jobs collection.

    This is a thin abstraction over Mongo; higher-level services are expected to
    validate payload structure.
    """

    now = _now()
    doc: Dict[str, Any] = {
        "organization_id": organization_id,
        "type": type,
        "payload": payload or {},
        "status": "pending",
        "attempts": 0,
        "max_attempts": max_attempts,
        "locked_by": None,
        "locked_at": None,
        "next_run_at": run_at or now,
        "last_error": None,
        "result_summary": None,
        "created_at": now,
        "updated_at": now,
    }
    res = await db.jobs.insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def claim_job(
    db,
    *,
    worker_id: str,
    now: Optional[datetime] = None,
    lock_ttl_seconds: int = 300,
) -> Optional[Dict[str, Any]]:
    """Atomically claim a pending job for execution.

    - Picks the oldest pending job whose next_run_at <= now
    - Respects a simple lock TTL to recover from crashed workers
    """

    if now is None:
        now = _now()
    lock_expiry = now - timedelta(seconds=lock_ttl_seconds)

    query = {
        "status": {"$in": ["pending", "failed"]},
        "next_run_at": {"$lte": now},
        "$or": [
            {"locked_at": {"$exists": False}},
            {"locked_at": None},
            {"locked_at": {"$lt": lock_expiry}},
        ],
    }

    update = {
        "$set": {
            "status": "running",
            "locked_by": worker_id,
            "locked_at": now,
            "updated_at": now,
        }
    }

    job = await db.jobs.find_one_and_update(
        query,
        update,
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )
    return job


async def _mark_succeeded(db, job: Dict[str, Any], result_summary: Optional[Dict[str, Any]] = None) -> None:
    now = _now()
    await db.jobs.update_one(
        {"_id": job["_id"]},
        {
            "$set": {
                "status": "succeeded",
                "result_summary": result_summary,
                "updated_at": now,
            }
        },
    )


def _compute_backoff(attempts: int) -> timedelta:
    """Compute retry backoff delay.

    For now we keep this effectively zero in order to make retry behavior
    deterministic in tests and simple in production. The structure allows
    future tuning without changing call sites.
    """
    base_seconds = 0
    delay = base_seconds * (2 ** max(attempts - 1, 0))
    return timedelta(seconds=min(delay, 3600))


async def _mark_failed(db, job: Dict[str, Any], error: str) -> None:
    now = _now()
    attempts = int(job.get("attempts") or 0) + 1
    max_attempts = int(job.get("max_attempts") or 3)

    if attempts >= max_attempts:
        status = "dead"
        next_run_at = None
    else:
        status = "failed"
        next_run_at = now + _compute_backoff(attempts)

    await db.jobs.update_one(
        {"_id": job["_id"]},
        {
            "$set": {
                "status": status,
                "attempts": attempts,
                "last_error": error,
                "next_run_at": next_run_at,
                "locked_by": None,
                "locked_at": None,
                "updated_at": now,
            }
        },
    )


JOB_HANDLERS: Dict[str, JobHandler] = {}


async def handle_indexnow_submit(db, job: Dict[str, Any]) -> None:
    """Job handler for IndexNow URL submissions.

    Behaviour:
    - If IndexNow is disabled or not configured, we treat the job as
      successfully "skipped" and mark it succeeded (no retries).
    - On transport errors, we let the normal job retry/backoff semantics
      handle transient failures.
    """

    from app.services.indexnow_client import IndexNowClient, IndexNowSettings

    settings = IndexNowSettings()
    client = IndexNowClient(settings)

    try:
        payload = job.get("payload") or {}
        urls = payload.get("urls") or []
        if not urls:
            await _mark_succeeded(db, job, result_summary={"ok": True, "status": "empty"})
            return

        # Single vs batch submission
        if len(urls) == 1:
            result = await client.submit_single_url(urls[0])
        else:
            result = await client.submit_batch(urls)

        status = result.get("status")
        if status in {"skipped", "success"}:
            await _mark_succeeded(db, job, result_summary=result)
            return

        # For error statuses we raise to let the job system apply retry/backoff
        raise RuntimeError(f"IndexNow submission failed: {result}")
    finally:
        await client.aclose()




def register_job_handler(job_type: str, handler: JobHandler) -> None:
    if job_type in JOB_HANDLERS:
        logger.warning("Overwriting job handler for type %s", job_type)
    JOB_HANDLERS[job_type] = handler


async def process_claimed_job(db, job: Dict[str, Any]) -> None:
    """Execute a claimed job using the registered handler.

    Any exception from the handler is captured and translated into failed/dead
    status with backoff semantics.
    """

    job_type = job.get("type") or ""
    handler = JOB_HANDLERS.get(job_type)
    if not handler:
        await _mark_failed(db, job, f"NO_HANDLER for type={job_type}")
        return

    try:
        await handler(db, job)
        await _mark_succeeded(db, job, result_summary={"ok": True})
    except Exception as exc:  # pragma: no cover - error branch
        logger.error("Job %s of type %s failed: %s", job.get("_id"), job_type, exc, exc_info=True)
        await _mark_failed(db, job, str(exc))


# Register built-in job handlers
register_job_handler("seo.indexnow_submit", handle_indexnow_submit)


async def run_job_worker_loop(worker_id: str, *, sleep_seconds: int = 5) -> None:
    """Simple background loop to process jobs.

    Intended to be triggered from server.py via an env flag.
    """

    db = await get_db()
    while True:
        job = await claim_job(db, worker_id=worker_id)
        if job:
            await process_claimed_job(db, job)
        else:
            await asyncio_sleep(sleep_seconds)


async def asyncio_sleep(seconds: int) -> None:
    """Tiny indirection around asyncio.sleep for easier monkeypatching in tests."""
    import asyncio

    await asyncio.sleep(seconds)


async def enqueue_indexnow_job(db, *, organization_id: str, urls: list[str]) -> Dict[str, Any]:
    """Convenience helper to enqueue an IndexNow submission job.

    This is a thin wrapper around `enqueue_job` so higher-level services can
    schedule URL submission without knowing job type internals.
    """

    payload = {"urls": urls}
    return await enqueue_job(
        db,
        organization_id=organization_id,
        type="seo.indexnow_submit",
        payload=payload,
    )
