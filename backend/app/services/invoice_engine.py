"""Invoice Engine Service (Faz 1).

Replaces the basic efatura service with a full invoice engine.
Handles:
- Invoice CRUD with idempotency
- State machine transitions
- Booking → Invoice creation
- Decision engine integration
- Dashboard stats
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Any, Optional

from app.db import get_db
from app.domain.invoice.booking_transform import build_invoice_from_booking
from app.domain.invoice.decision_engine import decide_document_type
from app.domain.invoice.models import (
    InvoiceStatus,
    InvoiceType,
    build_customer_billing_profile,
    build_tax_breakdown,
)
from app.domain.invoice.state_machine import (
    InvoiceStateError,
    get_allowed_transitions,
    validate_invoice_transition,
)
from app.services.efatura.provider import get_efatura_provider
from app.utils import now_utc, serialize_doc


COL = "invoices"
EVENTS_COL = "invoice_events"


def _idempotency_key(tenant_id: str, booking_id: str) -> str:
    data = f"{tenant_id}|booking|{booking_id}"
    return hashlib.sha256(data.encode()).hexdigest()


def _manual_idempotency_key(tenant_id: str, lines: list[dict], grand_total: float) -> str:
    lines_str = "|".join(
        f"{ln.get('description','')},{ln.get('quantity',0)},{ln.get('unit_price',0)}"
        for ln in (lines or [])
    )
    data = f"{tenant_id}|manual|{grand_total}|{lines_str}"
    return hashlib.sha256(data.encode()).hexdigest()


async def _write_event(
    db, tenant_id: str, invoice_id: str, event_type: str, actor: str = "", payload: dict | None = None,
):
    await db[EVENTS_COL].insert_one({
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "type": event_type,
        "actor": actor,
        "payload": payload or {},
        "created_at": now_utc(),
    })


# ── Create from Booking ──────────────────────────────────────────────

async def create_invoice_from_booking(
    tenant_id: str,
    org_id: str,
    booking_id: str,
    customer_data: dict[str, Any] | None = None,
    created_by: str = "",
) -> dict[str, Any]:
    """Create an invoice from a booking. Idempotent by booking_id."""
    db = await get_db()

    idem_key = _idempotency_key(tenant_id, booking_id)
    existing = await db[COL].find_one({"idempotency_key": idem_key, "tenant_id": tenant_id})
    if existing:
        return serialize_doc(existing)

    from bson import ObjectId
    try:
        booking = await db.bookings.find_one({"_id": ObjectId(booking_id), "organization_id": org_id})
    except Exception:
        booking = await db.bookings.find_one({"_id": booking_id, "organization_id": org_id})

    if not booking:
        return {"error": "Booking not found"}

    booking_ser = serialize_doc(booking)

    customer_profile = None
    if customer_data:
        customer_profile = build_customer_billing_profile(**customer_data)
    else:
        customer_profile = build_customer_billing_profile(
            name=booking_ser.get("guest_name") or booking_ser.get("customer_name") or "",
        )

    invoice_payload = build_invoice_from_booking(booking_ser, customer_profile)

    customer_type = (customer_profile or {}).get("customer_type", "b2c")
    tax_id = (customer_profile or {}).get("tax_id", "")
    id_number = (customer_profile or {}).get("id_number", "")

    decision = decide_document_type(
        customer_type=customer_type,
        tax_id=tax_id,
        id_number=id_number,
    )

    now = now_utc()
    invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"

    doc = {
        "invoice_id": invoice_id,
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "source_type": "booking",
        "source_id": booking_id,
        "booking_id": booking_id,
        "booking_ref": invoice_payload.get("booking_ref", ""),
        "product_type": invoice_payload.get("product_type", "hotel"),
        "status": InvoiceStatus.DRAFT,
        "invoice_type": decision["document_type"],
        "decision_reason": decision["reason"],
        "customer": customer_profile,
        "lines": invoice_payload.get("lines", []),
        "totals": invoice_payload.get("totals", {}),
        "currency_info": invoice_payload.get("currency_info", {}),
        "hotel_name": invoice_payload.get("hotel_name", ""),
        "guest_name": invoice_payload.get("guest_name", ""),
        "stay": invoice_payload.get("stay", {}),
        "provider": "mock",
        "provider_invoice_id": None,
        "provider_status": None,
        "accounting_ref": None,
        "accounting_status": None,
        "idempotency_key": idem_key,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "issued_at": None,
        "cancelled_at": None,
        "error_message": None,
    }
    await db[COL].insert_one(doc)
    await _write_event(db, tenant_id, invoice_id, "invoice.created", created_by)
    return serialize_doc(doc)


# ── Manual Invoice ────────────────────────────────────────────────────

async def create_manual_invoice(
    tenant_id: str,
    org_id: str,
    lines: list[dict],
    customer_data: dict[str, Any] | None = None,
    currency: str = "TRY",
    created_by: str = "",
) -> dict[str, Any]:
    """Create a manual invoice (not linked to booking)."""
    db = await get_db()

    processed_lines = []
    for ln in lines:
        lt = ln.get("line_total") or round(float(ln.get("quantity", 1)) * float(ln.get("unit_price", 0)), 2)
        tax_rate = float(ln.get("tax_rate", 20))
        tax_amount = round(lt * tax_rate / 100, 2)
        processed_lines.append({
            "description": ln.get("description", ""),
            "quantity": float(ln.get("quantity", 1)),
            "unit_price": float(ln.get("unit_price", 0)),
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "line_total": lt,
            "gross_total": round(lt + tax_amount, 2),
            "product_type": ln.get("product_type", "hotel"),
            "line_type": ln.get("line_type", "service"),
        })

    totals = build_tax_breakdown(processed_lines, currency)
    idem_key = _manual_idempotency_key(tenant_id, processed_lines, totals["grand_total"])

    existing = await db[COL].find_one({"idempotency_key": idem_key, "tenant_id": tenant_id})
    if existing:
        return serialize_doc(existing)

    customer_profile = None
    if customer_data:
        customer_profile = build_customer_billing_profile(**customer_data)

    customer_type = (customer_profile or {}).get("customer_type", "b2c")
    tax_id = (customer_profile or {}).get("tax_id", "")
    id_number = (customer_profile or {}).get("id_number", "")

    decision = decide_document_type(
        customer_type=customer_type,
        tax_id=tax_id,
        id_number=id_number,
    )

    now = now_utc()
    invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"

    doc = {
        "invoice_id": invoice_id,
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "source_type": "manual",
        "source_id": "",
        "booking_id": None,
        "booking_ref": "",
        "product_type": "manual",
        "status": InvoiceStatus.DRAFT,
        "invoice_type": decision["document_type"],
        "decision_reason": decision["reason"],
        "customer": customer_profile,
        "lines": processed_lines,
        "totals": totals,
        "currency_info": {"invoice_currency": currency, "booking_currency": currency, "exchange_rate": 1.0, "same_currency": True},
        "hotel_name": "",
        "guest_name": (customer_profile or {}).get("name", ""),
        "stay": {},
        "provider": "mock",
        "provider_invoice_id": None,
        "provider_status": None,
        "accounting_ref": None,
        "accounting_status": None,
        "idempotency_key": idem_key,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "issued_at": None,
        "cancelled_at": None,
        "error_message": None,
    }
    await db[COL].insert_one(doc)
    await _write_event(db, tenant_id, invoice_id, "invoice.created", created_by)
    return serialize_doc(doc)


# ── State Transitions ─────────────────────────────────────────────────

async def transition_invoice(
    tenant_id: str, invoice_id: str, target_status: str, actor: str = "",
) -> dict[str, Any]:
    """Transition invoice to a new state."""
    db = await get_db()
    doc = await db[COL].find_one({"tenant_id": tenant_id, "invoice_id": invoice_id})
    if not doc:
        return {"error": "Invoice not found"}

    current = doc["status"]
    try:
        validate_invoice_transition(current, target_status)
    except InvoiceStateError as e:
        return {"error": str(e)}

    now = now_utc()
    update: dict[str, Any] = {"status": target_status, "updated_at": now}

    if target_status == InvoiceStatus.ISSUED:
        update["issued_at"] = now
    elif target_status == InvoiceStatus.CANCELLED:
        update["cancelled_at"] = now
    elif target_status == InvoiceStatus.FAILED:
        update["error_message"] = "Issue failed"

    await db[COL].update_one({"_id": doc["_id"]}, {"$set": update})
    await _write_event(db, tenant_id, invoice_id, f"invoice.{target_status}", actor)

    updated = await db[COL].find_one({"_id": doc["_id"]})
    return serialize_doc(updated)


# ── Issue Invoice (via provider) ──────────────────────────────────────

async def issue_invoice(tenant_id: str, invoice_id: str, actor: str = "") -> dict[str, Any]:
    """Issue invoice through the e-document provider."""
    db = await get_db()
    doc = await db[COL].find_one({"tenant_id": tenant_id, "invoice_id": invoice_id})
    if not doc:
        return {"error": "Invoice not found"}

    current = doc["status"]
    if current not in (InvoiceStatus.DRAFT, InvoiceStatus.READY_FOR_ISSUE, InvoiceStatus.FAILED):
        return {"error": f"Cannot issue invoice in status '{current}'"}

    # Transition to issuing
    if current == InvoiceStatus.DRAFT:
        validate_invoice_transition(current, InvoiceStatus.READY_FOR_ISSUE)
        await db[COL].update_one({"_id": doc["_id"]}, {"$set": {"status": InvoiceStatus.READY_FOR_ISSUE, "updated_at": now_utc()}})

    validate_invoice_transition(
        InvoiceStatus.READY_FOR_ISSUE if current != InvoiceStatus.FAILED else InvoiceStatus.FAILED,
        InvoiceStatus.ISSUING if current != InvoiceStatus.FAILED else InvoiceStatus.READY_FOR_ISSUE,
    )

    await db[COL].update_one({"_id": doc["_id"]}, {"$set": {"status": InvoiceStatus.ISSUING, "updated_at": now_utc()}})
    await _write_event(db, tenant_id, invoice_id, "invoice.issuing", actor)

    provider = get_efatura_provider(doc.get("provider", "mock"))
    try:
        pid = doc.get("provider_invoice_id")
        if not pid:
            pid = await provider.create_invoice(serialize_doc(doc))

        status_result = await provider.send_invoice(pid)
        now = now_utc()

        if status_result == "sent":
            final_status = InvoiceStatus.ISSUED
        elif status_result == "rejected":
            final_status = InvoiceStatus.FAILED
        else:
            final_status = InvoiceStatus.ISSUED

        update = {
            "status": final_status,
            "provider_invoice_id": pid,
            "provider_status": status_result,
            "updated_at": now,
        }
        if final_status == InvoiceStatus.ISSUED:
            update["issued_at"] = now
        elif final_status == InvoiceStatus.FAILED:
            update["error_message"] = f"Provider returned: {status_result}"

        await db[COL].update_one({"_id": doc["_id"]}, {"$set": update})
        await _write_event(db, tenant_id, invoice_id, f"invoice.{final_status}", actor, {"provider_status": status_result})

        updated = await db[COL].find_one({"_id": doc["_id"]})
        return serialize_doc(updated)

    except Exception as e:
        await db[COL].update_one(
            {"_id": doc["_id"]},
            {"$set": {"status": InvoiceStatus.FAILED, "error_message": str(e), "updated_at": now_utc()}},
        )
        await _write_event(db, tenant_id, invoice_id, "invoice.failed", actor, {"error": str(e)})
        return {"error": str(e)}


# ── Cancel Invoice ────────────────────────────────────────────────────

async def cancel_invoice(tenant_id: str, invoice_id: str, actor: str = "", reason: str = "") -> dict[str, Any]:
    """Cancel an invoice."""
    db = await get_db()
    doc = await db[COL].find_one({"tenant_id": tenant_id, "invoice_id": invoice_id})
    if not doc:
        return {"error": "Invoice not found"}

    current = doc["status"]
    try:
        validate_invoice_transition(current, InvoiceStatus.CANCELLED)
    except InvoiceStateError:
        return {"error": f"Cannot cancel invoice in status '{current}'"}

    pid = doc.get("provider_invoice_id")
    if pid:
        provider = get_efatura_provider(doc.get("provider", "mock"))
        try:
            await provider.cancel_invoice(pid)
        except Exception:
            pass

    now = now_utc()
    await db[COL].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": InvoiceStatus.CANCELLED, "cancelled_at": now, "updated_at": now}},
    )
    await _write_event(db, tenant_id, invoice_id, "invoice.cancelled", actor, {"reason": reason})

    updated = await db[COL].find_one({"_id": doc["_id"]})
    return serialize_doc(updated)


# ── Read Operations ───────────────────────────────────────────────────

async def get_invoice(tenant_id: str, invoice_id: str) -> dict[str, Any] | None:
    db = await get_db()
    doc = await db[COL].find_one({"tenant_id": tenant_id, "invoice_id": invoice_id})
    return serialize_doc(doc) if doc else None


async def list_invoices(
    tenant_id: str,
    org_id: str,
    status: str | None = None,
    source_type: str | None = None,
    limit: int = 50,
    skip: int = 0,
) -> dict[str, Any]:
    db = await get_db()
    q: dict[str, Any] = {"organization_id": org_id}
    if tenant_id:
        q["tenant_id"] = tenant_id
    if status:
        q["status"] = status
    if source_type:
        q["source_type"] = source_type

    total = await db[COL].count_documents(q)
    cursor = db[COL].find(q).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {
        "items": [serialize_doc(d) for d in docs],
        "total": total,
        "limit": limit,
        "skip": skip,
    }


async def get_invoice_events(tenant_id: str, invoice_id: str) -> list[dict[str, Any]]:
    db = await get_db()
    cursor = db[EVENTS_COL].find(
        {"tenant_id": tenant_id, "invoice_id": invoice_id}
    ).sort("created_at", 1)
    docs = await cursor.to_list(length=200)
    return [serialize_doc(d) for d in docs]


async def get_booking_invoice(tenant_id: str, booking_id: str) -> dict[str, Any] | None:
    """Check if a booking already has an invoice."""
    db = await get_db()
    doc = await db[COL].find_one({"tenant_id": tenant_id, "booking_id": booking_id})
    return serialize_doc(doc) if doc else None


# ── Dashboard Stats ───────────────────────────────────────────────────

async def get_invoice_dashboard_stats(tenant_id: str, org_id: str) -> dict[str, Any]:
    """Get invoice dashboard stats."""
    db = await get_db()
    q: dict[str, Any] = {"organization_id": org_id}
    if tenant_id:
        q["tenant_id"] = tenant_id

    total = await db[COL].count_documents(q)
    draft_count = await db[COL].count_documents({**q, "status": InvoiceStatus.DRAFT})
    issued_count = await db[COL].count_documents({**q, "status": InvoiceStatus.ISSUED})
    failed_count = await db[COL].count_documents({**q, "status": InvoiceStatus.FAILED})
    cancelled_count = await db[COL].count_documents({**q, "status": InvoiceStatus.CANCELLED})

    pipeline = [
        {"$match": {**q, "status": {"$in": [InvoiceStatus.ISSUED, InvoiceStatus.SYNCED]}}},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$totals.grand_total"},
            "total_tax": {"$sum": "$totals.tax_total"},
            "total_subtotal": {"$sum": "$totals.subtotal"},
        }},
    ]
    agg = await db[COL].aggregate(pipeline).to_list(length=1)
    financials = agg[0] if agg else {"total_revenue": 0, "total_tax": 0, "total_subtotal": 0}
    financials.pop("_id", None)

    return {
        "total": total,
        "draft": draft_count,
        "issued": issued_count,
        "failed": failed_count,
        "cancelled": cancelled_count,
        "financials": financials,
    }
