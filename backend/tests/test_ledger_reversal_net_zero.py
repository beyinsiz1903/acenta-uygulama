from __future__ import annotations

import math
import time

import pytest

from app.db import get_db


def approx_equal(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


@pytest.mark.anyio
async def test_ledger_reversal_net_zero(async_client, admin_token):
    """BOOKING_CONFIRMED + REFUND_APPROVED net EUR etkisinin ~0 oldugunu kanitlar.

    Bu test sadece _test/posting endpoint'ini kullanir (Phase 1.3 debug araci):
    - 100 EUR tutarinda BOOKING_CONFIRMED posting olusturur
    - Ayni source_id icin 100 EUR REFUND_APPROVED posting olusturur
    - ledger_postings ve ledger_entries uzerinden:
      * Her event setinin kendi icinde balanced oldugunu
      * Ikisinin birlikte net etkinin ~0 EUR oldugunu dogrular
    """

    client = async_client
    db = await get_db()

    # Unique source_id to avoid interference with other tests
    source_id = f"TEST_BKG_{int(time.time())}"
    payload_base = {
        "source_type": "booking",
        "source_id": source_id,
        "agency_account_id": "AGENCY_TEST",
        "platform_account_id": "PLATFORM_TEST",
        "amount": 100.0,
    }

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1) Booking confirmed event
    r1 = await client.post(
        "/api/ops/finance/_test/posting",
        headers=headers,
        json={**payload_base, "event": "BOOKING_CONFIRMED"},
    )
    assert r1.status_code == 200, r1.text
    post1 = r1.json()

    # 2) Refund approved event
    r2 = await client.post(
        "/api/api/ops/finance/_test/posting",
        headers=headers,
        json={**payload_base, "event": "REFUND_APPROVED"},
    )
    assert r2.status_code == 200, r2.text
    post2 = r2.json()

    org_id = post1.get("organization_id") or post2.get("organization_id")
    assert org_id, "organization_id not returned from _test/posting"

    # 3) Load ledger docs (postings or entries)
    query = {
        "organization_id": org_id,
        "source.type": "booking",
        "source.id": source_id,
    }
    projection = {
        "_id": 0,
        "currency": 1,
        "debit": 1,
        "credit": 1,
        "event": 1,
        "lines": 1,
    }

    docs = await db.ledger_postings.find(query, projection).to_list(length=100)
    source_collection = "ledger_postings"
    if not docs:
        docs = await db.ledger_entries.find(query, projection).to_list(length=200)
        source_collection = "ledger_entries"

    assert docs, f"No ledger docs found in {source_collection} for {source_id}"

    # Flatten lines if needed (for ledger_postings -> lines[])
    flat = []
    for d in docs:
        if "debit" in d or "credit" in d:
            flat.append(d)
        elif isinstance(d.get("lines"), list):
            for ln in d["lines"]:
                flat.append(
                    {
                        "currency": ln.get("currency") or d.get("currency"),
                        "debit": ln.get("debit", 0.0),
                        "credit": ln.get("credit", 0.0),
                        "event": d.get("event"),
                    }
                )
        else:
            flat.append(d)

    # All EUR
    for d in flat:
        cur = d.get("currency")
        assert cur == "EUR", f"Non-EUR currency found: {cur}"

    confirm = [d for d in flat if d.get("event") == "BOOKING_CONFIRMED"]
    refund = [d for d in flat if d.get("event") == "REFUND_APPROVED"]

    assert confirm, f"No BOOKING_CONFIRMED docs in {source_collection}"
    assert refund, f"No REFUND_APPROVED docs in {source_collection}"

    def sums(rows):
        td = sum(float(x.get("debit", 0.0) or 0.0) for x in rows)
        tc = sum(float(x.get("credit", 0.0) or 0.0) for x in rows)
        return td, tc

    c_debit, c_credit = sums(confirm)
    r_debit, r_credit = sums(refund)

    tol_confirm = max(0.01, max(c_debit, c_credit) * 0.001)
    tol_refund = max(0.01, max(r_debit, r_credit) * 0.001)

    assert approx_equal(c_debit, c_credit, tol_confirm), (
        "BOOKING_CONFIRMED unbalanced",
        c_debit,
        c_credit,
        tol_confirm,
    )
    assert approx_equal(r_debit, r_credit, tol_refund), (
        "REFUND_APPROVED unbalanced",
        r_debit,
        r_credit,
        tol_refund,
    )

    net = (c_debit - c_credit) + (r_debit - r_credit)
    tol_net = max(0.01, max(c_debit, c_credit, r_debit, r_credit) * 0.001)
    assert abs(net) <= tol_net, f"net_effect_EUR != 0 (net={net}, tol={tol_net})"
