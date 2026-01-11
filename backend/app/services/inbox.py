from __future__ import annotations

"""Inbox / notification center service (FAZ 4).

Provides helpers to:
- Create or reuse booking-level inbox threads
- Append SYSTEM messages for key booking events
- Append USER messages from UI
"""

from typing import Any, Dict, Optional

from bson import ObjectId

from app.utils import now_utc
from app.errors import AppError


async def get_or_create_booking_thread(db, *, organization_id: str, booking: dict[str, Any]) -> dict[str, Any]:
    """Return existing BOOKING thread for a booking or create a new one.

    Threads are per (organization_id, booking_id, type="BOOKING").
    """

    booking_id = str(booking["_id"])

    existing = await db.inbox_threads.find_one(
        {
            "organization_id": organization_id,
            "type": "BOOKING",
            "booking_id": booking_id,
        }
    )
    if existing:
        return existing

    now = now_utc()
    subject = f"{booking.get('code') or booking_id} – {booking.get('hotel_name') or 'Booking'}"

    participants: list[dict[str, Any]] = []
    if booking.get("agency_id"):
        participants.append({"type": "AGENCY", "id": str(booking["agency_id"])})
    if booking.get("hotel_id"):
        participants.append({"type": "HOTEL", "id": str(booking["hotel_id"])})

    doc = {
        "organization_id": organization_id,
        "type": "BOOKING",
        "booking_id": booking_id,
        "subject": subject,
        "participants": participants,
        "status": "OPEN",
        "last_message_at": now,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.inbox_threads.insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


def _build_system_body_for_event(event_type: str, meta: Dict[str, Any]) -> str:
    et = event_type
    amount = meta.get("amount_cents") or meta.get("amount_minor") or meta.get("amount")
    currency = meta.get("currency") or ""

    if et == "BOOKING_CONFIRMED":
        return "Rezervasyon onaylandı."
    if et == "PAYMENT_CAPTURED":
        if amount is not None:
            return f"Ödeme alındı: {amount/100:.2f} {currency}".strip()
        return "Ödeme alındı."
    if et == "PAYMENT_REFUNDED":
        if amount is not None:
            return f"Ödeme iade edildi: {amount/100:.2f} {currency}".strip()
        return "Ödeme iade edildi."
    if et == "VOUCHER_ISSUED":
        return "Voucher oluşturuldu."
    if et == "GUEST_REQUEST_CANCEL":
        reason = meta.get("reason") or ""
        return f"Misafir iptal talebi gönderdi. {reason}".strip()
    if et == "GUEST_REQUEST_AMEND":
        return "Misafir tarih değişikliği talebi gönderdi."

    return et


async def append_system_message_for_event(
    db,
    *,
    organization_id: str,
    booking_id: str,
    event_type: str,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a SYSTEM message in inbox for a booking event.

    Best-effort: failures are logged but do not break main flow.
    """

    from logging import getLogger

    logger = getLogger("inbox")
    meta = meta or {}

    try:
        booking = await db.bookings.find_one({
            "_id": ObjectId(booking_id),
            "organization_id": organization_id,
        })
        if not booking:
            return

        thread = await get_or_create_booking_thread(db, organization_id=organization_id, booking=booking)

        body = _build_system_body_for_event(event_type, meta)
        now = now_utc()

        msg_doc = {
            "organization_id": organization_id,
            "thread_id": thread["_id"],
            "sender_type": "SYSTEM",
            "sender_id": None,
            "sender_email": None,
            "body": body,
            "attachments": [],
            "event_type": event_type,
            "created_at": now,
        }

        await db.inbox_messages.insert_one(msg_doc)

        await db.inbox_threads.update_one(
            {"_id": thread["_id"]},
            {"$set": {"last_message_at": now, "updated_at": now}},
        )
    except Exception:
        logger.exception(
            "append_system_message_for_event_failed",
            extra={"organization_id": organization_id, "booking_id": booking_id, "event_type": event_type},
        )


async def append_user_message(
    db,
    *,
    organization_id: str,
    thread_id: str,
    user: Dict[str, Any],
    body: str,
) -> Dict[str, Any]:
    """Append a USER message to a thread.

    Returns the inserted message doc (with id as string).
    """

    try:
        oid = ObjectId(thread_id)
    except Exception:
        raise AppError(404, "THREAD_NOT_FOUND", "Thread not found", {"thread_id": thread_id})

    thread = await db.inbox_threads.find_one({"_id": oid, "organization_id": organization_id})
    if not thread:
        raise AppError(404, "THREAD_NOT_FOUND", "Thread not found", {"thread_id": thread_id})

    now = now_utc()

    msg_doc: Dict[str, Any] = {
        "organization_id": organization_id,
        "thread_id": oid,
        "sender_type": "USER",
        "sender_id": str(user.get("id") or user.get("_id") or ""),
        "sender_email": user.get("email"),
        "body": body,
        "attachments": [],
        "event_type": None,
        "created_at": now,
    }

    res = await db.inbox_messages.insert_one(msg_doc)
    msg_doc["_id"] = res.inserted_id

    await db.inbox_threads.update_one(
        {"_id": oid},
        {"$set": {"last_message_at": now, "updated_at": now}},
    )

    msg_doc["id"] = str(msg_doc.pop("_id"))
    return msg_doc
