from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.db import get_db
from app.utils import now_utc


@pytest.mark.anyio
async def test_public_quote_happy_path(async_client):
    db = await get_db()

    await db.products.delete_many({})
    await db.product_versions.delete_many({})
    await db.rate_plans.delete_many({})
    await db.public_quotes.delete_many({})

    org = "org_public_quote"
    now = now_utc()

    prod = {
        "organization_id": org,
        "type": "hotel",
        "code": "HTL-Q1",
        "name": {"tr": "Quote Oteli"},
        "name_search": "quote oteli",
        "status": "active",
        "default_currency": "EUR",
        "location": {"city": "Izmir", "country": "TR"},
        "created_at": now,
        "updated_at": now,
    }
    res = await db.products.insert_one(prod)
    pid = res.inserted_id

    await db.product_versions.insert_one(
        {
            "organization_id": org,
            "product_id": pid,
            "version": 1,
            "status": "published",
            "content": {"description": {"tr": "Test"}},
        }
    )

    await db.rate_plans.insert_one(
        {
            "organization_id": org,
            "product_id": pid,
            "code": "RP-Q1",
            "currency": "EUR",
            "base_net_price": 100.0,
            "status": "active",
        }
    )

    payload = {
        "org": org,
        "product_id": str(pid),
        "date_from": date.today().isoformat(),
        "date_to": (date.today() + timedelta(days=3)).isoformat(),
        "pax": {"adults": 2, "children": 0},
        "rooms": 1,
        "currency": "EUR",
    }

    resp = await async_client.post("/api/public/quote", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["quote_id"]
    assert data["amount_cents"] > 0
    assert data["currency"] == "EUR"
    assert "product" in data


@pytest.mark.anyio
async def test_public_checkout_happy_path_stubbed_stripe(monkeypatch, async_client):
    db = await get_db()

    await db.products.delete_many({})
    await db.product_versions.delete_many({})
    await db.rate_plans.delete_many({})
    await db.public_quotes.delete_many({})
    await db.public_checkouts.delete_many({})
    await db.bookings.delete_many({})

    org = "org_public_checkout"
    now = now_utc()

    prod = {
        "organization_id": org,
        "type": "hotel",
        "code": "HTL-C1",
        "name": {"tr": "Checkout Oteli"},
        "name_search": "checkout oteli",
        "status": "active",
        "default_currency": "EUR",
        "location": {"city": "Izmir", "country": "TR"},
        "created_at": now,
        "updated_at": now,
    }
    res = await db.products.insert_one(prod)
    pid = res.inserted_id

    await db.product_versions.insert_one(
        {
            "organization_id": org,
            "product_id": pid,
            "version": 1,
            "status": "published",
            "content": {"description": {"tr": "Test"}},
        }
    )

    await db.rate_plans.insert_one(
        {
            "organization_id": org,
            "product_id": pid,
            "code": "RP-C1",
            "currency": "EUR",
            "base_net_price": 100.0,
            "status": "active",
        }
    )

    # 1) Create quote
    quote_payload = {
        "org": org,
        "product_id": str(pid),
        "date_from": date.today().isoformat(),
        "date_to": (date.today() + timedelta(days=2)).isoformat(),
        "pax": {"adults": 2, "children": 0},
        "rooms": 1,
        "currency": "EUR",
    }

    quote_resp = await async_client.post("/api/public/quote", json=quote_payload)
    assert quote_resp.status_code == 200
    quote_data = quote_resp.json()
    quote_id = quote_data["quote_id"]
    amount_cents = quote_data["amount_cents"]

    # 2) Stub stripe_adapter.create_payment_intent
    from app.services import stripe_adapter

    captured: dict = {}

    async def fake_create_payment_intent(*, amount_cents: int, currency: str, metadata: dict, idempotency_key: str, capture_method: str = "manual"):
        captured["amount_cents"] = amount_cents
        captured["currency"] = currency
        captured["metadata"] = metadata
        captured["idempotency_key"] = idempotency_key
        captured["capture_method"] = capture_method
        return {
            "id": "pi_public_checkout",
            "client_secret": "cs_public_checkout",
        }

    monkeypatch.setattr(stripe_adapter, "create_payment_intent", fake_create_payment_intent)

    # 3) Perform checkout
    checkout_payload = {
        "org": org,
        "quote_id": quote_id,
        "guest": {
            "full_name": "Test Guest",
            "email": "guest@example.com",
            "phone": "+905001112233",
        },
        "payment": {"method": "stripe", "return_url": "https://example.com/book/complete"},
        "idempotency_key": "idem-public-1",
    }

    checkout_resp = await async_client.post("/api/public/checkout", json=checkout_payload)
    assert checkout_resp.status_code == 200
    data = checkout_resp.json()
    assert data["ok"] is True
    assert data["booking_id"]
    assert data["payment_intent_id"] == "pi_public_checkout"
    assert data["client_secret"] == "cs_public_checkout"

    # Stripe metadata assertions
    assert captured["amount_cents"] == amount_cents
    assert captured["currency"].upper() == "EUR"
    meta = captured["metadata"]
    assert meta["source"] == "public_checkout"
    assert meta["organization_id"] == org
    assert meta["quote_id"] == quote_id
    assert "booking_id" in meta
    assert captured["capture_method"] == "automatic"

    # Booking status and amounts
    booking = await db.bookings.find_one({"_id": data["booking_id"]})
    # booking_id is string from API, must convert or query by booking_code instead
    if not booking:
        booking = await db.bookings.find_one({"payment_intent_id": "pi_public_checkout"})
    assert booking is not None
    assert booking.get("status") == "PENDING_PAYMENT"
    amounts = booking.get("amounts") or {}
    assert float(amounts.get("sell", 0.0)) == pytest.approx(amount_cents / 100.0)

    # Idempotency: second call returns same booking + PI
    checkout_resp2 = await async_client.post("/api/public/checkout", json=checkout_payload)
    assert checkout_resp2.status_code == 200
    data2 = checkout_resp2.json()
    assert data2["booking_id"] == data["booking_id"]
    assert data2["payment_intent_id"] == data["payment_intent_id"]
    assert data2["client_secret"] == data["client_secret"]


@pytest.mark.anyio
async def test_public_checkout_expired_quote(async_client):
    db = await get_db()

    await db.public_quotes.delete_many({})

    org = "org_public_expired"
    now = now_utc()

    await db.public_quotes.insert_one(
        {
            "quote_id": "qt_expired",
            "organization_id": org,
            "amount_cents": 10000,
            "currency": "EUR",
            "status": "pending",
            "expires_at": now - timedelta(minutes=1),
            "created_at": now - timedelta(minutes=10),
        }
    )

    payload = {
        "org": org,
        "quote_id": "qt_expired",
        "guest": {
            "full_name": "Expired Guest",
            "email": "expired@example.com",
            "phone": "+905001112233",
        },
        "payment": {"method": "stripe"},
        "idempotency_key": "idem-expired-1",
    }

    resp = await async_client.post("/api/public/checkout", json=payload)
    assert resp.status_code == 404
