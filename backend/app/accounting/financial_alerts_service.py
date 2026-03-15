"""Financial Alerts Service.

Generates and manages financial alerts for:
- High failure rates (>20%)
- Reconciliation mismatches
- Aging (unsynced >24h)
- Other anomalies

DB Collection: financial_alerts

Severity: critical, warning, info
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.db import get_db
from app.utils import now_utc, serialize_doc

logger = logging.getLogger("accounting.alerts")

ALERTS_COL = "financial_alerts"

# Alert types
ALERT_HIGH_FAIL_RATE = "high_fail_rate"
ALERT_RECON_CRITICAL = "reconciliation_critical"
ALERT_RECON_MISMATCH = "reconciliation_mismatch"
ALERT_AGING = "aging_alert"
ALERT_CUSTOM = "custom"

# Severity
SEV_CRITICAL = "critical"
SEV_WARNING = "warning"
SEV_INFO = "info"

# Status
STATUS_ACTIVE = "active"
STATUS_ACKNOWLEDGED = "acknowledged"
STATUS_RESOLVED = "resolved"


async def create_alert(
    tenant_id: str,
    alert_type: str,
    severity: str,
    message: str,
    threshold: float = 0,
    current_value: float = 0,
) -> dict[str, Any]:
    """Create a financial alert. Prevents duplicate active alerts of same type."""
    db = await get_db()

    # Prevent duplicate active alerts of same type within last hour
    from datetime import timedelta
    recent_cutoff = now_utc() - timedelta(hours=1)
    existing = await db[ALERTS_COL].find_one({
        "tenant_id": tenant_id,
        "alert_type": alert_type,
        "status": STATUS_ACTIVE,
        "created_at": {"$gte": recent_cutoff},
    })
    if existing:
        return serialize_doc(existing)

    now = now_utc()
    alert_id = f"ALERT-{uuid.uuid4().hex[:8].upper()}"

    doc = {
        "alert_id": alert_id,
        "tenant_id": tenant_id,
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
        "threshold": threshold,
        "current_value": current_value,
        "status": STATUS_ACTIVE,
        "created_at": now,
        "acknowledged_at": None,
        "resolved_at": None,
    }
    await db[ALERTS_COL].insert_one(doc)
    logger.info("Alert created: %s [%s] %s (tenant=%s)", alert_id, severity, alert_type, tenant_id)
    return serialize_doc(doc)


async def acknowledge_alert(
    alert_id: str,
    actor: str,
    tenant_id: str | None = None,
) -> dict[str, Any] | None:
    """Acknowledge an alert."""
    db = await get_db()
    q: dict[str, Any] = {"alert_id": alert_id}
    if tenant_id:
        q["tenant_id"] = tenant_id

    doc = await db[ALERTS_COL].find_one(q)
    if not doc:
        return None

    now = now_utc()
    await db[ALERTS_COL].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": STATUS_ACKNOWLEDGED, "acknowledged_at": now, "acknowledged_by": actor}},
    )
    updated = await db[ALERTS_COL].find_one({"_id": doc["_id"]})
    return serialize_doc(updated)


async def resolve_alert(
    alert_id: str,
    actor: str,
    tenant_id: str | None = None,
) -> dict[str, Any] | None:
    """Resolve an alert."""
    db = await get_db()
    q: dict[str, Any] = {"alert_id": alert_id}
    if tenant_id:
        q["tenant_id"] = tenant_id

    doc = await db[ALERTS_COL].find_one(q)
    if not doc:
        return None

    now = now_utc()
    await db[ALERTS_COL].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": STATUS_RESOLVED, "resolved_at": now, "resolved_by": actor}},
    )
    updated = await db[ALERTS_COL].find_one({"_id": doc["_id"]})
    return serialize_doc(updated)


async def list_alerts(
    tenant_id: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    limit: int = 50,
    skip: int = 0,
) -> dict[str, Any]:
    """List financial alerts with filters."""
    db = await get_db()
    q: dict[str, Any] = {}
    if tenant_id:
        q["tenant_id"] = tenant_id
    if status:
        q["status"] = status
    if severity:
        q["severity"] = severity

    total = await db[ALERTS_COL].count_documents(q)
    cursor = db[ALERTS_COL].find(q).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {"items": [serialize_doc(d) for d in docs], "total": total}


async def get_alert_stats(tenant_id: str | None = None) -> dict[str, Any]:
    """Get alert stats for dashboard."""
    db = await get_db()
    q: dict[str, Any] = {}
    if tenant_id:
        q["tenant_id"] = tenant_id

    active = await db[ALERTS_COL].count_documents({**q, "status": STATUS_ACTIVE})
    acknowledged = await db[ALERTS_COL].count_documents({**q, "status": STATUS_ACKNOWLEDGED})
    critical_active = await db[ALERTS_COL].count_documents({**q, "status": STATUS_ACTIVE, "severity": SEV_CRITICAL})

    return {
        "active_alerts": active,
        "acknowledged_alerts": acknowledged,
        "critical_active": critical_active,
    }


async def check_and_generate_alerts(tenant_id: str) -> dict[str, Any]:
    """Check conditions and generate alerts. Called by scheduler."""
    db = await get_db()
    generated = []

    # 1. High fail rate (>20%)
    total_jobs = await db.accounting_sync_jobs.count_documents({"tenant_id": tenant_id})
    failed_jobs = await db.accounting_sync_jobs.count_documents({
        "tenant_id": tenant_id, "status": {"$in": ["failed", "retrying"]},
    })
    if total_jobs > 0:
        fail_rate = failed_jobs / total_jobs
        if fail_rate > 0.2:
            alert = await create_alert(
                tenant_id=tenant_id,
                alert_type=ALERT_HIGH_FAIL_RATE,
                severity=SEV_CRITICAL if fail_rate > 0.5 else SEV_WARNING,
                message=f"Yuksek basarisizlik orani: %{fail_rate*100:.1f} ({failed_jobs}/{total_jobs})",
                threshold=0.2,
                current_value=fail_rate,
            )
            generated.append(alert)

    # 2. Aging: unsynced invoices >24h
    from datetime import timedelta
    cutoff_24h = now_utc() - timedelta(hours=24)
    aged_count = 0
    aged_invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "status": "issued",
        "created_at": {"$lt": cutoff_24h},
    }).to_list(length=1000)

    for inv in aged_invoices:
        sync = await db.accounting_sync_jobs.find_one({
            "tenant_id": tenant_id,
            "invoice_id": inv.get("invoice_id"),
            "status": "synced",
        })
        if not sync:
            aged_count += 1

    if aged_count > 0:
        alert = await create_alert(
            tenant_id=tenant_id,
            alert_type=ALERT_AGING,
            severity=SEV_CRITICAL if aged_count > 10 else SEV_WARNING,
            message=f"{aged_count} fatura 24 saatten fazla suredir senkronize edilmedi",
            threshold=0,
            current_value=aged_count,
        )
        generated.append(alert)

    return {"alerts_generated": len(generated)}
