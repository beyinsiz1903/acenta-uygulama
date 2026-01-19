from __future__ import annotations

import pytest
from bson import ObjectId

from app.services.b2c_post_payment import run_b2c_post_payment_side_effects
from app.utils import now_utc


@pytest.mark.anyio
async def test_b2c_post_payment_side_effects_creates_voucher_and_email_once(test_db, monkeypatch):
    """Public (B2C) booking: helper should confirm, issue voucher PDF and enqueue email exactly once.

    This is a pure integration test against the helper + existing voucher/email services,
    without going through the Stripe webhook stack.
    """

    db = test_db
    org_id = "org_public_b2c_side"

    # Seed minimal public booking with guest email
    booking_id = ObjectId()
    booking_doc = {
        "_id": booking_id,
        "organization_id": org_id,
        "source": "public",
        "status": "PENDING_PAYMENT",
        "guest": {"full_name": "B2C Guest", "email": "b2c@example.com"},
        "currency": "EUR",
        "amounts": {"sell": 100.0},
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    await db.bookings.insert_one(booking_doc)

    # Minimal voucher template so PDF rendering has something to use
    await db.voucher_templates.insert_one(
        {
            "organization_id": org_id,
            "key": "b2c_booking_default",
            "name": "B2C Booking Template",
            "html": "<html><body><h1>Voucher for {{booking_id}}</h1></body></html>",
            "created_at": now_utc(),
        }
    )

    # First run: should confirm booking, create voucher PDF and enqueue email
    await run_b2c_post_payment_side_effects(db, booking_id=str(booking_id))

    # Booking should be CONFIRMED
    updated = await db.bookings.find_one({"_id": booking_id})
    assert updated is not None
    assert updated.get("status") == "CONFIRMED"

    # There should be at least one active voucher record (HTML-level)
    voucher_docs = await db.vouchers.find({"organization_id": org_id, "booking_id": str(booking_id)}).to_list(10)
    assert len(voucher_docs) == 1

    # There should be exactly one email_outbox job for booking.confirmed
    outbox_docs = await db.email_outbox.find(
        {"organization_id": org_id, "booking_id": booking_id, "event_type": "booking.confirmed"}
    ).to_list(10)
    assert len(outbox_docs) == 1

    # Second run must be idempotent: no extra PDFs or emails
    await run_b2c_post_payment_side_effects(db, booking_id=str(booking_id))

    pdf_docs2 = await db.files_vouchers.find({"organization_id": org_id, "booking_id": str(booking_id)}).to_list(10)
    assert len(pdf_docs2) == 1

    outbox_docs2 = await db.email_outbox.find(
        {"organization_id": org_id, "booking_id": booking_id, "event_type": "booking.confirmed"}
    ).to_list(10)
    assert len(outbox_docs2) == 1
