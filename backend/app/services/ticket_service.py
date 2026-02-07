"""QR Ticket + Check-in service (C).

Generates tickets with unique codes, QR data, and handles check-in.
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Any, Dict, List, Optional

from app.db import get_db
from app.utils import now_utc, serialize_doc


def _generate_ticket_code() -> str:
    """Generate a short, unique ticket code."""
    raw = uuid.uuid4().hex[:10].upper()
    return f"TKT-{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def _generate_qr_data(ticket_code: str, tenant_id: str) -> str:
    """Generate QR code data string."""
    return f"TICKET:{tenant_id}:{ticket_code}"


async def create_ticket(
    tenant_id: str,
    org_id: str,
    reservation_id: str,
    product_name: str,
    customer_name: str,
    customer_email: str = "",
    customer_phone: str = "",
    event_date: str = "",
    seat_info: str = "",
    notes: str = "",
    created_by: str = "",
) -> Dict[str, Any]:
    db = await get_db()
    now = now_utc()

    # Idempotency: one ticket per reservation
    existing = await db.tickets.find_one({
        "tenant_id": tenant_id,
        "reservation_id": reservation_id,
    })
    if existing:
        return serialize_doc(existing)

    ticket_code = _generate_ticket_code()
    qr_data = _generate_qr_data(ticket_code, tenant_id)

    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "reservation_id": reservation_id,
        "ticket_code": ticket_code,
        "qr_data": qr_data,
        "product_name": product_name,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "event_date": event_date,
        "seat_info": seat_info,
        "notes": notes,
        "status": "active",  # active | checked_in | canceled | expired
        "checked_in_at": None,
        "checked_in_by": None,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await db.tickets.insert_one(doc)
    return serialize_doc(doc)


async def check_in_ticket(
    tenant_id: str,
    ticket_code: str,
    checked_in_by: str = "",
) -> Dict[str, Any]:
    db = await get_db()
    now = now_utc()

    ticket = await db.tickets.find_one({
        "tenant_id": tenant_id,
        "ticket_code": ticket_code,
    })
    if not ticket:
        return {"error": "Ticket not found", "code": "not_found"}

    if ticket["status"] == "checked_in":
        return {
            "error": "Ticket already checked in",
            "code": "already_checked_in",
            "checked_in_at": serialize_doc(ticket.get("checked_in_at")),
        }
    if ticket["status"] == "canceled":
        return {"error": "Ticket is canceled", "code": "canceled"}
    if ticket["status"] == "expired":
        return {"error": "Ticket is expired", "code": "expired"}

    await db.tickets.update_one(
        {"_id": ticket["_id"]},
        {"$set": {
            "status": "checked_in",
            "checked_in_at": now,
            "checked_in_by": checked_in_by,
            "updated_at": now,
        }},
    )

    ticket["status"] = "checked_in"
    ticket["checked_in_at"] = now
    ticket["checked_in_by"] = checked_in_by
    return {"success": True, "ticket": serialize_doc(ticket)}


async def cancel_ticket(tenant_id: str, ticket_code: str) -> Dict[str, Any]:
    db = await get_db()
    result = await db.tickets.find_one_and_update(
        {"tenant_id": tenant_id, "ticket_code": ticket_code, "status": "active"},
        {"$set": {"status": "canceled", "updated_at": now_utc()}},
        return_document=True,
    )
    if not result:
        return {"error": "Ticket not found or not active"}
    return serialize_doc(result)


async def get_ticket_by_code(tenant_id: str, ticket_code: str) -> Optional[Dict]:
    db = await get_db()
    doc = await db.tickets.find_one({"tenant_id": tenant_id, "ticket_code": ticket_code})
    return serialize_doc(doc) if doc else None


async def list_tickets(
    org_id: str,
    tenant_id: str = None,
    status: str = None,
    reservation_id: str = None,
    limit: int = 50,
) -> List[Dict]:
    db = await get_db()
    q: Dict[str, Any] = {"organization_id": org_id}
    if tenant_id:
        q["tenant_id"] = tenant_id
    if status:
        q["status"] = status
    if reservation_id:
        q["reservation_id"] = reservation_id
    cursor = db.tickets.find(q).sort("created_at", -1).limit(limit)
    return [serialize_doc(d) for d in await cursor.to_list(length=limit)]


async def get_checkin_stats(org_id: str, tenant_id: str = None) -> Dict[str, int]:
    db = await get_db()
    q: Dict[str, Any] = {"organization_id": org_id}
    if tenant_id:
        q["tenant_id"] = tenant_id
    total = await db.tickets.count_documents(q)
    checked = await db.tickets.count_documents({**q, "status": "checked_in"})
    active = await db.tickets.count_documents({**q, "status": "active"})
    canceled = await db.tickets.count_documents({**q, "status": "canceled"})
    return {"total": total, "checked_in": checked, "active": active, "canceled": canceled}
