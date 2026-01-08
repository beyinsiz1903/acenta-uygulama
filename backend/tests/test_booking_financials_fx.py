from __future__ import annotations

import math
import uuid

import pytest

from app.db import get_db
from app.utils import now_utc


TOLERANCE_ABS = 0.02
TOLERANCE_PCT = 0.001  # 0.1%


def approx_equal(a: float, b: float, *, abs_tol: float = TOLERANCE_ABS, rel_tol: float = TOLERANCE_PCT) -> bool:
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


async def _create_simple_booking(client, token: str) -> str:
    """Use existing P0.2 flow to create a booking and return booking_id.

    This helper intentionally stays high-level: it assumes that the
    /api/b2b/hotels/search, /api/b2b/quotes and /api/b2b/bookings endpoints
    are already wired and working (P0.2).
    """

    headers = {"Authorization": f"Bearer {token}"}

    # 1) Search hotels for Istanbul with deterministic dates
    today = now_utc().date()
    # Use dates further in the future to avoid availability issues
    check_in = today.replace(year=2026, month=1, day=10)
    check_out = today.replace(year=2026, month=1, day=12)

    params = {
        "city": "Istanbul",
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "adults": "2",
        "children": "0",
    }
    res = await client.get("/api/b2b/hotels/search", headers=headers, params=params)
    assert res.status_code == 200
    data = res.json()
    items = data.get("items") or []
    assert items, "P0.2 search did not return any items"

    first = items[0]
    product_id = first["product_id"]
    rate_plan_id = first["rate_plan_id"]

    # 2) Create quote
    quote_payload = {
        "channel_id": "agency_extranet",
        "items": [
            {
                "product_id": product_id,
                "room_type_id": "default_room",
                "rate_plan_id": rate_plan_id,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "occupancy": 2,
            }
        ],
        "client_context": {"source": "p0.3-fx-test"},
    }
    res = await client.post("/api/b2b/quotes", headers=headers, json=quote_payload)
    assert res.status_code == 200, f"Quote creation failed: {res.status_code} - {res.text}"
    quote = res.json()
    quote_id = quote["quote_id"]

    # 3) Create booking
    booking_payload = {
        "quote_id": quote_id,
        "customer": {"name": "FX Test", "email": "fx@test.com"},
        "travellers": [{"first_name": "FX", "last_name": "Test"}],
        "notes": "P0.3 FX test booking",
    }
    res = await client.post(
        "/api/b2b/bookings",
        headers={**headers, "Idempotency-Key": f"p0.3-fx-booking-{uuid.uuid4().hex[:8]}"},
        json=booking_payload,
    )
    assert res.status_code == 200, f"Booking creation failed: {res.status_code} - {res.text}"
    booking = res.json()
    return booking["booking_id"]


@pytest.mark.anyio
async def test_booking_financials_and_fx_snapshot_consistency(async_client, admin_token, agency_token):
    """Booking financials ve ledger EUR denkligini dogrular.

    - P0.2 booking olusturur
    - booking_financials dokumanini ceker
    - ledger_postings/entries uzerinden EUR bazinda denklik kontrolu yapar
    """

    client = async_client

    # 1) Agency booking olustur
    booking_id = await _create_simple_booking(client, agency_token)

    # 2) Admin context ile booking_financials snapshot'ini al
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    res = await client.get(f"/api/ops/finance/bookings/{booking_id}/financials", headers=headers_admin)
    assert res.status_code == 200, f"Booking financials failed: {res.status_code} - {res.text}"
    fin = res.json()
    
    print(f"DEBUG: Booking financials response: {fin}")

    sell_total = float(fin.get("sell_total", 0.0))
    assert sell_total > 0
    currency = fin.get("currency")
    assert currency is not None

    # 3) Ledger postings/entries'den EUR denkligini dogrula
    db = await get_db()
    org_id = fin["organization_id"]

    # 4) Ledger postings/entries'den EUR denkligini dogrula
    postings_cur = db.ledger_postings.find(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": booking_id,
        }
    )
    postings = await postings_cur.to_list(length=1000)
    assert postings, "No ledger postings found for booking"

    # Tum postings EUR olmali
    for p in postings:
        assert p.get("currency") == "EUR"

    total_debit = sum(float(p.get("debit", 0.0)) for p in postings)
    total_credit = sum(float(p.get("credit", 0.0)) for p in postings)

    assert approx_equal(total_debit, total_credit), "Ledger debits and credits must balance in EUR"

    # Not: Tekil posting setinden sell_total_eur'yu dogrudan cikarmak
    # her zaman birebir mumkun olmayabilir (komisyon, fee vs.), o yuzden
    # burada sadece temel denklik ve snapshot varligini test ediyoruz.
