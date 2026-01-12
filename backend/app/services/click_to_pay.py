from __future__ import annotations

"""Click-to-Pay helpers.

This module encapsulates the persistence and token resolution logic for
ops-initiated "click-to-pay" payment links. It deliberately mirrors the
public_my_booking token model:

- random opaque token returned to caller
- sha256(token) stored as token_hash in DB
- TTL enforced via expires_at and a Mongo TTL index

The actual Stripe PaymentIntent is created by callers using the existing
stripe_adapter, with capture_method="automatic" and metadata that ties the
intent back to a booking + organization.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import hashlib

from app.utils import now_utc
from app.errors import AppError


CLICK_TO_PAY_TTL_HOURS = 24


@dataclass
class PaymentLink:
    token: str
    token_hash: str
    expires_at: datetime
    organization_id: str
    booking_id: str
    payment_intent_id: str
    amount_cents: int
    currency: str


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def create_payment_link(
    db,
    *,
    organization_id: str,
    booking_id: str,
    payment_intent_id: str,
    amount_cents: int,
    currency: str,
    actor_email: Optional[str] = None,
) -> PaymentLink:
    """Create a new click-to-pay link and persist it.

    - Generates a random token (returned to caller)
    - Stores only token_hash in DB
    - TTL is 24h via expires_at; a Mongo TTL index must be configured
    separately.
    """

    from secrets import token_urlsafe

    if amount_cents <= 0:
        raise AppError(422, "click_to_pay_invalid_amount", "Click-to-pay amount must be > 0")

    token = f"ctp_{token_urlsafe(24)}"
    token_hash = _hash_token(token)
    now = now_utc()
    expires_at = now + timedelta(hours=CLICK_TO_PAY_TTL_HOURS)

    doc: Dict[str, Any] = {
        "token_hash": token_hash,
        "expires_at": expires_at,
        "organization_id": organization_id,
        "booking_id": booking_id,
        "payment_intent_id": payment_intent_id,
        "amount_cents": int(amount_cents),
        "currency": currency.lower(),
        "status": "active",
        "telemetry": {
            "access_count": 0,
            "last_access_at": None,
            "last_ip": None,
            "last_ua": None,
        },
        "created_at": now,
        "created_by": actor_email,
    }

    await db.click_to_pay_links.insert_one(doc)

    return PaymentLink(
        token=token,
        token_hash=token_hash,
        expires_at=expires_at,
        organization_id=organization_id,
        booking_id=booking_id,
        payment_intent_id=payment_intent_id,
        amount_cents=int(amount_cents),
        currency=currency.lower(),
    )


async def resolve_payment_link(db, token: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve a raw token to (link_doc, booking_doc).

    Rules:
    - Look up by token_hash and expires_at > now
    - If no document is found or booking is missing, raise 404 AppError
    - On success, update basic telemetry counters (best-effort)
    """

    from bson import ObjectId

    now = now_utc()
    token_hash = _hash_token(token)

    link = await db.click_to_pay_links.find_one(
        {"token_hash": token_hash, "expires_at": {"$gt": now}},
    )
    if not link:
        raise AppError(404, "CLICK_TO_PAY_TOKEN_NOT_FOUND", "Payment link not found or expired")

    booking_id = link.get("booking_id")
    if not booking_id:
        raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found for payment link")

    booking = await db.bookings.find_one({"_id": booking_id})
    if not booking:
        try:
            oid = ObjectId(booking_id)
        except Exception:
            oid = None
        if oid is not None:
            booking = await db.bookings.find_one({"_id": oid})

    if not booking:
        raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found for payment link")

    # Telemetry best-effort update
    try:
        telemetry = link.get("telemetry") or {}
        telemetry.update(
            {
                "access_count": int(telemetry.get("access_count", 0)) + 1,
                "last_access_at": now,
            }
        )
        await db.click_to_pay_links.update_one(
            {"_id": link["_id"]},
            {"$set": {"telemetry": telemetry}},
        )
    except Exception:
        pass

    return link, booking
