from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.db import get_db
from app.utils import now_utc


@pytest.mark.anyio
async def test_booking_cancel_creates_net_zero_ledger_and_full_refund(async_client, agency_token):
    """P1.x After-sales v1: CANCEL akışının finansal kanıtı.

    Senaryo:
    - Agency booking yaratır (mevcut P0.2 flow ile)
    - POST /api/b2b/bookings/{id}/cancel çağrılır
    - Sonuçta:
      - Booking.status == "CANCELLED"
      - booking_financials.refunded_total == sell_total_eur, penalty_total == 0
      - BOOKING_CONFIRMED + BOOKING_CANCELLED ledger_postings toplamı net 0
        ve her iki eventin mutlak tutarları eşit
    """

    client = async_client
    headers = {"Authorization": f"Bearer {agency_token}"}
    db = await get_db()

    # 1) Get agency info from token to find bookings that belong to this agency
    # First, get user info from the agency token
    user_resp = await client.get("/api/auth/me", headers=headers)
    assert user_resp.status_code == 200, f"Failed to get user info: {user_resp.text}"
    user_data = user_resp.json()
    agency_id = user_data.get("agency_id")
    org_id = user_data.get("organization_id")
    
    if not agency_id:
        pytest.skip("Agency user does not have agency_id; cannot test booking cancellation.")

    # 2) Find a CONFIRMED booking that belongs to this agency
    booking = await db.bookings.find_one({
        "status": "CONFIRMED",
        "organization_id": org_id,
        "agency_id": agency_id
    })
    if not booking:
        pytest.skip("No CONFIRMED booking found for this agency; P0.2 flow must create at least one booking for this test.")

    booking_id = str(booking["_id"])

    # 3) Cancel endpoint'i çağır
    resp = await client.post(f"/api/b2b/bookings/{booking_id}/cancel", json={}, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["booking_id"] == booking_id
    assert data["status"] == "CANCELLED"
    assert data["refund_status"] == "COMPLETED"

    # 3) Booking dokümanını kontrol et
    booking_after = await db.bookings.find_one({"_id": ObjectId(booking_id), "organization_id": org_id})
    assert booking_after is not None
    assert booking_after.get("status") == "CANCELLED"

    # 4) Booking financials: full refund, no penalty
    bf = await db.booking_financials.find_one({"organization_id": org_id, "booking_id": booking_id})
    assert bf is not None, "booking_financials document must exist after cancellation"

    sell_total_eur = float(bf.get("sell_total_eur", 0.0))
    refunded_total = float(bf.get("refunded_total", 0.0))
    penalty_total = float(bf.get("penalty_total", 0.0))

    assert refunded_total == pytest.approx(sell_total_eur)
    assert penalty_total == pytest.approx(0.0)

    # 5) Ledger postings: BOOKING_CONFIRMED + BOOKING_CANCELLED net 0
    postings = await db.ledger_postings.find(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": booking_id,
            "event": {"$in": ["BOOKING_CONFIRMED", "BOOKING_CANCELLED"]},
        }
    ).to_list(length=20)

    assert postings, "No ledger postings found for booking (CONFIRMED/CANCELLED)"

    total_debit = sum(float(p.get("debit", 0.0) or 0.0) for p in postings)
    total_credit = sum(float(p.get("credit", 0.0) or 0.0) for p in postings)

    # Balanced ledger overall
    assert total_debit == pytest.approx(total_credit, abs=0.02)

    # Event-bazlı mutlak tutarlar eşit olmalı
    confirmed_amount = sum(float(p.get("debit", 0.0) or 0.0) + float(p.get("credit", 0.0) or 0.0)
                           for p in postings if p.get("event") == "BOOKING_CONFIRMED")
    cancelled_amount = sum(float(p.get("debit", 0.0) or 0.0) + float(p.get("credit", 0.0) or 0.0)
                           for p in postings if p.get("event") == "BOOKING_CANCELLED")

    assert confirmed_amount == pytest.approx(cancelled_amount, abs=0.02)
