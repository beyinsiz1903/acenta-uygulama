from __future__ import annotations

"""B2C post-payment side effects (booking confirmation + voucher + email).

This helper is intentionally small, idempotent and best-effort:
- NEVER breaks payment finalisation
- Can be safely called multiple times for the same booking
- Leaves audit-friendly traces via booking_events / inbox / email_outbox
"""

from typing import Any, Optional

from bson import ObjectId

from app.services.booking_lifecycle import BookingLifecycleService
from app.services.voucher_pdf import issue_voucher_pdf
from app.services.email_outbox import enqueue_booking_email
from app.services.vouchers import generate_for_booking
from app.utils.datetime import now_utc


async def run_b2c_post_payment_side_effects(db, *, booking_id: str) -> None:
    """Confirm public booking + issue voucher PDF + enqueue guest email.

    Design goals:
    - Idempotent: can be called multiple times safely
    - Best-effort: swallows all exceptions (should not break payment flow)
    - Scoped to B2C: only runs for bookings with source="public"
    """

    try:
        try:
            oid = ObjectId(booking_id)
        except Exception:
            # Non-ObjectId booking ids are not part of public checkout flow
            return

        booking = await db.bookings.find_one({"_id": oid})
        if not booking:
            return

        # Only act on public (B2C) bookings
        source = str(booking.get("source") or "").lower()
        if source != "public":
            return

        org_id = booking.get("organization_id")
        if not org_id:
            return

        # 1) Promote booking to CONFIRMED if not already in a final status
        lifecycle = BookingLifecycleService(db)
        current_status = booking.get("status")
        if current_status not in {"CONFIRMED", "CANCELLED"}:
            await lifecycle.append_event(
                organization_id=org_id,
                agency_id=str(booking.get("agency_id") or ""),
                booking_id=str(booking["_id"]),
                event="BOOKING_CONFIRMED",
                before={"status": current_status},
                after={"status": "CONFIRMED"},
            )

        # Reload booking to observe potential status change (optional, but safe)
        booking = await db.bookings.find_one({"_id": oid}) or booking

        # 2) Ensure there is an active voucher and persist a PDF rendition
        await generate_for_booking(
            db,
            organization_id=org_id,
            booking_id=booking_id,
            created_by_email="system_b2c_post_payment",
        )
        await issue_voucher_pdf(
            db,
            organization_id=org_id,
            booking_id=booking_id,
            issue_reason="INITIAL",  # type: ignore[arg-type]
            locale="tr",
            issued_by="system_b2c_post_payment",
        )

        # 3) Enqueue booking.confirmed email to guest (idempotent via simple dedupe)
        guest = booking.get("guest") or {}
        guest_email: Optional[str] = guest.get("email") or booking.get("guest_email")
        if not guest_email:
            return

        # Check for existing outbox job for this booking/event
        existing = await db.email_outbox.find_one(
            {
                "organization_id": org_id,
                "booking_id": booking["_id"],
                "event_type": "booking.confirmed",
            }
        )
        if existing:
            return

        await enqueue_booking_email(
            db,
            organization_id=org_id,
            booking=booking,
            event_type="booking.confirmed",
            to_addresses=[guest_email],
        )
    except Exception:
        # Hard safety net: NEVER let side-effect failures bubble up to callers.
        # Detailed logging is handled inside the underlying services.
        return
