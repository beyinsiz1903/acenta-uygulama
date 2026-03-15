"""Reconciliation Engine Service.

Compares booking, invoice, and accounting data to detect mismatches.

Supports:
- Incremental (hourly): checks recent items only
- Full (daily): checks all items for a tenant
- Manual (on-demand): triggered by operator

DB Collections: reconciliation_runs, reconciliation_items

CTO Rules:
- Reconciliation detects and reports only. NO auto-correction in this iteration.
- Mismatches generate finance_ops_queue items and alerts.
"""
from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any

from app.db import get_db
from app.utils import now_utc, serialize_doc

logger = logging.getLogger("accounting.reconciliation")

RUNS_COL = "reconciliation_runs"
ITEMS_COL = "reconciliation_items"

# Mismatch type enum (CTO-mandated)
MISMATCH_MISSING_INVOICE = "missing_invoice"
MISMATCH_AMOUNT = "amount_mismatch"
MISMATCH_TAX = "tax_mismatch"
MISMATCH_MISSING_SYNC = "missing_sync"
MISMATCH_SYNC_AMOUNT = "sync_amount_mismatch"
MISMATCH_DUPLICATE_ENTRY = "duplicate_entry"
MISMATCH_CUSTOMER = "customer_mismatch"
MISMATCH_STATUS = "status_mismatch"

VALID_MISMATCH_TYPES = [
    MISMATCH_MISSING_INVOICE, MISMATCH_AMOUNT, MISMATCH_TAX,
    MISMATCH_MISSING_SYNC, MISMATCH_SYNC_AMOUNT, MISMATCH_DUPLICATE_ENTRY,
    MISMATCH_CUSTOMER, MISMATCH_STATUS,
]

# Severity classification (CTO-mandated)
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"

# Source of truth
SOURCE_BOOKING = "booking"
SOURCE_INVOICE = "invoice"
SOURCE_ACCOUNTING = "accounting"

# Age buckets
AGE_0_1H = "0_1h"
AGE_1_6H = "1_6h"
AGE_6_24H = "6_24h"
AGE_GT_24H = "gt_24h"

# Run types
RUN_INCREMENTAL = "incremental"
RUN_FULL = "full"
RUN_MANUAL = "manual"


def _classify_severity(mismatch_type: str, extra: dict | None = None) -> str:
    """Classify mismatch severity per CTO rules."""
    if mismatch_type == MISMATCH_DUPLICATE_ENTRY:
        return SEVERITY_CRITICAL
    if mismatch_type == MISMATCH_MISSING_SYNC:
        age = (extra or {}).get("age_bucket", "")
        if age == AGE_GT_24H:
            return SEVERITY_CRITICAL
        return SEVERITY_HIGH
    if mismatch_type == MISMATCH_AMOUNT:
        diff = abs((extra or {}).get("amount_diff", 0))
        if diff > 1000:
            return SEVERITY_CRITICAL
        return SEVERITY_HIGH
    if mismatch_type in (MISMATCH_TAX, MISMATCH_CUSTOMER):
        return SEVERITY_HIGH
    if mismatch_type in (MISMATCH_STATUS, MISMATCH_SYNC_AMOUNT):
        return SEVERITY_MEDIUM
    if mismatch_type == MISMATCH_MISSING_INVOICE:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


def _calc_age_bucket(created_at) -> str:
    """Calculate age bucket from a datetime."""
    if not created_at:
        return AGE_GT_24H
    now = now_utc()
    if hasattr(created_at, 'isoformat'):
        # Handle timezone-naive datetimes from MongoDB
        from datetime import timezone
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        diff = now - created_at
    else:
        return AGE_GT_24H
    hours = diff.total_seconds() / 3600
    if hours <= 1:
        return AGE_0_1H
    if hours <= 6:
        return AGE_1_6H
    if hours <= 24:
        return AGE_6_24H
    return AGE_GT_24H


async def run_reconciliation(
    tenant_id: str,
    run_type: str = RUN_MANUAL,
    triggered_by: str = "",
    lookback_hours: int | None = None,
) -> dict[str, Any]:
    """Execute a reconciliation run.

    For incremental: lookback_hours=2 (only recent data)
    For full: lookback_hours=None (all data)
    """
    db = await get_db()
    now = now_utc()
    run_id = f"RECON-{uuid.uuid4().hex[:8].upper()}"

    run_doc = {
        "run_id": run_id,
        "tenant_id": tenant_id,
        "run_type": run_type,
        "status": "running",
        "started_at": now,
        "completed_at": None,
        "triggered_by": triggered_by,
        "stats": {},
        "created_at": now,
    }
    await db[RUNS_COL].insert_one(run_doc)

    try:
        items = []

        # Phase 1: Booking vs Invoice comparison
        booking_items = await _compare_bookings_invoices(db, tenant_id, lookback_hours)
        items.extend(booking_items)

        # Phase 2: Invoice vs Accounting comparison
        acct_items = await _compare_invoices_accounting(db, tenant_id, lookback_hours)
        items.extend(acct_items)

        # Phase 3: Duplicate detection
        dup_items = await _detect_duplicates(db, tenant_id, lookback_hours)
        items.extend(dup_items)

        # Save all mismatch items
        saved_count = 0
        for item in items:
            item["run_id"] = run_id
            item["tenant_id"] = tenant_id
            item["resolution_state"] = "open"
            item["created_at"] = now
            await db[ITEMS_COL].insert_one(item)
            saved_count += 1

        # Build stats
        stats = _build_stats(items)
        completed_at = now_utc()

        await db[RUNS_COL].update_one(
            {"run_id": run_id, "tenant_id": tenant_id},
            {"$set": {
                "status": "completed",
                "completed_at": completed_at,
                "stats": stats,
            }},
        )

        # Generate finance ops items and alerts
        await _generate_ops_items(db, tenant_id, run_id, items)
        await _generate_alerts(db, tenant_id, run_id, stats)

        logger.info(
            "Reconciliation %s complete: %d mismatches (tenant=%s, type=%s)",
            run_id, saved_count, tenant_id, run_type,
        )

        return {
            "run_id": run_id,
            "run_type": run_type,
            "status": "completed",
            "stats": stats,
            "mismatch_count": saved_count,
        }

    except Exception as e:
        logger.error("Reconciliation %s failed: %s", run_id, e)
        await db[RUNS_COL].update_one(
            {"run_id": run_id},
            {"$set": {"status": "failed", "completed_at": now_utc(), "stats": {"error": str(e)}}},
        )
        return {"run_id": run_id, "status": "failed", "error": str(e)}


async def _compare_bookings_invoices(
    db, tenant_id: str, lookback_hours: int | None,
) -> list[dict]:
    """Find bookings without invoices and amount mismatches."""
    items = []
    bq: dict[str, Any] = {"organization_id": tenant_id, "status": {"$in": ["confirmed", "completed"]}}
    if lookback_hours:
        cutoff = now_utc() - timedelta(hours=lookback_hours)
        bq["created_at"] = {"$gte": cutoff}

    bookings = await db.bookings.find(bq).to_list(length=5000)

    for booking in bookings:
        b = serialize_doc(booking)
        booking_id = b.get("id", "")

        # Check for invoice
        invoice = await db.invoices.find_one({
            "tenant_id": tenant_id,
            "booking_id": str(booking_id),
        })

        if not invoice:
            age_bucket = _calc_age_bucket(booking.get("created_at"))
            items.append({
                "booking_id": str(booking_id),
                "invoice_id": None,
                "accounting_ref": None,
                "mismatch_type": MISMATCH_MISSING_INVOICE,
                "severity": _classify_severity(MISMATCH_MISSING_INVOICE),
                "source_of_truth": SOURCE_BOOKING,
                "amount_expected": b.get("total_price") or b.get("grand_total") or 0,
                "amount_actual": 0,
                "tax_expected": 0,
                "tax_actual": 0,
                "age_bucket": age_bucket,
                "details": f"Booking {booking_id} icin fatura bulunamadi",
            })
            continue

        inv = serialize_doc(invoice)
        booking_total = float(b.get("total_price") or b.get("grand_total") or 0)
        invoice_total = float(inv.get("grand_total") or 0)

        if booking_total > 0 and invoice_total > 0 and abs(booking_total - invoice_total) > 0.01:
            items.append({
                "booking_id": str(booking_id),
                "invoice_id": inv.get("invoice_id"),
                "accounting_ref": inv.get("accounting_ref"),
                "mismatch_type": MISMATCH_AMOUNT,
                "severity": _classify_severity(MISMATCH_AMOUNT, {"amount_diff": booking_total - invoice_total}),
                "source_of_truth": SOURCE_BOOKING,
                "amount_expected": booking_total,
                "amount_actual": invoice_total,
                "tax_expected": float(b.get("tax_amount") or 0),
                "tax_actual": float(inv.get("tax_breakdown", {}).get("total_tax") or inv.get("total_tax") or 0),
                "age_bucket": _calc_age_bucket(invoice.get("created_at")),
                "details": f"Tutar uyumsuzlugu: booking={booking_total}, fatura={invoice_total}",
            })

    return items


async def _compare_invoices_accounting(
    db, tenant_id: str, lookback_hours: int | None,
) -> list[dict]:
    """Find issued invoices missing sync and sync mismatches."""
    items = []
    iq: dict[str, Any] = {"tenant_id": tenant_id, "status": {"$in": ["issued", "synced", "sync_failed"]}}
    if lookback_hours:
        cutoff = now_utc() - timedelta(hours=lookback_hours)
        iq["created_at"] = {"$gte": cutoff}

    invoices = await db.invoices.find(iq).to_list(length=5000)

    for invoice in invoices:
        inv = serialize_doc(invoice)
        invoice_id = inv.get("invoice_id", "")

        sync_job = await db.accounting_sync_jobs.find_one({
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
        })

        if not sync_job:
            age_bucket = _calc_age_bucket(invoice.get("created_at"))
            items.append({
                "booking_id": inv.get("booking_id"),
                "invoice_id": invoice_id,
                "accounting_ref": None,
                "mismatch_type": MISMATCH_MISSING_SYNC,
                "severity": _classify_severity(MISMATCH_MISSING_SYNC, {"age_bucket": age_bucket}),
                "source_of_truth": SOURCE_INVOICE,
                "amount_expected": float(inv.get("grand_total") or 0),
                "amount_actual": 0,
                "tax_expected": 0,
                "tax_actual": 0,
                "age_bucket": age_bucket,
                "details": f"Fatura {invoice_id} muhasebe senkronizasyonu bulunamadi",
            })
            continue

        sj = serialize_doc(sync_job)
        if sj.get("status") == "failed" and (sj.get("attempt_count") or 0) >= 5:
            items.append({
                "booking_id": inv.get("booking_id"),
                "invoice_id": invoice_id,
                "accounting_ref": sj.get("external_ref"),
                "mismatch_type": MISMATCH_STATUS,
                "severity": SEVERITY_MEDIUM,
                "source_of_truth": SOURCE_INVOICE,
                "amount_expected": float(inv.get("grand_total") or 0),
                "amount_actual": 0,
                "tax_expected": 0,
                "tax_actual": 0,
                "age_bucket": _calc_age_bucket(sync_job.get("created_at")),
                "details": f"Senkronizasyon kalici basarisiz: {sj.get('error_message', '')}",
            })

    return items


async def _detect_duplicates(
    db, tenant_id: str, lookback_hours: int | None,
) -> list[dict]:
    """Detect duplicate accounting entries for the same invoice."""
    items = []
    jq: dict[str, Any] = {"tenant_id": tenant_id, "status": "synced"}
    if lookback_hours:
        cutoff = now_utc() - timedelta(hours=lookback_hours)
        jq["created_at"] = {"$gte": cutoff}

    pipeline = [
        {"$match": jq},
        {"$group": {"_id": "$invoice_id", "count": {"$sum": 1}, "jobs": {"$push": "$job_id"}}},
        {"$match": {"count": {"$gt": 1}}},
    ]
    async for dup in db.accounting_sync_jobs.aggregate(pipeline):
        items.append({
            "booking_id": None,
            "invoice_id": dup["_id"],
            "accounting_ref": None,
            "mismatch_type": MISMATCH_DUPLICATE_ENTRY,
            "severity": SEVERITY_CRITICAL,
            "source_of_truth": SOURCE_ACCOUNTING,
            "amount_expected": 0,
            "amount_actual": 0,
            "tax_expected": 0,
            "tax_actual": 0,
            "age_bucket": None,
            "details": f"Cift muhasebe kaydi: {len(dup.get('jobs', []))} adet sync job ({', '.join(dup.get('jobs', [])[:3])})",
        })

    return items


def _build_stats(items: list[dict]) -> dict[str, Any]:
    """Build summary statistics from mismatch items."""
    by_type = {}
    by_severity = {}
    for item in items:
        mt = item.get("mismatch_type", "unknown")
        sev = item.get("severity", "low")
        by_type[mt] = by_type.get(mt, 0) + 1
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return {
        "total_mismatches": len(items),
        "by_type": by_type,
        "by_severity": by_severity,
        "critical_count": by_severity.get(SEVERITY_CRITICAL, 0),
        "high_count": by_severity.get(SEVERITY_HIGH, 0),
    }


async def _generate_ops_items(db, tenant_id: str, run_id: str, items: list[dict]) -> None:
    """Create finance ops queue items for critical/high severity mismatches."""
    from app.accounting.finance_ops_service import create_ops_item
    for item in items:
        if item.get("severity") in (SEVERITY_CRITICAL, SEVERITY_HIGH):
            await create_ops_item(
                tenant_id=tenant_id,
                related_type="reconciliation_item",
                related_id=f"{run_id}:{item.get('mismatch_type')}:{item.get('invoice_id') or item.get('booking_id', '')}",
                priority=item.get("severity"),
                description=item.get("details", ""),
                source="reconciliation",
            )


async def _generate_alerts(db, tenant_id: str, run_id: str, stats: dict) -> None:
    """Generate financial alerts based on reconciliation results."""
    from app.accounting.financial_alerts_service import create_alert
    critical = stats.get("critical_count", 0)
    total = stats.get("total_mismatches", 0)

    if critical > 0:
        await create_alert(
            tenant_id=tenant_id,
            alert_type="reconciliation_critical",
            severity="critical",
            message=f"Mutabakat: {critical} kritik uyumsuzluk tespit edildi (run: {run_id})",
            threshold=0,
            current_value=critical,
        )

    if total > 10:
        await create_alert(
            tenant_id=tenant_id,
            alert_type="reconciliation_mismatch",
            severity="warning",
            message=f"Mutabakat: toplam {total} uyumsuzluk tespit edildi (run: {run_id})",
            threshold=10,
            current_value=total,
        )


async def list_runs(
    tenant_id: str,
    run_type: str | None = None,
    limit: int = 20,
    skip: int = 0,
) -> dict[str, Any]:
    """List reconciliation runs."""
    db = await get_db()
    q: dict[str, Any] = {"tenant_id": tenant_id}
    if run_type:
        q["run_type"] = run_type

    total = await db[RUNS_COL].count_documents(q)
    cursor = db[RUNS_COL].find(q).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {"items": [serialize_doc(d) for d in docs], "total": total}


async def list_items(
    tenant_id: str,
    run_id: str | None = None,
    mismatch_type: str | None = None,
    severity: str | None = None,
    resolution_state: str | None = None,
    limit: int = 50,
    skip: int = 0,
) -> dict[str, Any]:
    """List reconciliation items with filters."""
    db = await get_db()
    q: dict[str, Any] = {"tenant_id": tenant_id}
    if run_id:
        q["run_id"] = run_id
    if mismatch_type:
        q["mismatch_type"] = mismatch_type
    if severity:
        q["severity"] = severity
    if resolution_state:
        q["resolution_state"] = resolution_state

    total = await db[ITEMS_COL].count_documents(q)
    cursor = db[ITEMS_COL].find(q).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {"items": [serialize_doc(d) for d in docs], "total": total}


async def get_aging_stats(tenant_id: str) -> dict[str, Any]:
    """Get unsynced invoice aging statistics (CTO KPI)."""
    db = await get_db()
    now_utc()

    issued_invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "status": "issued",
    }).to_list(length=10000)

    buckets = {AGE_0_1H: 0, AGE_1_6H: 0, AGE_6_24H: 0, AGE_GT_24H: 0}
    for inv in issued_invoices:
        # Check if sync job exists
        sync = await db.accounting_sync_jobs.find_one({
            "tenant_id": tenant_id,
            "invoice_id": inv.get("invoice_id"),
            "status": "synced",
        })
        if sync:
            continue
        bucket = _calc_age_bucket(inv.get("created_at"))
        buckets[bucket] = buckets.get(bucket, 0) + 1

    return {
        "unsynced_aging": buckets,
        "total_unsynced": sum(buckets.values()),
    }


async def get_reconciliation_summary(tenant_id: str) -> dict[str, Any]:
    """Get overall reconciliation summary for dashboard."""
    db = await get_db()

    # Last run
    last_run = await db[RUNS_COL].find_one(
        {"tenant_id": tenant_id, "status": "completed"},
        sort=[("completed_at", -1)],
    )

    # Open items
    open_items = await db[ITEMS_COL].count_documents({
        "tenant_id": tenant_id,
        "resolution_state": "open",
    })
    critical_items = await db[ITEMS_COL].count_documents({
        "tenant_id": tenant_id,
        "resolution_state": "open",
        "severity": SEVERITY_CRITICAL,
    })

    # Aging stats
    aging = await get_aging_stats(tenant_id)

    return {
        "last_run": serialize_doc(last_run) if last_run else None,
        "open_mismatches": open_items,
        "critical_mismatches": critical_items,
        **aging,
    }
