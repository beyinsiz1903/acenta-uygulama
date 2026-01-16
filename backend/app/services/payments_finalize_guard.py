from __future__ import annotations

"""Finalize guard for Stripe webhook events.

Single source-of-truth for booking-level payment finalisation with
idempotency + out-of-order protection.

This module is intentionally Stripe-specific for now and focused on
booking.payment_status so it can sit on top of existing booking_payments
/ ledger orchestration.
"""

from typing import Any, Dict, Optional

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.utils import now_utc


def _extract_payment_intent_id(event: Dict[str, Any]) -> Optional[str]:
    data = event.get("data", {}) or {}
    obj = data.get("object") or {}
    # If event is PaymentIntent.* -> object.id is the PI id
    pi_id = obj.get("id")
    if pi_id and (obj.get("object") == "payment_intent" or obj.get("object") is None):
        return str(pi_id)
    # If event is charge.* -> object.payment_intent holds the PI id
    pi_from_charge = obj.get("payment_intent")
    if pi_from_charge:
        return str(pi_from_charge)
    return None


async def _resolve_booking_by_payment_intent(db, payment_intent_id: str) -> Optional[Dict[str, Any]]:
    if not payment_intent_id:
        return None

    # 1) Direct lookup on bookings by payment_intent_id (public checkout flow)
    booking = await db.bookings.find_one({"payment_intent_id": payment_intent_id})
    if booking:
        return booking

    # 2) Fallback via public_checkouts registry (idempotency record)
    checkout = await db.public_checkouts.find_one({"payment_intent_id": payment_intent_id})
    if checkout and checkout.get("booking_id"):
        try:
            bid = ObjectId(str(checkout["booking_id"]))
        except Exception:
            return None
        booking = await db.bookings.find_one({"_id": bid})
        return booking

    return None


async def apply_stripe_event_with_guard(
    db,
    *,
    event: Dict[str, Any],
    now=None,
    logger=None,
) -> Dict[str, Any]:
    """Apply a Stripe webhook event with booking-level finalisation guard.

    Returns a small dict:
    {"ok": bool, "decision": str, "reason": str|None, "booking_id": str|None, "event_id": str}
    """

    if now is None:
        now = now_utc()

    provider = "stripe"
    event_id = str(event.get("id")) if event.get("id") is not None else ""
    event_type = str(event.get("type") or "")

    pi_id = _extract_payment_intent_id(event)

    coll = db.payment_finalizations

    base_doc: Dict[str, Any] = {
        "provider": provider,
        "event_id": event_id,
        "payment_intent_id": pi_id,
        "kind": event_type,
        "decision": "processing",
        "reason": None,
        "created_at": now,
        "applied_at": None,
    }

    # 1) Event-level dedupe via (provider, event_id) unique index
    try:
        await coll.insert_one(base_doc)
    except DuplicateKeyError:
        # Already processed this exact event id
        return {
            "ok": True,
            "decision": "ignored_duplicate",
            "reason": "event_id_seen",
            "booking_id": None,
            "event_id": event_id,
        }

    # Helper to persist decision/reason/booking context
    async def _finalise(decision: str, reason: Optional[str], booking: Optional[Dict[str, Any]] = None):
        update: Dict[str, Any] = {
            "decision": decision,
            "reason": reason,
        }
        if booking:
            update["booking_id"] = str(booking.get("_id"))
            update["organization_id"] = booking.get("organization_id")
        if decision == "applied":
            update["applied_at"] = now

        await coll.update_one(
            {"provider": provider, "event_id": event_id},
            {"$set": update},
        )
        return {
            "ok": decision == "applied",
            "decision": decision,
            "reason": reason,
            "booking_id": str(booking.get("_id")) if booking else None,
            "event_id": event_id,
        }

    # 2) Resolve booking from PI
    booking = await _resolve_booking_by_payment_intent(db, pi_id) if pi_id else None
    if not booking:
        return await _finalise("error", "missing_booking", None)

    org_id = booking.get("organization_id")

    # 3) Final-state guard: already paid/refunded/voided or hard-confirmed bookings
    final_payment_statuses = {"paid", "refunded", "voided"}
    final_booking_statuses = {"CONFIRMED", "CANCELLED"}
    if str(booking.get("payment_status") or "").lower() in final_payment_statuses or booking.get("status") in final_booking_statuses:
        return await _finalise("ignored_duplicate", "already_finalized", booking)

    # 4) Map event type to target payment_status
    target_status: Optional[str] = None
    if event_type == "payment_intent.succeeded":
        target_status = "paid"
    elif event_type == "payment_intent.payment_failed":
        target_status = "failed"
    else:
        # Non-final events are simply logged as ignored
        return await _finalise("ignored_not_final", f"unsupported_event_type:{event_type}", booking)

    # 5) CAS update on booking.payment_status to protect against out-of-order events
    
    # Accept transitions only from pending/None -> final state
    current_status = str(booking.get("payment_status") or "").lower() or None
    allowed_previous = {None, "", "pending"}

    filter_doc = {
        "_id": booking["_id"],
        "organization_id": org_id,
        "$or": [
            {"payment_status": {"$exists": False}},
            {"payment_status": {"$in": list(allowed_previous)}},
        ],
    }

    update_doc: Dict[str, Any] = {
        "$set": {
            "payment_status": target_status,
            "updated_at": now,
        }
    }
    if target_status == "paid":
        update_doc["$set"]["paid_at"] = now

    res = await db.bookings.update_one(filter_doc, update_doc)

    if res.modified_count == 0:
        # Another event already moved this booking to a final state
        return await _finalise("ignored_out_of_order", "status_mismatch", booking)

    # 6) Success path
    return await _finalise("applied", None, booking)
