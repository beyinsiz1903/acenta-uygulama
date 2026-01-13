from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.db import get_db
from app.utils import now_utc


@pytest.mark.anyio
async def test_public_booking_summary_happy_path(async_client):
    db = await get_db()

    await db.bookings.delete_many({})

    org = "org_public_summary"
    now = now_utc()

    booking = {
        "organization_id": org,
        "booking_code": "PB-TEST123",
        "status": "PENDING_PAYMENT",
        "amounts": {"sell": 123.45},
        "currency": "EUR",
        "public_quote": {
            "date_from": datetime(2026, 1, 15),
            "date_to": datetime(2026, 1, 17),
            "nights": 2,
            "pax": {"adults": 2, "children": 0, "rooms": 1},
        },
        "created_at": now,
        "guest": {
            "full_name": "Should Not Leak",
            "email": "secret@example.com",
            "phone": "+9000000000",
        },
    }
    await db.bookings.insert_one(booking)

    resp = await async_client.get("/api/public/bookings/by-code/PB-TEST123", params={"org": org})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    b = data["booking"]

    assert b["booking_code"] == "PB-TEST123"
    assert b["status"] == "PENDING_PAYMENT"
    assert b["price"]["amount_cents"] == 12345
    assert b["price"]["currency"] == "EUR"

    assert b["pax"]["adults"] == 2
    assert b["pax"]["children"] == 0
    assert b["pax"]["rooms"] == 1

    # PII should NOT be present
    assert "guest" not in b
    assert "email" not in b


@pytest.mark.anyio
async def test_public_booking_summary_not_found(async_client):
    db = await get_db()
    await db.bookings.delete_many({})

    resp = await async_client.get("/api/public/bookings/by-code/NOPE", params={"org": "org_x"})
    assert resp.status_code == 404
    data = resp.json()
    assert data["detail"] == "NOT_FOUND"
