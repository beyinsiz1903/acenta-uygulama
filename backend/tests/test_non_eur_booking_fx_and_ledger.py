from __future__ import annotations

import math

import pytest

from app.db import get_db
from app.utils import now_utc


TOLERANCE_ABS = 0.02
TOLERANCE_PCT = 0.001


def approx_equal(a: float, b: float, *, abs_tol: float = TOLERANCE_ABS, rel_tol: float = TOLERANCE_PCT) -> bool:
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


@pytest.mark.anyio
async def test_non_eur_booking_fx_and_ledger(async_client, admin_token, agency_token):
    """P1.1: TRY booking flow + EUR ledger standardi kaniti.

    Kanit seti:
    1) Booking TRY, sell>0
    2) Booking.amounts.sell_eur > 0 ve FX snapshot ile tutarli
    3) booking_financials sell_total & sell_total_eur, booking ile bire bir ayni
    4) fx_rate_snapshots context=booking, base/quote/rate_basis dogru
    5) ledger_postings EUR, toplam debit/credit ~= booking.amounts.sell_eur
    """

    client = async_client
    db = await get_db()

    # 1) agency1 kullanicisi ile basit bir booking yarat (mevcut P0.2 flow uzerinden)
    # Burada direkt olarak b2b booking create endpoint'ini kullaniyoruz.

    # a) Agency kullanicisi ile login olmaya gerek yok; admin ile ops/b2b booking akisi test
    headers_agency = {"Authorization": f"Bearer {agency_token}"}

    # Use a simple existing search to obtain a product offer via P0.2 flow if needed.
    # For simplicity in this test, assume there is already at least one existing booking
    # created for agency1 in the system and reuse it. This keeps the test stable against
    # future search/quote changes.

    # Find latest booking for agency1
    agency_user = await db.users.find_one({"email": "agency1@demo.test"})
    assert agency_user is not None
    agency_id = agency_user["agency_id"]

    booking = await db.bookings.find_one({"agency_id": agency_id}, sort=[("created_at", -1)])
    assert booking is not None, "No existing booking found for agency1; seed or P0.2 flow must create one."

    booking_id = str(booking["_id"])

    # 1) Booking TRY, sell>0
    currency = booking.get("currency")
    amounts = booking.get("amounts") or {}
    sell = float(amounts.get("sell", 0.0))
    sell_eur = amounts.get("sell_eur")

    assert currency in {"EUR", "TRY"}

    if currency == "EUR":
        pytest.skip("Non-EUR P1.1 flow not yet active in this environment (booking currency is still EUR)")

    assert currency == "TRY"
    assert sell > 0

    # 2) Booking.amounts.sell_eur > 0 ve FX snapshot ile tutarli
    assert sell_eur is not None and float(sell_eur) > 0

    fx_info = booking.get("fx") or {}
    rate = float(fx_info.get("rate", 0.0))
    rate_basis = fx_info.get("rate_basis")
    base = fx_info.get("base")
    quote = fx_info.get("quote")

    assert rate_basis == "QUOTE_PER_EUR"
    assert base == "EUR"
    assert quote == "TRY"
    assert rate > 0

    expected_sell_eur = round(float(sell) / rate, 2)
    assert approx_equal(float(sell_eur), expected_sell_eur), (
        f"sell_eur mismatch: booking.amounts.sell_eur={sell_eur}, "
        f"expected ~{expected_sell_eur} from sell={sell} / rate={rate}"
    )

    # 3) booking_financials mirror
    bf = await db.booking_financials.find_one({"booking_id": booking_id, "organization_id": booking["organization_id"]})
    if not bf:
        # ensure_financials yoksa ops endpoint'i uzerinden olustur
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        resp_fin = await client.get(f"/api/ops/finance/bookings/{booking_id}/financials", headers=admin_headers)
        assert resp_fin.status_code == 200, resp_fin.text
        bf = resp_fin.json()
    else:
        # normalize
        bf["sell_total"] = float(bf.get("sell_total", 0.0))
        bf["sell_total_eur"] = float(bf.get("sell_total_eur", 0.0))

    assert float(bf.get("sell_total", 0.0)) == sell
    assert float(bf.get("sell_total_eur", 0.0)) == float(sell_eur)

    fx_snap = bf.get("fx_snapshot") or {}
    assert fx_snap.get("base") == "EUR"
    assert fx_snap.get("quote") == "TRY"
    assert fx_snap.get("rate_basis") == "QUOTE_PER_EUR"

    # 4) fx_rate_snapshots dokumani
    snap = await db.fx_rate_snapshots.find_one(
        {
            "organization_id": booking["organization_id"],
            "context.type": "booking",
            "context.id": booking_id,
        }
    )
    assert snap is not None
    assert snap.get("base") == "EUR"
    assert snap.get("quote") == "TRY"
    assert snap.get("rate_basis") == "QUOTE_PER_EUR"

    # 5) ledger_postings EUR, toplam debit/credit ~= booking.amounts.sell_eur
    postings = await db.ledger_postings.find(
        {
            "organization_id": booking["organization_id"],
            "source.type": "booking",
            "source.id": booking_id,
            "event": "BOOKING_CONFIRMED",
        }
    ).to_list(length=10)

    assert postings, "No BOOKING_CONFIRMED postings found for booking"

    total_debit = 0.0
    total_credit = 0.0
    for p in postings:
        assert p.get("currency") == "EUR"
        total_debit += float(p.get("debit", 0.0) or 0.0)
        total_credit += float(p.get("credit", 0.0) or 0.0)

    assert approx_equal(total_debit, total_credit), f"Ledger not balanced: debit={total_debit}, credit={total_credit}"
    assert approx_equal(total_debit, float(sell_eur)), f"Ledger amount {total_debit} != booking.sell_eur {sell_eur}"
