from __future__ import annotations

import json
from typing import Dict, Any

import pytest

from app.services.booking_payments import BookingPaymentsOrchestrator
from app.db import get_db


@pytest.mark.anyio
async def test_stripe_webhook_rejects_invalid_signature(async_client):
    """Webhook must return 400 when Stripe signature is invalid.

    This proves we are actually verifying the signature instead of trusting payloads.
    """

    # Payload shape roughly matching a payment_intent.succeeded event
    fake_event: Dict[str, Any] = {
        "id": "evt_test_invalid_sig",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_test_1"}},
    }

    resp = await async_client.post(
        "/api/payments/stripe/webhook",
        content=json.dumps(fake_event),
        headers={"Stripe-Signature": "totally-invalid"},
    )

    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "stripe_invalid_signature"


@pytest.mark.anyio
async def test_payment_intent_succeeded_currency_mismatch_returns_500(monkeypatch, async_client, test_db, admin_headers):
    """If webhook currency != booking currency (EUR-only policy), we must 500.

    This forces Stripe to retry while we investigate, instead of silently 200-ing.
    """

    # Create a dummy booking + aggregate in EUR so orchestrator has something to work with
    db = test_db
    orchestrator = BookingPaymentsOrchestrator(db)
    booking_id = "bkg_stripe_1"
    org_id = "org_demo"
    agency_id = "agency_demo"
    payment_id = "pay_demo_1"

    # Create aggregate with EUR
    await orchestrator._aggregates.get_or_create_aggregate(
        organization_id=org_id,
        agency_id=agency_id,
        booking_id=booking_id,
        currency="EUR",
        total_cents=11_000,
    )

    # Fake Stripe event with non-EUR currency
    event_payload = {
        "id": "evt_test_currency_mismatch",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_currency",
                "amount_received": 11_000,
                "currency": "usd",
                "metadata": {
                    "booking_id": booking_id,
                    "organization_id": org_id,
                    "agency_id": agency_id,
                    "payment_id": payment_id,
                },
            }
        },
    }

    # Monkeypatch Stripe signature verification to bypass crypto and just return the event
    from app.services import stripe_handlers as handlers  # type: ignore

    async def fake_construct_event(*args, **kwargs):  # pragma: no cover - simple shim
        return event_payload

    # Monkeypatch get_db to return test_db
    async def fake_get_db():
        return test_db

    monkeypatch.setattr(handlers, "verify_and_parse_stripe_event", fake_construct_event)
    monkeypatch.setattr(handlers, "get_db", fake_get_db)

    resp = await async_client.post(
        "/api/payments/stripe/webhook",
        content=json.dumps(event_payload),
        headers={"Stripe-Signature": "valid-for-test"},
    )

    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "stripe_currency_mismatch"


@pytest.mark.anyio
async def test_payment_intent_succeeded_idempotent_on_provider_ids(monkeypatch, async_client, test_db):
    """Two identical payment_intent.succeeded events (same ids) must be idempotent.

    First call should create a booking_payment_transactions row + aggregates;
    second call must be a no-op (still 200) and not duplicate tx.
    """

    db = test_db
    orchestrator = BookingPaymentsOrchestrator(db)
    booking_id = "bkg_stripe_2"
    org_id = "org_demo"
    agency_id = "agency_demo"
    payment_id = "pay_demo_2"

    await orchestrator._aggregates.get_or_create_aggregate(
        organization_id=org_id,
        agency_id=agency_id,
        booking_id=booking_id,
        currency="EUR",
        total_cents=22_000,
    )

    event_id = "evt_pi_idem"
    pi_id = "pi_idem_1"

    event_payload = {
        "id": event_id,
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": pi_id,
                "amount_received": 22_000,
                "currency": "eur",
                "metadata": {
                    "booking_id": booking_id,
                    "organization_id": org_id,
                    "agency_id": agency_id,
                    "payment_id": payment_id,
                },
            }
        },
    }

    from app.services import stripe_handlers as handlers  # type: ignore

    async def fake_construct_event(*args, **kwargs):  # pragma: no cover
        return event_payload

    monkeypatch.setattr(handlers, "verify_and_parse_stripe_event", fake_construct_event)

    # 1st delivery
    resp1 = await async_client.post(
        "/api/payments/stripe/webhook",
        content=json.dumps(event_payload),
        headers={"Stripe-Signature": "valid-for-test"},
    )
    assert resp1.status_code == 200

    # 2nd delivery (replay)
    resp2 = await async_client.post(
        "/api/payments/stripe/webhook",
        content=json.dumps(event_payload),
        headers={"Stripe-Signature": "valid-for-test"},
    )
    assert resp2.status_code == 200

    # Ensure we only inserted a single tx for this provider_object_id
    tx_docs = await test_db.booking_payment_transactions.find({"provider_object_id": pi_id}).to_list(10)
    assert len(tx_docs) == 1


@pytest.mark.anyio
async def test_charge_refunded_idempotent_on_refund_id(monkeypatch, async_client, test_db):
    """Two charge.refunded events with same refund id must be idempotent.

    booking_payment_transactions has a unique constraint on provider_event_id /
    provider_object_id, so duplicate events must not double-apply refund.
    """

    db = test_db
    orchestrator = BookingPaymentsOrchestrator(db)
    booking_id = "bkg_stripe_3"
    org_id = "org_demo"
    agency_id = "agency_demo"
    payment_id = "pay_demo_3"

    # Start with a fully paid booking (simulate previous capture)
    await orchestrator._aggregates.get_or_create_aggregate(
        organization_id=org_id,
        agency_id=agency_id,
        booking_id=booking_id,
        currency="EUR",
        total_cents=33_000,
    )
    await orchestrator._aggregates.apply_capture_succeeded(
        organization_id=org_id,
        agency_id=agency_id,
        booking_id=booking_id,
        payment_id=payment_id,
        amount_cents=33_000,
    )

    event_id = "evt_refund_idem"
    refund_id = "re_idem_1"

    event_payload = {
        "id": event_id,
        "type": "charge.refunded",
        "data": {
            "object": {
                "id": "ch_1",  # charge id (not used for idempotency in our design)
                "amount_refunded": 33_000,
                "currency": "eur",
                "payment_intent": "pi_for_refund",
                "refunds": {
                    "data": [
                        {
                            "id": refund_id,
                            "amount": 33_000,
                            "currency": "eur",
                        }
                    ]
                },
                "metadata": {
                    "booking_id": booking_id,
                    "organization_id": org_id,
                    "agency_id": agency_id,
                    "payment_id": payment_id,
                },
            }
        },
    }

    from app.services import stripe_handlers as handlers  # type: ignore

    async def fake_construct_event(*args, **kwargs):  # pragma: no cover
        return event_payload

    monkeypatch.setattr(handlers, "verify_and_parse_stripe_event", fake_construct_event)

    # 1st delivery
    resp1 = await async_client.post(
        "/api/payments/stripe/webhook",
        content=json.dumps(event_payload),
        headers={"Stripe-Signature": "valid-for-test"},
    )
    assert resp1.status_code == 200

    # 2nd delivery (replay)
    resp2 = await async_client.post(
        "/api/payments/stripe/webhook",
        content=json.dumps(event_payload),
        headers={"Stripe-Signature": "valid-for-test"},
    )
    assert resp2.status_code == 200

    # Ensure only one tx (per refund id)
    tx_docs = await test_db.booking_payment_transactions.find({"provider_object_id": refund_id}).to_list(10)
    assert len(tx_docs) == 1


@pytest.mark.anyio
async def test_capture_and_refund_endpoints_set_idempotency_keys(monkeypatch, async_client, admin_headers):
    """/create-intent and /capture must pass Idempotency-Key to Stripe adapter.

    We don't hit real Stripe here; we assert our adapter is called with the
    expected idempotency key derived from the HTTP layer.
    """

    called: Dict[str, Any] = {}

    from app.services import stripe_adapter as adapter  # type: ignore

    async def fake_create_intent(*, amount_cents: int, currency: str, metadata: Dict[str, str], idempotency_key: str) -> Dict[str, Any]:  # pragma: no cover
        called["create"] = {
            "amount_cents": amount_cents,
            "currency": currency,
            "metadata": metadata,
            "idempotency_key": idempotency_key,
        }
        return {"id": "pi_fake", "amount": amount_cents, "currency": currency, "metadata": metadata}

    async def fake_capture_intent(*, payment_intent_id: str, idempotency_key: str) -> Dict[str, Any]:  # pragma: no cover
        called["capture"] = {
            "payment_intent_id": payment_intent_id,
            "idempotency_key": idempotency_key,
        }
        return {"id": payment_intent_id, "status": "succeeded"}

    monkeypatch.setattr(adapter, "create_payment_intent", fake_create_intent)
    monkeypatch.setattr(adapter, "capture_payment_intent", fake_capture_intent)

    idem_key_create = "idem-create-123"
    idem_key_capture = "idem-capture-456"

    # Create intent endpoint
    resp1 = await async_client.post(
        "/api/payments/stripe/create-intent",
        headers={**admin_headers, "Idempotency-Key": idem_key_create},
        json={
            "booking_id": "bkg_ui_1",
            "amount_cents": 44_000,
            "currency": "EUR",
        },
    )
    assert resp1.status_code == 200
    assert "create" in called
    assert called["create"]["idempotency_key"] == idem_key_create

    # Capture endpoint
    resp2 = await async_client.post(
        "/api/payments/stripe/capture",
        headers={**admin_headers, "Idempotency-Key": idem_key_capture},
        json={"payment_intent_id": "pi_fake"},
    )
    assert resp2.status_code == 200
    assert "capture" in called
    assert called["capture"]["idempotency_key"] == idem_key_capture
