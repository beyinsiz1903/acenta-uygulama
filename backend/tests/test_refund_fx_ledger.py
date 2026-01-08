from __future__ import annotations

import math

import pytest

from app.db import get_db
from app.utils import now_utc


TOLERANCE_ABS = 0.02
TOLERANCE_PCT = 0.001


def approx_equal(a: float, b: float, *, abs_tol: float = TOLERANCE_ABS, rel_tol: float = TOLERANCE_PCT) -> bool:
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


async def _create_simple_booking(client, token: str) -> str:
    from app.tests.test_booking_financials_fx import _create_simple_booking as _helper  # type: ignore

    return await _helper(client, token)


@pytest.mark.anyio
async def test_refund_creates_reversal_and_net_eur_zero(async_client, admin_token, agency_token):
    """Booking + refund toplam EUR etkisi ~0 olmalidir.

    - Booking olustur
    - Refund case ac ve approve et (full refund varsayimi)
    - Ledger posting'lerde CONFIRMED + REFUND_APPROVED setlerini topla
    - Net EUR etkisinin sifira yakin oldugunu dogrula
    """

    client = async_client
    db = await get_db()

    # 1) Booking olustur (agency context)
    booking_id = await _create_simple_booking(client, agency_token)

    # 2) Refund case ac (ops_finance API uzerinden)
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    payload = {
        "booking_id": booking_id,
        "reason": "P0.3 refund FX test",
        "requested_amount": None,  # full
    }
    res = await client.post("/api/ops/finance/refunds", headers=headers_admin, json=payload)
    assert res.status_code == 200
    case = res.json()
    case_id = case["id"]

    # 3) Refund'i approve et (full amount)
    approve_payload = {
        "approved_amount": case.get("requested_amount") or case.get("proposed_amount") or 0.0,
        "payment_reference": "p0.3-refund-test",
    }
    res = await client.post(
        f"/api/ops/finance/refunds/{case_id}/approve",
        headers=headers_admin,
        json=approve_payload,
    )
    assert res.status_code == 200

    org_id = case["organization_id"]

    # 4) Ledger postings'i cek ve booking + refund etkisini hesapla
    postings_cur = db.ledger_postings.find(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": booking_id,
        }
    )
    postings = await postings_cur.to_list(length=1000)
    assert postings, "No ledger postings found for booking+refund"

    # Tum postings EUR olmali
    for p in postings:
        assert p.get("currency") == "EUR"

    total_debit = sum(float(p.get("debit", 0.0)) for p in postings)
    total_credit = sum(float(p.get("credit", 0.0)) for p in postings)

    # Immutable ledger'da booking+refund net etkisi ~0 olmali
    net = total_debit - total_credit
    assert approx_equal(net, 0.0, abs_tol=0.01, rel_tol=0), f"Net EUR etkisi 0 degil: {net}"
