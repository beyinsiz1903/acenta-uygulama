from __future__ import annotations

import json

import pytest

from app.utils import now_utc


@pytest.mark.anyio
async def test_stripe_webhook_triggers_b2c_side_effects_for_public_booking(async_client, test_db, monkeypatch):
    """payment_intent.succeeded with public booking metadata triggers B2C side effects.

    We assert that:
    - booking status is moved to CONFIRMED/VOUCHERED
    - a voucher document exists
    - a booking.confirmed email_outbox job is enqueued
    """

    db = test_db
    org_id = "org_public_webhook"

    # Seed a public booking with pending payment
    booking_doc = {
        "organization_id": org_id,
        "source": "public",
        "status": "PENDING_PAYMENT",
        "guest": {"full_name": "Webhook Guest", "email": "webhook@example.com"},
        "currency": "EUR",
        "amounts": {"sell": 100.0},
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    res = await db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    # Minimal voucher template so vouchers service can render HTML
    await db.voucher_templates.insert_one(
        {
            "organization_id": org_id,
            "key": "b2b_booking_default",
            "name": "B2C Booking Template",
            "html": "<html><body><h1>Voucher for {booking_id}</h1></body></html>",
            "status": "active",
            "created_at": now_utc(),
        }
    )

    # Monkeypatch verify_and_parse_stripe_event to bypass real Stripe signature
    from app.services import stripe_handlers as handlers

    event_payload = {
        "id": "evt_test_b2c",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_b2c",
                "amount_received": 10000,
                "currency": "eur",
                "metadata": {
                    "booking_id": booking_id,
                    "organization_id": org_id,
                    "agency_id": "agency_public",
                    "payment_id": "pay_test_b2c",
                    "channel": "public",
                },
            }
        },
    }

    async def fake_verify_and_parse(raw_body: bytes, signature: str | None):  # type: ignore[unused-argument]
        return event_payload

    async def fake_apply_stripe_event_with_guard(db, event, now, logger=None):  # type: ignore[unused-argument]
        # Simulate a successful payment finalisation for this booking
        return {
            "ok": True,
            "decision": "applied",
            "reason": None,
            "booking_id": booking_id,
            "event_id": event_payload["id"],
        }

    monkeypatch.setattr(handlers, "verify_and_parse_stripe_event", fake_verify_and_parse)
    monkeypatch.setattr(handlers, "apply_stripe_event_with_guard", fake_apply_stripe_event_with_guard)

    # Call handler directly (router mounting differs in tests)
    status, body = await handlers.handle_stripe_webhook(b"{}", "dummy-signature")

    assert status == 200
    assert body.get("ok") is True

    # Booking should now be at least CONFIRMED/VOUCHERED
    updated = await db.bookings.find_one({"_id": res.inserted_id})
    assert updated is not None
    assert updated.get("status") in {"CONFIRMED", "VOUCHERED"}

    # Voucher should exist
    vouchers = await db.vouchers.find({"organization_id": org_id, "booking_id": booking_id}).to_list(10)
    assert len(vouchers) == 1

    # Email outbox job should exist (booking.confirmed)
    outbox = await db.email_outbox.find(
        {"organization_id": org_id, "booking_id": res.inserted_id, "event_type": "booking.confirmed"}
    ).to_list(10)
    assert len(outbox) == 1


@pytest.mark.anyio
async def test_stripe_webhook_does_not_trigger_side_effects_for_non_public(async_client, test_db, monkeypatch):
    """Non-public booking should not trigger B2C side effects even on succeeded PI."""

    db = test_db
    org_id = "org_non_public_webhook"

    booking_doc = {
        "organization_id": org_id,
        "source": "b2b",
        "status": "PENDING_PAYMENT",
        "guest": {"full_name": "B2B Guest", "email": "b2b@example.com"},
        "currency": "EUR",
        "amounts": {"sell": 200.0},
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    res = await db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    # voucher template
    await db.voucher_templates.insert_one(
        {
            "organization_id": org_id,
            "key": "b2b_booking_default",
            "name": "B2B Booking Template",
            "html": "<html><body><h1>Voucher for {booking_id}</h1></body></html>",
            "status": "active",
            "created_at": now_utc(),
        }
    )

    from app.services import stripe_handlers as handlers

    event_payload = {
        "id": "evt_test_b2b",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_b2b",
                "amount_received": 20000,
                "currency": "eur",
                "metadata": {
                    "booking_id": booking_id,
                    "organization_id": org_id,
                    "agency_id": "agency_b2b",
                    "payment_id": "pay_test_b2b",
                    "channel": "b2b",
                },
            }
        },
    }

    async def fake_verify_and_parse(raw_body: bytes, signature: str | None):  # type: ignore[unused-argument]
        return event_payload

    async def fake_apply_stripe_event_with_guard(db, event, now, logger=None):  # type: ignore[unused-argument]
        # Simulate a successful payment finalisation for this booking
        return {
            "ok": True,
            "decision": "applied",
            "reason": None,
            "booking_id": booking_id,
            "event_id": event_payload["id"],
        }

    monkeypatch.setattr(handlers, "verify_and_parse_stripe_event", fake_verify_and_parse)
    monkeypatch.setattr(handlers, "apply_stripe_event_with_guard", fake_apply_stripe_event_with_guard)

    # Call handler directly
    status, body = await handlers.handle_stripe_webhook(b"{}", "dummy-signature")

    assert status == 200
    assert body.get("ok") is True

    # Booking should not have B2C voucher/email side effects
    vouchers = await db.vouchers.find({"organization_id": org_id, "booking_id": booking_id}).to_list(10)
    assert vouchers == []

    outbox = await db.email_outbox.find(
        {"organization_id": org_id, "booking_id": res.inserted_id, "event_type": "booking.confirmed"}
    ).to_list(10)
    assert outbox == []
