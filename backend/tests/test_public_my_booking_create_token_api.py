from __future__ import annotations

from datetime import timedelta

import pytest

from app.db import get_db
from app.utils import now_utc


@pytest.mark.anyio
async def test_create_token_happy_path(async_client):
    db = await get_db()

    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})

    org = "org_public_instant"
    now = now_utc()

    booking = {
        "_id": "BKG-INSTANT-1",
        "organization_id": org,
        "booking_code": "PB-INSTANT-123",
        "status": "PENDING_PAYMENT",
        "created_at": now,
    }
    await db.bookings.insert_one(booking)

    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": "PB-INSTANT-123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "token" in data and isinstance(data["token"], str) and data["token"]
    assert "expires_at" in data

    token_doc = await db.booking_public_tokens.find_one({"booking_id": booking["_id"]})
    assert token_doc is not None
    assert "token_hash" in token_doc
    assert token_doc.get("expires_at") is not None


@pytest.mark.anyio
async def test_create_token_not_found_is_ok(async_client):
    db = await get_db()

    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})

    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": "org_x", "booking_code": "NOPE"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ok": True}

    count = await db.booking_public_tokens.count_documents({})
    assert count == 0


@pytest.mark.anyio
async def test_create_token_validation_error(async_client):
    # Missing org / booking_code should trigger 422 validation error
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": "", "booking_code": ""},
    )
    assert resp.status_code == 422
