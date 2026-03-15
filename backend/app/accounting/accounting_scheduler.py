"""Accounting Sync Scheduler.

Background job that:
1. Processes pending retry jobs (backoff: 5m, 15m, 1h, 6h, 24h)
2. Polls status of recently synced invoices
3. Auto-syncs invoices based on rules
4. Runs hourly incremental reconciliation
5. Runs daily full reconciliation
6. Checks and generates financial alerts

Designed to be added to the existing APScheduler infrastructure.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("accounting.scheduler")


async def process_retry_queue() -> dict:
    """Process accounting sync jobs that are due for retry.

    Called by the scheduler every 2 minutes.
    """
    from app.accounting.sync_queue_service import (
        get_pending_retry_jobs,
        process_sync_job,
    )

    jobs = await get_pending_retry_jobs(limit=20)
    if not jobs:
        return {"processed": 0}

    processed = 0
    errors = 0
    for job in jobs:
        try:
            result = await process_sync_job(
                tenant_id=job["tenant_id"],
                invoice_id=job["invoice_id"],
                provider=job["provider"],
                actor="scheduler",
            )
            if result.get("status") == "synced":
                processed += 1
            else:
                errors += 1
        except Exception as e:
            logger.error("Retry job %s failed: %s", job.get("job_id"), e)
            errors += 1

    if processed or errors:
        logger.info(
            "Accounting retry queue: processed=%d, errors=%d, total=%d",
            processed, errors, len(jobs),
        )
    return {"processed": processed, "errors": errors, "total": len(jobs)}


async def poll_sync_status() -> dict:
    """Poll accounting providers for status updates on recently synced invoices.

    Called by the scheduler every 10 minutes.
    """
    from app.accounting.integrators.registry import get_accounting_integrator
    from app.accounting.sync_queue_service import JOBS_COL, JOB_SYNCED
    from app.accounting.tenant_integrator_service import get_integrator_credentials
    from app.db import get_db
    from app.utils import now_utc

    db = await get_db()
    # Poll synced jobs from the last 24 hours that have an external_ref
    from datetime import timedelta
    cutoff = now_utc() - timedelta(hours=24)
    cursor = db[JOBS_COL].find({
        "status": JOB_SYNCED,
        "external_ref": {"$ne": None},
        "updated_at": {"$gte": cutoff},
    }).limit(20)
    jobs = await cursor.to_list(length=20)

    polled = 0
    for job in jobs:
        provider = job.get("provider", "luca")
        integrator = get_accounting_integrator(provider)
        if not integrator:
            continue
        creds = await get_integrator_credentials(job["tenant_id"], provider) or {}
        try:
            result = await integrator.get_sync_status(job["external_ref"], creds)
            if result.success:
                polled += 1
        except Exception as e:
            logger.debug("Status poll for %s failed: %s", job.get("job_id"), e)

    return {"polled": polled, "total": len(jobs)}


async def run_incremental_reconciliation() -> dict:
    """Run hourly incremental reconciliation for all tenants.

    Called by scheduler every hour. Checks only recent data (last 2 hours).
    """
    from app.db import get_db
    db = await get_db()

    # Get all distinct tenant IDs that have invoices
    tenant_ids = await db.invoices.distinct("tenant_id")
    total_mismatches = 0

    for tenant_id in tenant_ids:
        if not tenant_id:
            continue
        try:
            from app.accounting.reconciliation_service import run_reconciliation
            result = await run_reconciliation(
                tenant_id=tenant_id,
                run_type="incremental",
                triggered_by="scheduler_hourly",
                lookback_hours=2,
            )
            total_mismatches += result.get("mismatch_count", 0)
        except Exception as e:
            logger.error("Incremental recon failed for tenant %s: %s", tenant_id, e)

    if total_mismatches:
        logger.info("Incremental reconciliation: %d mismatches across %d tenants",
                     total_mismatches, len(tenant_ids))
    return {"tenants": len(tenant_ids), "total_mismatches": total_mismatches}


async def run_full_reconciliation() -> dict:
    """Run daily full reconciliation for all tenants.

    Called by scheduler once daily. Checks all data.
    """
    from app.db import get_db
    db = await get_db()

    tenant_ids = await db.invoices.distinct("tenant_id")
    total_mismatches = 0

    for tenant_id in tenant_ids:
        if not tenant_id:
            continue
        try:
            from app.accounting.reconciliation_service import run_reconciliation
            result = await run_reconciliation(
                tenant_id=tenant_id,
                run_type="full",
                triggered_by="scheduler_daily",
                lookback_hours=None,
            )
            total_mismatches += result.get("mismatch_count", 0)
        except Exception as e:
            logger.error("Full recon failed for tenant %s: %s", tenant_id, e)

    logger.info("Full reconciliation: %d mismatches across %d tenants",
                total_mismatches, len(tenant_ids))
    return {"tenants": len(tenant_ids), "total_mismatches": total_mismatches}


async def check_financial_alerts() -> dict:
    """Check and generate financial alerts for all tenants.

    Called by scheduler every 30 minutes.
    """
    from app.db import get_db
    db = await get_db()

    tenant_ids = await db.invoices.distinct("tenant_id")
    total_alerts = 0

    for tenant_id in tenant_ids:
        if not tenant_id:
            continue
        try:
            from app.accounting.financial_alerts_service import check_and_generate_alerts
            result = await check_and_generate_alerts(tenant_id)
            total_alerts += result.get("alerts_generated", 0)
        except Exception as e:
            logger.error("Alert check failed for tenant %s: %s", tenant_id, e)

    if total_alerts:
        logger.info("Financial alerts: %d generated across %d tenants",
                     total_alerts, len(tenant_ids))
    return {"tenants": len(tenant_ids), "alerts_generated": total_alerts}
