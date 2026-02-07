"""E-Fatura service layer (A3 + A4).

Handles invoice CRUD, idempotency, audit logging, and provider dispatch.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.db import get_db
from app.utils import now_utc, serialize_doc
from app.services.efatura.provider import get_efatura_provider


def _compute_idempotency_key(
    tenant_id: str,
    source_type: str,
    source_id: str,
    lines: List[Dict],
    grand_total: float,
) -> str:
    """Deterministic idempotency key."""
    lines_str = "|".join(
        f"{l.get('description','')},{l.get('quantity',0)},{l.get('unit_price',0)},{l.get('tax_rate',0)}"
        for l in (lines or [])
    )
    data = f"{tenant_id}|{source_type}|{source_id}|{grand_total}|{lines_str}"
    return hashlib.sha256(data.encode()).hexdigest()


async def _write_event(db, tenant_id: str, invoice_id: str, event_type: str, payload: Dict = None):
    await db.efatura_events.insert_one({
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "type": event_type,
        "payload": payload or {},
        "created_at": now_utc(),
    })


async def create_efatura_profile(
    tenant_id: str,
    org_id: str,
    data: Dict[str, Any],
    created_by: str,
) -> Dict[str, Any]:
    db = await get_db()
    now = now_utc()
    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "legal_name": data.get("legal_name", ""),
        "tax_number": data.get("tax_number", ""),
        "tax_office": data.get("tax_office", ""),
        "address_line1": data.get("address_line1", ""),
        "address_line2": data.get("address_line2", ""),
        "city": data.get("city", ""),
        "district": data.get("district", ""),
        "postal_code": data.get("postal_code", ""),
        "email": data.get("email", ""),
        "default_currency": data.get("default_currency", "TRY"),
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await db.efatura_profiles.update_one(
        {"tenant_id": tenant_id},
        {"$set": doc},
        upsert=True,
    )
    return serialize_doc(doc)


async def get_efatura_profile(tenant_id: str) -> Optional[Dict]:
    db = await get_db()
    doc = await db.efatura_profiles.find_one({"tenant_id": tenant_id})
    return serialize_doc(doc) if doc else None


async def create_invoice(
    tenant_id: str,
    org_id: str,
    source_type: str,
    source_id: str,
    customer_id: str,
    lines: List[Dict],
    currency: str = "TRY",
    provider: str = "mock",
    created_by: str = "",
) -> Dict[str, Any]:
    db = await get_db()
    now = now_utc()

    subtotal = sum(float(l.get("line_total", 0)) for l in lines)
    tax_total = sum(
        float(l.get("line_total", 0)) * float(l.get("tax_rate", 0)) / 100
        for l in lines
    )
    grand_total = subtotal + tax_total

    idem_key = _compute_idempotency_key(tenant_id, source_type, source_id, lines, grand_total)

    # Idempotency check
    existing = await db.efatura_invoices.find_one({"idempotency_key": idem_key, "tenant_id": tenant_id})
    if existing:
        return serialize_doc(existing)

    invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "invoice_id": invoice_id,
        "source_type": source_type,
        "source_id": source_id,
        "customer_id": customer_id,
        "status": "draft",
        "provider": provider,
        "provider_invoice_id": None,
        "totals": {
            "subtotal": round(subtotal, 2),
            "tax_total": round(tax_total, 2),
            "grand_total": round(grand_total, 2),
            "currency": currency,
        },
        "lines": lines,
        "issued_at": now.isoformat(),
        "sent_at": None,
        "accepted_at": None,
        "rejected_at": None,
        "error_code": None,
        "error_message": None,
        "idempotency_key": idem_key,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await db.efatura_invoices.insert_one(doc)
    await _write_event(db, tenant_id, invoice_id, "invoice.created")
    return serialize_doc(doc)


async def send_invoice(tenant_id: str, invoice_id: str) -> Dict[str, Any]:
    db = await get_db()
    doc = await db.efatura_invoices.find_one({"tenant_id": tenant_id, "invoice_id": invoice_id})
    if not doc:
        return {"error": "Invoice not found"}
    if doc["status"] not in ("draft", "queued"):
        return {"error": f"Cannot send invoice with status '{doc['status']}'"}

    provider = get_efatura_provider(doc.get("provider", "mock"))
    try:
        pid = doc.get("provider_invoice_id")
        if not pid:
            pid = await provider.create_invoice(serialize_doc(doc))
            await db.efatura_invoices.update_one(
                {"_id": doc["_id"]},
                {"$set": {"provider_invoice_id": pid, "status": "queued", "updated_at": now_utc()}},
            )

        status = await provider.send_invoice(pid)
        now = now_utc()
        update: Dict[str, Any] = {"status": status, "updated_at": now}
        if status == "sent":
            update["sent_at"] = now.isoformat()
        elif status == "rejected":
            update["rejected_at"] = now.isoformat()
            update["error_message"] = "Provider rejected"

        await db.efatura_invoices.update_one({"_id": doc["_id"]}, {"$set": update})
        await _write_event(db, tenant_id, invoice_id, f"invoice.{status}")
        return {"status": status, "provider_invoice_id": pid}

    except Exception as e:
        await db.efatura_invoices.update_one(
            {"_id": doc["_id"]},
            {"$set": {"status": "draft", "error_message": str(e), "updated_at": now_utc()}},
        )
        await _write_event(db, tenant_id, invoice_id, "invoice.failed", {"error": str(e)})
        return {"error": str(e)}


async def get_invoice_status(tenant_id: str, invoice_id: str) -> Dict[str, Any]:
    db = await get_db()
    doc = await db.efatura_invoices.find_one({"tenant_id": tenant_id, "invoice_id": invoice_id})
    if not doc:
        return {"error": "Invoice not found"}

    pid = doc.get("provider_invoice_id")
    if pid:
        provider = get_efatura_provider(doc.get("provider", "mock"))
        result = await provider.get_status(pid)
        if result.get("status") and result["status"] != doc.get("status"):
            now = now_utc()
            update: Dict[str, Any] = {"status": result["status"], "updated_at": now}
            if result["status"] == "accepted":
                update["accepted_at"] = now.isoformat()
            await db.efatura_invoices.update_one({"_id": doc["_id"]}, {"$set": update})
            await _write_event(db, tenant_id, invoice_id, f"invoice.{result['status']}")
            doc["status"] = result["status"]

    return serialize_doc(doc)


async def cancel_invoice(tenant_id: str, invoice_id: str) -> Dict[str, Any]:
    db = await get_db()
    doc = await db.efatura_invoices.find_one({"tenant_id": tenant_id, "invoice_id": invoice_id})
    if not doc:
        return {"error": "Invoice not found"}

    pid = doc.get("provider_invoice_id")
    if pid:
        provider = get_efatura_provider(doc.get("provider", "mock"))
        await provider.cancel_invoice(pid)

    await db.efatura_invoices.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": "canceled", "updated_at": now_utc()}},
    )
    await _write_event(db, tenant_id, invoice_id, "invoice.canceled")
    return {"status": "canceled"}


async def list_invoices(
    tenant_id: str, org_id: str,
    status: str = None, limit: int = 50,
) -> List[Dict]:
    db = await get_db()
    q: Dict[str, Any] = {"organization_id": org_id}
    if tenant_id:
        q["tenant_id"] = tenant_id
    if status:
        q["status"] = status
    cursor = db.efatura_invoices.find(q).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [serialize_doc(d) for d in docs]


async def get_invoice_events(tenant_id: str, invoice_id: str) -> List[Dict]:
    db = await get_db()
    cursor = db.efatura_events.find(
        {"tenant_id": tenant_id, "invoice_id": invoice_id}
    ).sort("created_at", 1)
    docs = await cursor.to_list(length=200)
    return [serialize_doc(d) for d in docs]
