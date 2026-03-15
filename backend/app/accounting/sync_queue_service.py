"""Accounting Sync Queue Service.

Manages the lifecycle of invoice sync jobs to accounting providers.
Implements: enqueue -> process -> retry (with backoff) -> success/fail.

DB Collection: accounting_sync_jobs

Flow: invoice issued -> sync job queued -> processed -> synced/failed -> retry

Retry schedule: 5m, 15m, 1h, 6h, 24h (max 5 attempts)
"""
from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any

from app.accounting.integrators.base_accounting_integrator import ERR_DUPLICATE_RECORD
from app.accounting.integrators.registry import get_accounting_integrator
from app.accounting.tenant_integrator_service import get_integrator_credentials
from app.db import get_db
from app.utils import now_utc, serialize_doc

logger = logging.getLogger("accounting.sync_queue")

JOBS_COL = "accounting_sync_jobs"
INVOICES_COL = "invoices"

# Job status constants
JOB_PENDING = "pending"
JOB_PROCESSING = "processing"
JOB_SYNCED = "synced"
JOB_FAILED = "failed"
JOB_RETRYING = "retrying"

MAX_ATTEMPTS = 5

# Retry backoff schedule (minutes)
RETRY_BACKOFF = [5, 15, 60, 360, 1440]


def _get_next_retry_delay(attempt_count: int) -> timedelta:
    """Get retry delay based on attempt count (exponential backoff)."""
    idx = min(attempt_count - 1, len(RETRY_BACKOFF) - 1)
    if idx < 0:
        idx = 0
    return timedelta(minutes=RETRY_BACKOFF[idx])


async def enqueue_sync_job(
    tenant_id: str,
    invoice_id: str,
    provider: str = "luca",
    triggered_by: str = "",
) -> dict[str, Any]:
    """Enqueue an invoice for accounting sync. Idempotent by invoice_id + provider."""
    db = await get_db()

    # Idempotency: check existing job for this provider + invoice_id
    existing = await db[JOBS_COL].find_one({
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "provider": provider,
    })

    if existing:
        status = existing.get("status", "")
        if status == JOB_SYNCED:
            return {
                "error": "duplicate",
                "message": "Bu fatura zaten senkronize edilmis",
                "job": serialize_doc(existing),
            }
        if status in (JOB_FAILED, JOB_RETRYING):
            # Re-queue: reset to pending
            now = now_utc()
            await db[JOBS_COL].update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "status": JOB_PENDING,
                    "next_retry": None,
                    "triggered_by": triggered_by,
                    "updated_at": now,
                }},
            )
            updated = await db[JOBS_COL].find_one({"_id": existing["_id"]})
            return serialize_doc(updated)
        # Already pending or processing
        return serialize_doc(existing)

    # Verify invoice exists and is issued
    invoice = await db[INVOICES_COL].find_one({
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
    })
    if not invoice:
        return {"error": "Fatura bulunamadi"}

    inv_status = invoice.get("status", "")
    if inv_status not in ("issued", "synced", "sync_failed"):
        return {"error": f"Fatura durumu '{inv_status}', sadece kesilmis faturalar senkronize edilebilir"}

    now = now_utc()
    job_id = f"SYNCJOB-{uuid.uuid4().hex[:8].upper()}"

    doc = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "provider": provider,
        "status": JOB_PENDING,
        "attempt_count": 0,
        "last_attempt": None,
        "next_retry": None,
        "error_type": None,
        "error_message": None,
        "external_ref": None,
        "triggered_by": triggered_by,
        "created_at": now,
        "updated_at": now,
    }
    await db[JOBS_COL].insert_one(doc)
    return serialize_doc(doc)


async def process_sync_job(
    tenant_id: str,
    invoice_id: str,
    provider: str = "luca",
    actor: str = "",
) -> dict[str, Any]:
    """Process a sync job: execute the actual sync to accounting provider.

    Core flow:
    1. Load job and invoice
    2. Customer matching (get_or_create)
    3. Call accounting integrator
    4. Update job status and invoice accounting fields
    """
    db = await get_db()

    job = await db[JOBS_COL].find_one({
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "provider": provider,
    })

    if not job:
        # Auto-enqueue
        enqueue_result = await enqueue_sync_job(tenant_id, invoice_id, provider, actor)
        if "error" in enqueue_result:
            return enqueue_result
        job = await db[JOBS_COL].find_one({
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
            "provider": provider,
        })

    if not job:
        return {"error": "Senkronizasyon isi olusturulamadi"}

    if job.get("status") == JOB_SYNCED:
        return {
            "error": "duplicate",
            "message": "Bu fatura zaten senkronize edilmis",
            "job": serialize_doc(job),
        }

    # Load invoice
    invoice = await db[INVOICES_COL].find_one({
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
    })
    if not invoice:
        return {"error": "Fatura bulunamadi"}

    # Get integrator and credentials
    integrator = get_accounting_integrator(provider)
    if not integrator:
        return {"error": f"Desteklenmeyen muhasebe sistemi: {provider}"}

    creds = await get_integrator_credentials(tenant_id, provider) or {}

    # Mark as processing
    now = now_utc()
    attempt_count = (job.get("attempt_count") or 0) + 1
    await db[JOBS_COL].update_one(
        {"_id": job["_id"]},
        {"$set": {
            "status": JOB_PROCESSING,
            "attempt_count": attempt_count,
            "last_attempt": now,
            "updated_at": now,
        }},
    )

    # Customer matching (get_or_create)
    customer_data = (serialize_doc(invoice)).get("customer") or {}
    if customer_data.get("name") or customer_data.get("tax_id"):
        try:
            from app.accounting.customer_matching_service import get_or_create_customer
            cust_result = await get_or_create_customer(tenant_id, provider, customer_data)
            logger.info("Customer matched for %s: %s", invoice_id, cust_result.get("action"))
        except Exception as e:
            logger.warning("Customer matching failed for %s: %s", invoice_id, e)

    # Execute sync
    invoice_data = serialize_doc(invoice)
    try:
        result = await integrator.sync_invoice(invoice_data, creds)
    except Exception as e:
        return await _handle_job_failure(
            db, job, attempt_count, str(e), "transient_error", invoice
        )

    now = now_utc()
    if result.success:
        await db[JOBS_COL].update_one(
            {"_id": job["_id"]},
            {"$set": {
                "status": JOB_SYNCED,
                "external_ref": result.external_ref,
                "error_type": None,
                "error_message": None,
                "next_retry": None,
                "updated_at": now,
            }},
        )
        await _update_invoice_accounting(db, invoice, "synced", result.external_ref, None)
    else:
        if result.error_type == ERR_DUPLICATE_RECORD:
            # Duplicate = treat as synced
            await db[JOBS_COL].update_one(
                {"_id": job["_id"]},
                {"$set": {
                    "status": JOB_SYNCED,
                    "external_ref": f"duplicate-{invoice_id}",
                    "error_type": None,
                    "error_message": None,
                    "next_retry": None,
                    "updated_at": now,
                }},
            )
            await _update_invoice_accounting(db, invoice, "synced", f"duplicate-{invoice_id}", None)
        else:
            return await _handle_job_failure(
                db, job, attempt_count, result.message, result.error_type, invoice
            )

    # Also update legacy sync_logs for backward compat
    await _update_legacy_sync_log(db, job, result, attempt_count)

    updated = await db[JOBS_COL].find_one({"_id": job["_id"]})
    return serialize_doc(updated)


async def retry_failed_job(
    tenant_id: str,
    job_id: str,
    actor: str = "",
) -> dict[str, Any]:
    """Manually retry a failed sync job."""
    db = await get_db()
    job = await db[JOBS_COL].find_one({
        "tenant_id": tenant_id,
        "job_id": job_id,
    })
    if not job:
        return {"error": "Senkronizasyon isi bulunamadi"}

    if job.get("status") == JOB_SYNCED:
        return {"error": "Bu senkronizasyon zaten basarili"}

    # Reset to pending
    await db[JOBS_COL].update_one(
        {"_id": job["_id"]},
        {"$set": {"status": JOB_PENDING, "next_retry": None, "updated_at": now_utc()}},
    )

    return await process_sync_job(
        tenant_id=job["tenant_id"],
        invoice_id=job["invoice_id"],
        provider=job["provider"],
        actor=actor,
    )


async def get_pending_retry_jobs(limit: int = 50) -> list[dict[str, Any]]:
    """Get jobs that are due for retry (next_retry <= now)."""
    db = await get_db()
    now = now_utc()
    cursor = db[JOBS_COL].find({
        "status": JOB_RETRYING,
        "next_retry": {"$lte": now},
        "attempt_count": {"$lt": MAX_ATTEMPTS},
    }).sort("next_retry", 1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [serialize_doc(d) for d in docs]


async def get_sync_queue_stats(tenant_id: str) -> dict[str, Any]:
    """Get sync queue statistics for dashboard."""
    db = await get_db()
    q: dict[str, Any] = {"tenant_id": tenant_id}

    total = await db[JOBS_COL].count_documents(q)
    pending = await db[JOBS_COL].count_documents({**q, "status": JOB_PENDING})
    processing = await db[JOBS_COL].count_documents({**q, "status": JOB_PROCESSING})
    synced = await db[JOBS_COL].count_documents({**q, "status": JOB_SYNCED})
    failed = await db[JOBS_COL].count_documents({**q, "status": JOB_FAILED})
    retrying = await db[JOBS_COL].count_documents({**q, "status": JOB_RETRYING})

    last_sync = await db[JOBS_COL].find_one(
        {**q, "last_attempt": {"$ne": None}},
        sort=[("last_attempt", -1)],
    )
    last_sync_at = str(last_sync["last_attempt"]) if last_sync and last_sync.get("last_attempt") else None

    last_error_doc = await db[JOBS_COL].find_one(
        {**q, "status": {"$in": [JOB_FAILED, JOB_RETRYING]}, "error_message": {"$ne": None}},
        sort=[("updated_at", -1)],
    )
    last_error = last_error_doc.get("error_message") if last_error_doc else None
    last_error_type = last_error_doc.get("error_type") if last_error_doc else None

    # Provider status
    from app.accounting.tenant_integrator_service import get_integrator_credentials
    providers_status = []
    for prov in ["luca"]:
        creds = await get_integrator_credentials(tenant_id, prov)
        providers_status.append({
            "provider": prov,
            "configured": creds is not None,
        })

    return {
        "total_jobs": total,
        "pending": pending,
        "processing": processing,
        "synced": synced,
        "failed": failed,
        "retrying": retrying,
        "retry_queue": retrying + failed,
        "last_sync_at": last_sync_at,
        "last_error": last_error,
        "last_error_type": last_error_type,
        "providers": providers_status,
    }


async def list_sync_jobs(
    tenant_id: str,
    provider: str | None = None,
    status: str | None = None,
    limit: int = 50,
    skip: int = 0,
) -> dict[str, Any]:
    """List sync jobs with filters."""
    db = await get_db()
    q: dict[str, Any] = {"tenant_id": tenant_id}
    if provider:
        q["provider"] = provider
    if status:
        q["status"] = status

    total = await db[JOBS_COL].count_documents(q)
    cursor = db[JOBS_COL].find(q).sort("updated_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {
        "items": [serialize_doc(d) for d in docs],
        "total": total,
        "limit": limit,
        "skip": skip,
    }


async def _handle_job_failure(
    db, job: dict, attempt_count: int, message: str, error_type: str, invoice: dict,
) -> dict[str, Any]:
    """Handle a failed sync job with retry scheduling."""
    now = now_utc()

    if attempt_count >= MAX_ATTEMPTS:
        # Max retries reached - mark as permanently failed
        await db[JOBS_COL].update_one(
            {"_id": job["_id"]},
            {"$set": {
                "status": JOB_FAILED,
                "error_type": error_type,
                "error_message": message,
                "next_retry": None,
                "updated_at": now,
            }},
        )
    else:
        # Schedule retry
        delay = _get_next_retry_delay(attempt_count)
        next_retry = now + delay
        await db[JOBS_COL].update_one(
            {"_id": job["_id"]},
            {"$set": {
                "status": JOB_RETRYING,
                "error_type": error_type,
                "error_message": message,
                "next_retry": next_retry,
                "updated_at": now,
            }},
        )

    # Invoice state must NOT change on accounting failure
    await _update_invoice_accounting(db, invoice, "sync_failed", None, message)

    # Update legacy sync log
    await _update_legacy_sync_log_failure(db, job, message, error_type, attempt_count)

    updated = await db[JOBS_COL].find_one({"_id": job["_id"]})
    return serialize_doc(updated)


async def _update_invoice_accounting(
    db, invoice: dict, status: str, ref: str | None, error: str | None,
) -> None:
    """Update invoice accounting fields without changing invoice status."""
    now = now_utc()
    update: dict[str, Any] = {
        "accounting_status": status,
        "updated_at": now,
    }
    if ref is not None:
        update["accounting_ref"] = ref
    if error is not None:
        update["accounting_error"] = error
    else:
        update["accounting_error"] = None
    await db[INVOICES_COL].update_one({"_id": invoice["_id"]}, {"$set": update})


async def _update_legacy_sync_log(
    db, job: dict, result: Any, attempt_count: int,
) -> None:
    """Update legacy accounting_sync_logs for backward compatibility."""
    try:
        from app.accounting.accounting_sync_service import SYNC_COL
        existing = await db[SYNC_COL].find_one({
            "tenant_id": job["tenant_id"],
            "invoice_id": job["invoice_id"],
            "provider": job["provider"],
        })
        now = now_utc()
        if existing:
            await db[SYNC_COL].update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "sync_status": "synced" if result.success else "failed",
                    "external_accounting_ref": result.external_ref if result.success else None,
                    "sync_attempt_count": attempt_count,
                    "last_attempt_at": now,
                    "last_error": None if result.success else result.message,
                    "last_error_type": None if result.success else result.error_type,
                    "updated_at": now,
                }},
            )
    except Exception as e:
        logger.debug("Legacy sync log update skipped: %s", e)


async def _update_legacy_sync_log_failure(
    db, job: dict, message: str, error_type: str, attempt_count: int,
) -> None:
    """Update legacy sync log on failure."""
    try:
        from app.accounting.accounting_sync_service import SYNC_COL
        existing = await db[SYNC_COL].find_one({
            "tenant_id": job["tenant_id"],
            "invoice_id": job["invoice_id"],
            "provider": job["provider"],
        })
        now = now_utc()
        if existing:
            await db[SYNC_COL].update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "sync_status": "failed",
                    "sync_attempt_count": attempt_count,
                    "last_attempt_at": now,
                    "last_error": message,
                    "last_error_type": error_type,
                    "updated_at": now,
                }},
            )
    except Exception as e:
        logger.debug("Legacy sync log failure update skipped: %s", e)
