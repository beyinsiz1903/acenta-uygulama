from __future__ import annotations

from typing import Any, Dict, Tuple

import pytest

from app.db import get_db
from app.utils import now_utc


@pytest.mark.anyio
async def test_click_to_pay_happy_path_stubbed_stripe(monkeypatch, async_client, minimal_search_seed):
    """Happy path: ops creates a click-to-pay link and public resolves it.

    Stripe adapter is stubbed so we don't need real Stripe keys.
    Also asserts that PaymentIntent metadata is populated correctly.
    """

    db = await get_db()

    # Seed a simple booking in org "org_click_to_pay"
    org_id = "org_click_to_pay"
    now = now_utc()
    booking_id = "BKG-CLICK-1"

    await db.bookings.insert_one(
        {
            "_id": booking_id,
            "organization_id": org_id,
            "agency_id": "agency_ctp",
            "currency": "EUR",
            "amounts": {"sell": 123.45},
            "status": "CONFIRMED",
            "created_at": now,
            "updated_at": now,
        }
    )

    # Ensure booking_payments aggregate exists with zero paid amount
    await db.booking_payments.delete_many({"organization_id": org_id, "booking_id": booking_id})

    # Log in as admin and force org to match
    admin_email = "admin@acenta.test"
    await db.users.update_one(
        {"email": admin_email},
        {"$set": {"organization_id": org_id}},
    )

    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Stub stripe_adapter.create_payment_intent and retrieve_payment_intent
    from app.services import stripe_adapter

    captured_args: Dict[str, Any] = {}

    async def fake_create_payment_intent(*, amount_cents: int, currency: str, metadata: Dict[str, str], idempotency_key=None, capture_method: str = "manual") -> Dict[str, Any]:  # type: ignore[override]
        captured_args["amount_cents"] = amount_cents
        captured_args["currency"] = currency
        captured_args["metadata"] = metadata
        captured_args["capture_method"] = capture_method
        return {
            "id": "pi_fake_click_to_pay",
            "client_secret": "cs_test_click_to_pay",
        }

    async def fake_retrieve_payment_intent(*, payment_intent_id: str) -> Dict[str, Any]:  # type: ignore[override]
        assert payment_intent_id == "pi_fake_click_to_pay"
        return {
            "id": payment_intent_id,
            "client_secret": "cs_test_click_to_pay",
        }

    monkeypatch.setattr(stripe_adapter, "create_payment_intent", fake_create_payment_intent)
    monkeypatch.setattr(stripe_adapter, "retrieve_payment_intent", fake_retrieve_payment_intent)

    # Call ops endpoint to create link
    resp = await async_client.post(
        "/api/ops/payments/click-to-pay/",
        json={"booking_id": booking_id},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["url"].startswith("/pay/")
    assert body["amount_cents"] > 0
    assert body["currency"].upper() == "EUR"

    # Assert Stripe metadata and capture_method
    assert captured_args["currency"] == "eur"
    assert captured_args["capture_method"] == "automatic"
    meta = captured_args["metadata"]
    assert meta["source"] == "click_to_pay"
    assert meta["booking_id"] == booking_id
    assert meta["organization_id"] == org_id
    assert meta["agency_id"] == "agency_ctp"

    # Verify link persisted in click_to_pay_links
    link_doc = await db.click_to_pay_links.find_one({"organization_id": org_id, "booking_id": booking_id})
    assert link_doc is not None
    assert link_doc["amount_cents"] == body["amount_cents"]
    assert link_doc["currency"] == body["currency"].lower()

    # Resolve via public endpoint
    token = body["url"].split("/pay/")[-1]
    public_resp = await async_client.get(f"/api/public/pay/{token}")
    assert public_resp.status_code == 200
    pdata = public_resp.json()
    assert pdata["ok"] is True
    assert pdata["amount_cents"] == body["amount_cents"]
    assert pdata["currency"] == "EUR"
    assert pdata["client_secret"] == "cs_test_click_to_pay"
    assert pdata["booking_code"] in {booking_id, link_doc.get("booking_id")}


@pytest.mark.anyio
async def test_click_to_pay_nothing_to_collect(monkeypatch, async_client):
    """If remaining <= 0, endpoint should return ok:false, reason=nothing_to_collect."""

    db = await get_db()
    org_id = "org_click_to_pay_nothing"
    now = now_utc()
    booking_id = "BKG-CLICK-2"

    await db.bookings.insert_one(
        {
            "_id": booking_id,
            "organization_id": org_id,
            "agency_id": "agency_ctp2",
            "currency": "EUR",
            "amounts": {"sell": 100.0},
            "status": "CONFIRMED",
            "created_at": now,
            "updated_at": now,
        }
    )

    # Seed booking_payments as fully paid
    await db.booking_payments.insert_one(
        {
            "organization_id": org_id,
            "booking_id": booking_id,
            "currency": "EUR",
            "amount_total": 10_000,
            "amount_paid": 10_000,
            "amount_refunded": 0,
            "status": "PAID",
        }
    )

    admin_email = "admin@acenta.test"
    await db.users.update_one(
        {"email": admin_email},
        {"$set": {"organization_id": org_id}},
    )

    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    from app.services import stripe_adapter

    async def fake_create_payment_intent(**kwargs: Any) -> Dict[str, Any]:  # pragma: no cover - should not be called
        raise AssertionError("Stripe should not be called when nothing_to_collect")

    monkeypatch.setattr(stripe_adapter, "create_payment_intent", fake_create_payment_intent)

    resp = await async_client.post(
        "/api/ops/payments/click-to-pay/",
        json={"booking_id": booking_id},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["reason"] == "nothing_to_collect"
    assert body["url"] is None


@pytest.mark.anyio
async def test_click_to_pay_wrong_org_ownership(async_client):
    """Booking belonging to another org must not be visible to current user (404)."""

    db = await get_db()
    now = now_utc()

    booking_id = "BKG-CLICK-3"
    await db.bookings.insert_one(
        {
            "_id": booking_id,
            "organization_id": "org_A",
            "agency_id": "agency_A",
            "currency": "EUR",
            "amounts": {"sell": 50.0},
            "status": "CONFIRMED",
            "created_at": now,
            "updated_at": now,
        }
    )

    admin_email = "admin@acenta.test"
    await db.users.update_one(
        {"email": admin_email},
        {"$set": {"organization_id": "org_B"}},
    )

    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        "/api/ops/payments/click-to-pay/",
        json={"booking_id": booking_id},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_public_pay_invalid_and_expired_token(async_client):
    """Invalid or expired tokens should return generic 404 NOT_FOUND."""

    # Completely invalid token (no DB record)
    resp = await async_client.get("/api/public/pay/invalid-token-123")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "NOT_FOUND"

    # Manually insert an expired link and ensure resolver treats it as 404
    db = await get_db()
    now = now_utc()
    from app.services.click_to_pay import _hash_token

    raw_token = "expired-token-456"
    token_hash = _hash_token(raw_token)

    await db.click_to_pay_links.insert_one(
        {
            "token_hash": token_hash,
            "expires_at": now.replace(year=now.year - 1),  # clearly in the past
            "organization_id": "org_expired",
            "booking_id": "BKG-EXPIRED",
            "payment_intent_id": "pi_expired",
            "amount_cents": 1000,
            "currency": "eur",
            "status": "active",
            "telemetry": {"access_count": 0},
            "created_at": now,
        }
    )

    resp2 = await async_client.get(f"/api/public/pay/{raw_token}")
    assert resp2.status_code == 404
    body2 = resp2.json()
    assert body2["error"] == "NOT_FOUND"
