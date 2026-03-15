"""Accounting Sync Service (Faz 3).

Manages the lifecycle of invoice synchronization to accounting systems (Luca, etc.).
Implements idempotent sync, error classification, retry tracking, and dashboard stats.

Flow: issued invoice -> sync queue -> accounting adapter -> sync result

DB Collection: accounting_sync_logs
"""
from __future__ import annotations

import uuid
from typing import Any

from app.accounting.integrators.base_accounting_integrator import (
    ERR_DUPLICATE_RECORD,
)
from app.accounting.integrators.registry import get_accounting_integrator
from app.accounting.tenant_integrator_service import get_integrator_credentials
from app.db import get_db
from app.utils import now_utc, serialize_doc

SYNC_COL = "accounting_sync_logs"
INVOICES_COL = "invoices"

# Sync status constants
SYNC_PENDING = "pending"
SYNC_IN_PROGRESS = "in_progress"
SYNC_SUCCESS = "synced"
SYNC_FAILED = "failed"

MAX_AUTO_RETRIES = 3


async def queue_invoice_for_sync(
    tenant_id: str,
    invoice_id: str,
    provider: str = "luca",
    triggered_by: str = "",
) -> dict[str, Any]:
    """Queue an issued invoice for accounting sync. Idempotent by invoice_id + provider."""
    db = await get_db()

    # Idempotency: check if already queued/synced
    existing = await db[SYNC_COL].find_one({
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "provider": provider,
    })
    if existing:
        if existing.get("sync_status") == SYNC_SUCCESS:
            return {
                "error": "duplicate",
                "message": "Bu fatura zaten senkronize edilmis",
                "sync_log": serialize_doc(existing),
            }
        # If failed, allow re-queue by updating status
        if existing.get("sync_status") == SYNC_FAILED:
            await db[SYNC_COL].update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "sync_status": SYNC_PENDING,
                    "updated_at": now_utc(),
                    "triggered_by": triggered_by,
                }},
            )
            updated = await db[SYNC_COL].find_one({"_id": existing["_id"]})
            return serialize_doc(updated)
        # Already pending or in_progress
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
    sync_id = f"SYNC-{uuid.uuid4().hex[:8].upper()}"

    doc = {
        "sync_id": sync_id,
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "provider": provider,
        "external_accounting_ref": None,
        "sync_status": SYNC_PENDING,
        "sync_attempt_count": 0,
        "last_attempt_at": None,
        "last_error": None,
        "last_error_type": None,
        "triggered_by": triggered_by,
        "created_at": now,
        "updated_at": now,
    }
    await db[SYNC_COL].insert_one(doc)
    return serialize_doc(doc)


async def execute_sync(
    tenant_id: str,
    invoice_id: str,
    provider: str = "luca",
    actor: str = "",
) -> dict[str, Any]:
    """Execute the actual sync of an invoice to the accounting system.

    This is the core sync function. It:
    1. Loads the sync log and invoice
    2. Calls the accounting integrator adapter
    3. Updates sync status and invoice accounting fields
    """
    db = await get_db()

    sync_log = await db[SYNC_COL].find_one({
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "provider": provider,
    })

    if not sync_log:
        # Auto-queue if not exists
        queue_result = await queue_invoice_for_sync(tenant_id, invoice_id, provider, actor)
        if "error" in queue_result and queue_result["error"] != "duplicate":
            return queue_result
        if "error" in queue_result and queue_result["error"] == "duplicate":
            return queue_result
        sync_log = await db[SYNC_COL].find_one({
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
            "provider": provider,
        })

    if not sync_log:
        return {"error": "Senkronizasyon kaydi olusturulamadi"}

    # Already synced?
    if sync_log.get("sync_status") == SYNC_SUCCESS:
        return {
            "error": "duplicate",
            "message": "Bu fatura zaten senkronize edilmis",
            "sync_log": serialize_doc(sync_log),
        }

    # Load invoice data
    invoice = await db[INVOICES_COL].find_one({
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
    })
    if not invoice:
        return {"error": "Fatura bulunamadi"}

    # Get accounting integrator
    integrator = get_accounting_integrator(provider)
    if not integrator:
        return {"error": f"Desteklenmeyen muhasebe sistemi: {provider}"}

    # Get credentials
    creds = await get_integrator_credentials(tenant_id, provider) or {}

    # Mark as in_progress
    now = now_utc()
    attempt_count = (sync_log.get("sync_attempt_count") or 0) + 1
    await db[SYNC_COL].update_one(
        {"_id": sync_log["_id"]},
        {"$set": {
            "sync_status": SYNC_IN_PROGRESS,
            "sync_attempt_count": attempt_count,
            "last_attempt_at": now,
            "updated_at": now,
        }},
    )

    # Execute sync
    invoice_data = serialize_doc(invoice)
    try:
        result = await integrator.sync_invoice(invoice_data, creds)
    except Exception as e:
        result_data = _handle_sync_failure(
            str(e), "transient_error", sync_log, attempt_count
        )
        await db[SYNC_COL].update_one(
            {"_id": sync_log["_id"]},
            {"$set": result_data},
        )
        await _update_invoice_accounting_status(db, invoice, SYNC_FAILED, None, str(e))
        updated = await db[SYNC_COL].find_one({"_id": sync_log["_id"]})
        return serialize_doc(updated)

    now = now_utc()
    if result.success:
        # Sync succeeded
        await db[SYNC_COL].update_one(
            {"_id": sync_log["_id"]},
            {"$set": {
                "sync_status": SYNC_SUCCESS,
                "external_accounting_ref": result.external_ref,
                "last_error": None,
                "last_error_type": None,
                "updated_at": now,
            }},
        )
        await _update_invoice_accounting_status(
            db, invoice, "synced", result.external_ref, None
        )
    else:
        # Sync failed
        error_data = _handle_sync_failure(
            result.message, result.error_type, sync_log, attempt_count
        )
        await db[SYNC_COL].update_one(
            {"_id": sync_log["_id"]},
            {"$set": error_data},
        )
        # Handle duplicate as special case: mark as synced with note
        if result.error_type == ERR_DUPLICATE_RECORD:
            await _update_invoice_accounting_status(
                db, invoice, "synced", f"duplicate-{invoice_id}", None
            )
        else:
            await _update_invoice_accounting_status(
                db, invoice, "sync_failed", None, result.message
            )

    updated = await db[SYNC_COL].find_one({"_id": sync_log["_id"]})
    return serialize_doc(updated)


async def retry_sync(
    tenant_id: str,
    sync_id: str,
    actor: str = "",
) -> dict[str, Any]:
    """Manually retry a failed sync."""
    db = await get_db()
    sync_log = await db[SYNC_COL].find_one({
        "tenant_id": tenant_id,
        "sync_id": sync_id,
    })
    if not sync_log:
        return {"error": "Senkronizasyon kaydi bulunamadi"}

    if sync_log.get("sync_status") == SYNC_SUCCESS:
        return {"error": "Bu senkronizasyon zaten basarili"}

    # Reset to pending and execute
    await db[SYNC_COL].update_one(
        {"_id": sync_log["_id"]},
        {"$set": {"sync_status": SYNC_PENDING, "updated_at": now_utc()}},
    )

    return await execute_sync(
        tenant_id=sync_log["tenant_id"],
        invoice_id=sync_log["invoice_id"],
        provider=sync_log["provider"],
        actor=actor,
    )


async def get_sync_logs(
    tenant_id: str,
    provider: str | None = None,
    status: str | None = None,
    limit: int = 50,
    skip: int = 0,
) -> dict[str, Any]:
    """List sync logs with filters."""
    db = await get_db()
    q: dict[str, Any] = {"tenant_id": tenant_id}
    if provider:
        q["provider"] = provider
    if status:
        q["sync_status"] = status

    total = await db[SYNC_COL].count_documents(q)
    cursor = db[SYNC_COL].find(q).sort("updated_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {
        "items": [serialize_doc(d) for d in docs],
        "total": total,
        "limit": limit,
        "skip": skip,
    }


async def get_accounting_dashboard(tenant_id: str) -> dict[str, Any]:
    """Get accounting sync dashboard statistics."""
    db = await get_db()
    q: dict[str, Any] = {"tenant_id": tenant_id}

    total = await db[SYNC_COL].count_documents(q)
    pending = await db[SYNC_COL].count_documents({**q, "sync_status": SYNC_PENDING})
    in_progress = await db[SYNC_COL].count_documents({**q, "sync_status": SYNC_IN_PROGRESS})
    success = await db[SYNC_COL].count_documents({**q, "sync_status": SYNC_SUCCESS})
    failed = await db[SYNC_COL].count_documents({**q, "sync_status": SYNC_FAILED})

    # Last sync attempt
    last_sync = await db[SYNC_COL].find_one(
        {**q, "last_attempt_at": {"$ne": None}},
        sort=[("last_attempt_at", -1)],
    )
    last_sync_at = None
    if last_sync:
        last_sync_at = last_sync.get("last_attempt_at")
        if last_sync_at:
            last_sync_at = str(last_sync_at)

    # Last error
    last_error_doc = await db[SYNC_COL].find_one(
        {**q, "sync_status": SYNC_FAILED, "last_error": {"$ne": None}},
        sort=[("updated_at", -1)],
    )
    last_error = None
    last_error_type = None
    if last_error_doc:
        last_error = last_error_doc.get("last_error")
        last_error_type = last_error_doc.get("last_error_type")

    # Provider connection status
    providers_status = []
    for prov in ["luca"]:
        creds = await get_integrator_credentials(tenant_id, prov)
        providers_status.append({
            "provider": prov,
            "configured": creds is not None,
        })

    return {
        "total_syncs": total,
        "pending": pending,
        "in_progress": in_progress,
        "success": success,
        "failed": failed,
        "last_sync_at": last_sync_at,
        "last_error": last_error,
        "last_error_type": last_error_type,
        "providers": providers_status,
    }


def _handle_sync_failure(
    message: str, error_type: str, sync_log: dict, attempt_count: int,
) -> dict[str, Any]:
    """Build the update dict for a failed sync attempt."""
    now = now_utc()
    return {
        "sync_status": SYNC_FAILED,
        "last_error": message,
        "last_error_type": error_type,
        "updated_at": now,
    }


async def _update_invoice_accounting_status(
    db, invoice: dict, status: str, ref: str | None, error: str | None,
) -> None:
    """Update the invoice document with accounting sync status."""
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
