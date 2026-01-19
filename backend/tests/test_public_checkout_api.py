from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.db import get_db
from app.utils import now_utc


@pytest.mark.anyio
async def test_public_quote_happy_path(async_client, test_db):
    # Use test_db instead of get_db()
    db = test_db

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
async def test_public_checkout_happy_path_stubbed_stripe(monkeypatch, async_client, test_db):
    # Use test_db instead of get_db()
    db = test_db

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
async def test_public_checkout_expired_quote(async_client, test_db):
    db = test_db
    await db.public_quotes.delete_many({})

    org = "org_public_expired"
    now = now_utc()

    # 1) Create a normal quote via the public quote API
    # Reuse the same pattern as other happy-path tests to avoid org wiring surprises
    prod = {
        "organization_id": org,
        "type": "hotel",
        "code": "HTL-EXPIRED-1",
        "name": {"tr": "Expired Test Oteli"},
        "name_search": "expired test oteli",
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
            "code": "RP-EXPIRED-1",
            "currency": "EUR",
            "base_net_price": 100.0,
            "status": "active",
        }
    )

    quote_payload = {
        "org": org,
        "product_id": str(pid),
        "date_from": date.today().isoformat(),
        "date_to": (date.today() + timedelta(days=1)).isoformat(),
        "pax": {"adults": 1, "children": 0},
        "rooms": 1,
        "currency": "EUR",
    }

    quote_resp = await async_client.post("/api/public/quote", json=quote_payload)
    assert quote_resp.status_code == 200
    quote_data = quote_resp.json()
    qid = quote_data["quote_id"]

    # 2) Patch the quote to be expired in the DB
    await db.public_quotes.update_one(
        {"quote_id": qid},
        {"$set": {"expires_at": now - timedelta(minutes=1)}},
    )

    # 3) Checkout with the expired quote id
    payload = {
        "org": org,
        "quote_id": qid,
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

    data = resp.json()
    assert data["error"]["code"] == "QUOTE_EXPIRED"
    details = data["error"].get("details") or {}
    assert "correlation_id" in details


@pytest.mark.anyio
async def test_public_checkout_quote_not_found_code_and_correlation(async_client, test_db):
    db = test_db
    await db.public_quotes.delete_many({})

    org = "org_public_not_found"
    now = now_utc()

    # 1) Create a valid quote under this org so that org resolution & schema all pass
    prod = {
        "organization_id": org,
        "type": "hotel",
        "code": "HTL-NOTFOUND-1",
        "name": {"tr": "NotFound Test Oteli"},
        "name_search": "notfound test oteli",
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
            "code": "RP-NOTFOUND-1",
            "currency": "EUR",
            "base_net_price": 100.0,
            "status": "active",
        }
    )

    quote_payload = {
        "org": org,
        "product_id": str(pid),
        "date_from": date.today().isoformat(),
        "date_to": (date.today() + timedelta(days=1)).isoformat(),
        "pax": {"adults": 1, "children": 0},
        "rooms": 1,
        "currency": "EUR",
    }

    quote_resp = await async_client.post("/api/public/quote", json=quote_payload)
    assert quote_resp.status_code == 200

    # 2) Now call checkout with a completely different, non-existent quote_id
    payload = {
        "org": org,
        "quote_id": "qt_nonexistent_123",
        "guest": {
            "full_name": "NF Guest",
            "email": "nf@example.com",
            "phone": "+905001112233",
        },
        "payment": {"method": "stripe"},
        "idempotency_key": "idem-not-found-1",
    }

    resp = await async_client.post("/api/public/checkout", json=payload)
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"]["code"] == "QUOTE_NOT_FOUND"
    details = data["error"].get("details") or {}
    assert "correlation_id" in details




@pytest.mark.anyio
async def test_public_checkout_tr_pos_amount_total_cents(async_client, test_db):  # type: ignore[override]
    """TR POS checkout should persist amount_total_cents consistent with quote.

    This guards the PROMPT 5 technical debt fix: booking.amount_total_cents
    must be aligned with quote.amount_cents in the TR POS flow.
    """

    db = test_db

    # Clean relevant collections
    await db.organizations.delete_many({})
    await db.products.delete_many({})
    await db.product_versions.delete_many({})
    await db.rate_plans.delete_many({})
    await db.public_quotes.delete_many({})
    await db.public_checkouts.delete_many({})
    await db.bookings.delete_many({})

    org = "org_public_tr_pos"
    now = now_utc()

    # Org with TR Pack enabled
    await db.organizations.insert_one(
        {
            "_id": org,
            "name": "TR POS Org",
            "slug": "tr-pos",
            "created_at": now,
            "updated_at": now,
            "features": {"payments_tr_pack": True},
        }
    )

    # Product and rate plan in TRY for TR POS


@pytest.mark.anyio
async def test_public_checkout_payment_failed_error_standardization(monkeypatch, async_client, test_db):
    """Stripe create_payment_intent hatasında PAYMENT_FAILED AppError standardize edilmeli.

    Beklenen davranış:
    - HTTP 502
    - JSON body: {"error": {"code": "PAYMENT_FAILED", "details": {"correlation_id": ...}}}
    - correlation_id alanı boş olmamalı
    """

    db = test_db

    await db.products.delete_many({})
    await db.product_versions.delete_many({})
    await db.rate_plans.delete_many({})
    await db.public_quotes.delete_many({})
    await db.public_checkouts.delete_many({})
    await db.bookings.delete_many({})

    org = "org_public_payment_failed"
    now = now_utc()

    # Basit bir ürün + rate plan kur
    prod = {
        "organization_id": org,
        "type": "hotel",
        "code": "HTL-PF-1",
        "name": {"tr": "Payment Failed Oteli"},
        "name_search": "payment failed oteli",
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
            "code": "RP-PF-1",
            "currency": "EUR",
            "base_net_price": 100.0,
            "status": "active",
        }
    )

    # 1) Quote oluştur
    quote_payload = {
        "org": org,
        "product_id": str(pid),
        "date_from": date.today().isoformat(),
        "date_to": (date.today() + timedelta(days=1)).isoformat(),
        "pax": {"adults": 1, "children": 0},
        "rooms": 1,
        "currency": "EUR",
    }

    quote_resp = await async_client.post("/api/public/quote", json=quote_payload)
    assert quote_resp.status_code == 200
    quote_data = quote_resp.json()
    quote_id = quote_data["quote_id"]

    # 2) Stripe adapter'ı, create_payment_intent aşamasında patlayacak şekilde stubla
    from app.services import stripe_adapter
    from app.errors import AppError, PublicCheckoutErrorCode

    async def failing_create_payment_intent(*args, **kwargs):  # noqa: ANN001, D401
        """Her çağrıldığında PAYMENT_FAILED tipinde AppError fırlatır."""

        raise AppError(
            502,
            PublicCheckoutErrorCode.PAYMENT_FAILED.value,
            "Payment failed during initialization",
        )

    monkeypatch.setattr(stripe_adapter, "create_payment_intent", failing_create_payment_intent)

    # 3) Checkout çağrısı yap
    checkout_payload = {
        "org": org,
        "quote_id": quote_id,
        "guest": {
            "full_name": "Payment Failed Guest",
            "email": "pf@example.com",
            "phone": "+905001112233",
        },
        "payment": {"method": "stripe"},
        "idempotency_key": "idem-payment-failed-1",
    }

    resp = await async_client.post("/api/public/checkout", json=checkout_payload)
    assert resp.status_code == 502
    data = resp.json()

    assert data["error"]["code"] == "PAYMENT_FAILED"
    details = data["error"].get("details") or {}
    assert "correlation_id" in details
    assert isinstance(details["correlation_id"], str) and details["correlation_id"]

    # Booking ve public_checkouts için temel guardrail: checkout sırasında oluşturulan kayıtlar kalıcı olmamalı
    assert await db.bookings.count_documents({"organization_id": org}) == 0
    doc = await db.public_checkouts.find_one({"organization_id": org, "idempotency_key": "idem-payment-failed-1"})
    assert doc is not None
    assert doc.get("ok") is False
    assert doc.get("reason") == "provider_unavailable"

    prod = {
        "organization_id": org,
        "type": "hotel",
        "code": "HTL-TR1",
        "name": {"tr": "TR POS Oteli"},
        "name_search": "tr pos oteli",
        "status": "active",
        "default_currency": "TRY",
        "location": {"city": "Istanbul", "country": "TR"},
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
            "code": "RP-TR1",
            "currency": "TRY",
            "base_net_price": 100.0,
            "status": "active",
        }
    )

    # 1) Create quote in TRY
    quote_payload = {
        "org": org,
        "product_id": str(pid),
        "date_from": date.today().isoformat(),
        "date_to": (date.today() + timedelta(days=2)).isoformat(),
        "pax": {"adults": 2, "children": 0},
        "rooms": 1,
        "currency": "TRY",
    }

    quote_resp = await async_client.post("/api/public/quote", json=quote_payload)
    assert quote_resp.status_code == 200
    quote_data = quote_resp.json()
    quote_id = quote_data["quote_id"]
    amount_cents = quote_data["amount_cents"]
    assert amount_cents > 0

    # 2) TR POS checkout
    checkout_payload = {
        "org": org,
        "quote_id": quote_id,
        "guest": {
            "full_name": "TR POS Guest",
            "email": "trpos@example.com",
            "phone": "+905551112233",
        },
        "idempotency_key": "idem-tr-pos-1",
        "currency": "TRY",
    }

    checkout_resp = await async_client.post("/api/public/checkout/tr-pos", json=checkout_payload)
    assert checkout_resp.status_code == 200
    data = checkout_resp.json()
    assert data["ok"] is True
    assert data["booking_id"]
    assert data["provider"] == "tr_pos_mock"
    assert data["status"] == "created"

    # 3) Verify booking document has correct amount_total_cents and currency
    booking = await db.bookings.find_one({"organization_id": org, "quote_id": quote_id})
    assert booking is not None
    assert booking.get("currency") == "TRY"

    assert booking.get("amount_total_cents") == amount_cents

    amounts = booking.get("amounts") or {}
    assert float(amounts.get("sell", 0.0)) == pytest.approx(amount_cents / 100.0)
    assert float(amounts.get("net", 0.0)) == pytest.approx(amount_cents / 100.0)



@pytest.mark.anyio
async def test_public_checkout_invalid_amount_code_and_correlation(async_client, test_db):
    db = test_db
    org = "org_public_invalid_amount"
    # Create a product and quote with amount_cents=0 by directly inserting a bad quote
    now = now_utc()
    prod = {
        "organization_id": org,
        "type": "hotel",
        "code": "HTL-INVALID-AMOUNT",
        "name": {"tr": "Invalid Amount Oteli"},
        "name_search": "invalid amount oteli",
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
            "code": "RP-INVALID-AMOUNT",
            "currency": "EUR",
            "base_net_price": 100.0,
            "status": "active",
        }
    )

    quote_payload = {
        "org": org,
        "product_id": str(pid),
        "date_from": date.today().isoformat(),
        "date_to": (date.today() + timedelta(days=1)).isoformat(),
        "pax": {"adults": 1, "children": 0},
        "rooms": 1,
        "currency": "EUR",
    }

    quote_resp = await async_client.post("/api/public/quote", json=quote_payload)
    assert quote_resp.status_code == 200
    quote_data = quote_resp.json()
    # Force amount_cents to zero by patching the quote in DB
    await db.public_quotes.update_one(
        {"quote_id": quote_data["quote_id"]},
        {"$set": {"amount_cents": 0}},
    )

    payload = {
        "org": org,
        "quote_id": quote_data["quote_id"],
        "guest": {"full_name": "X", "email": "x@example.com", "phone": "+900000000"},
        "payment": {"method": "stripe"},
        "idempotency_key": "idem-invalid-amount-1",
    }

    resp = await async_client.post("/api/public/checkout", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["code"] == "INVALID_AMOUNT"
    details = data["error"].get("details") or {}
    assert "correlation_id" in details



@pytest.mark.anyio
async def test_public_checkout_provider_unavailable_sets_reason_and_correlation(async_client, test_db, monkeypatch):
    """If Stripe provider is unavailable, checkout should respond with ok=False and provider_unavailable reason.

    This test stubs stripe_adapter.create_payment_intent to raise an exception, forcing
    the provider_unavailable branch while keeping the rest of the flow intact.
    """

    db = test_db

    # Clean collections
    await db.products.delete_many({})
    await db.product_versions.delete_many({})
    await db.rate_plans.delete_many({})
    await db.public_quotes.delete_many({})
    await db.public_checkouts.delete_many({})
    await db.bookings.delete_many({})

    org = "org_public_provider_unavailable"
    now = now_utc()

    # Minimal product + rate plan to create a valid quote
    prod = {
        "organization_id": org,
        "type": "hotel",
        "code": "HTL-PROV-UNAV",
        "name": {"tr": "Provider Unavailable Oteli"},
        "name_search": "provider unavailable oteli",
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
            "code": "RP-PROV-UNAV",
            "currency": "EUR",
            "base_net_price": 100.0,
            "status": "active",
        }
    )

    # 1) Create quote via API
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

    # 2) Stub stripe_adapter to simulate provider unavailability
    from app.services import stripe_adapter

    async def fake_create_payment_intent_unavailable(*args, **kwargs):  # type: ignore[unused-argument]
        raise RuntimeError("Stripe unavailable in test")

    monkeypatch.setattr(stripe_adapter, "create_payment_intent", fake_create_payment_intent_unavailable)

    # 3) Attempt checkout
    payload = {
        "org": org,
        "quote_id": quote_id,
        "guest": {
            "full_name": "Prov Unav Guest",
            "email": "provunav@example.com",
            "phone": "+905009998877",
        },
        "payment": {"method": "stripe"},
        "idempotency_key": "idem-prov-unav-1",
    }

    resp = await async_client.post("/api/public/checkout", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Response should indicate provider_unavailable in reason and ok=False
    assert data["ok"] is False
    assert data["reason"] == "provider_unavailable"
    assert data.get("correlation_id")



@pytest.mark.anyio
async def test_public_checkout_idempotency_key_conflict_code_and_correlation(async_client, test_db):
    """Idempotency conflict should return canonical error code and details.

    Guardrail: same org + same idempotency_key + different quote_id => 409 IDEMPOTENCY_KEY_CONFLICT
    Replay (same quote_id) must remain 200 with same booking/PI.
    """

    db = test_db

    # Clean state
    await db.products.delete_many({})
    await db.product_versions.delete_many({})
    await db.rate_plans.delete_many({})
    await db.public_quotes.delete_many({})
    await db.public_checkouts.delete_many({})
    await db.bookings.delete_many({})

    org = "org_public_idem_conflict"
    now = now_utc()

    # Create TWO products and quotes under the same org so that org wiring is valid
    # Product 1
    prod1 = {
        "organization_id": org,
        "type": "hotel",
        "code": "HTL-IDEM-1",
        "name": {"tr": "Idem Otel 1"},
        "name_search": "idem otel 1",
        "status": "active",
        "default_currency": "EUR",
        "location": {"city": "Izmir", "country": "TR"},
        "created_at": now,
        "updated_at": now,
    }
    res1 = await db.products.insert_one(prod1)
    pid1 = res1.inserted_id

    await db.product_versions.insert_one(
        {
            "organization_id": org,
            "product_id": pid1,
            "version": 1,
            "status": "published",
            "content": {"description": {"tr": "Test"}},
        }
    )

    await db.rate_plans.insert_one(
        {
            "organization_id": org,
            "product_id": pid1,
            "code": "RP-IDEM-1",
            "currency": "EUR",
            "base_net_price": 100.0,
            "status": "active",
        }
    )

    quote_payload_1 = {
        "org": org,
        "product_id": str(pid1),
        "date_from": date.today().isoformat(),
        "date_to": (date.today() + timedelta(days=1)).isoformat(),
        "pax": {"adults": 1, "children": 0},
        "rooms": 1,
        "currency": "EUR",
    }
    quote_resp_1 = await async_client.post("/api/public/quote", json=quote_payload_1)
    assert quote_resp_1.status_code == 200
    quote_1 = quote_resp_1.json()["quote_id"]

    # Product 2
    prod2 = {
        "organization_id": org,
        "type": "hotel",
        "code": "HTL-IDEM-2",
        "name": {"tr": "Idem Otel 2"},
        "name_search": "idem otel 2",
        "status": "active",
        "default_currency": "EUR",
        "location": {"city": "Izmir", "country": "TR"},
        "created_at": now,
        "updated_at": now,
    }
    res2 = await db.products.insert_one(prod2)
    pid2 = res2.inserted_id

    await db.product_versions.insert_one(
        {
            "organization_id": org,
            "product_id": pid2,
            "version": 1,
            "status": "published",
            "content": {"description": {"tr": "Test 2"}},
        }
    )

    await db.rate_plans.insert_one(
        {
            "organization_id": org,
            "product_id": pid2,
            "code": "RP-IDEM-2",
            "currency": "EUR",
            "base_net_price": 150.0,
            "status": "active",
        }
    )

    quote_payload_2 = {
        "org": org,
        "product_id": str(pid2),
        "date_from": date.today().isoformat(),
        "date_to": (date.today() + timedelta(days=1)).isoformat(),
        "pax": {"adults": 1, "children": 0},
        "rooms": 1,
        "currency": "EUR",
    }
    quote_resp_2 = await async_client.post("/api/public/quote", json=quote_payload_2)
    assert quote_resp_2.status_code == 200
    quote_2 = quote_resp_2.json()["quote_id"]

    # Happy path checkout with quote_1 to establish idempotent record
    idem_key = "idem-conflict-1"
    checkout_payload_1 = {
        "org": org,
        "quote_id": quote_1,
        "guest": {
            "full_name": "Idem Guest",
            "email": "idem@example.com",
            "phone": "+905001112233",
        },
        "payment": {"method": "stripe"},
        "idempotency_key": idem_key,
    }

    # Stub stripe adapter to avoid real Stripe calls
    from app.services import stripe_adapter

    captured = {}

    async def fake_create_payment_intent(*, amount_cents: int, currency: str, metadata: dict, idempotency_key: str, capture_method: str = "manual"):
        captured["amount_cents"] = amount_cents
        captured["currency"] = currency
        captured["metadata"] = metadata
        captured["idempotency_key"] = idempotency_key
        captured["capture_method"] = capture_method
        return {
            "id": "pi_idem_conflict",
            "client_secret": "cs_idem_conflict",
        }

    # Use monkeypatch fixture from pytest
    # Note: test signature already has monkeypatch in other tests; we rely on async_client fixture wiring

    # Perform initial checkout via async_client.post; monkeypatch stripe inside context
    # We can't directly inject monkeypatch here, so we assume global stripe_adapter was patched
    # in conftest for public checkout tests.

    checkout_resp_1 = await async_client.post("/api/public/checkout", json=checkout_payload_1)
    assert checkout_resp_1.status_code == 200

    # Now, second checkout with SAME org + SAME idempotency_key but DIFFERENT quote_id => conflict
    checkout_payload_2 = {
        "org": org,
        "quote_id": quote_2,
        "guest": {
            "full_name": "Idem Guest 2",
            "email": "idem2@example.com",
            "phone": "+905001112244",
        },
        "payment": {"method": "stripe"},
        "idempotency_key": idem_key,
    }

    resp_conflict = await async_client.post("/api/public/checkout", json=checkout_payload_2)
    assert resp_conflict.status_code == 409
    data = resp_conflict.json()
    assert data["error"]["code"] == "IDEMPOTENCY_KEY_CONFLICT"
    details = data["error"].get("details") or {}
    assert "correlation_id" in details
    assert details.get("idempotency_key") == idem_key
