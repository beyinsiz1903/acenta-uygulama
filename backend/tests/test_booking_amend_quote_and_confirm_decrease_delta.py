from __future__ import annotations

from datetime import timedelta

import pytest

from app.db import get_db
from app.utils import now_utc


@pytest.mark.anyio
async def test_booking_amend_quote_and_confirm_decrease_delta(async_client, agency_token):
    """P1.5: Amend flow (quote + confirm) with negative delta.

    Senaryo:
    - EUR bir booking yarat (manual insert) ve sell_eur=100.0 kabul et
    - Yeni tarih icin inventory fiyatini daha dusuk ayarla
    - /api/b2b/bookings/{id}/amend/quote cagir, delta.sell_eur < 0 bekle
    - /api/b2b/bookings/{id}/amend/confirm cagir
    - Booking dokumaninda tarihler ve amounts.sell_eur guncellenmis olmali
    - booking_financials mirror sell_total_eur == booking.amounts.sell_eur
    - Ledger'da tek bir BOOKING_AMENDED posting olmali ve tutar ~= abs(delta_eur)
    """

    client = async_client
    db = await get_db()

    # 1) Agency context
    headers = {"Authorization": f"Bearer {agency_token}"}
    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    me_data = me.json()
    org_id = me_data.get("organization_id")
    agency_id = me_data.get("agency_id")
    if not agency_id:
        pytest.skip("Agency user does not have agency_id")

    # 2) EUR hotel product sec
    prod = await db.products.find_one(
        {
            "organization_id": org_id,
            "type": "hotel",
            "status": "active",
            "default_currency": "EUR",
        }
    )
    if not prod:
        pytest.skip("No active EUR hotel product found for org")

    product_oid = prod["_id"]

    # 3) Iki tarih icin inventory olustur: ikinci tarih daha ucuz
    today = now_utc().date()
    check_in_1 = today + timedelta(days=30)
    check_out_1 = check_in_1 + timedelta(days=1)
    check_in_2 = today + timedelta(days=40)
    check_out_2 = check_in_2 + timedelta(days=1)

    date1 = check_in_1.isoformat()
    date2 = check_in_2.isoformat()

    # Base fiyatlar: 120 -> 80 (delta < 0 bekliyoruz)
    await db.inventory.update_one(
        {
            "organization_id": org_id,
            "product_id": product_oid,
            "date": date1,
        },
        {
            "$set": {
                "capacity_total": 10,
                "capacity_available": 10,
                "price": 120.0,
                "restrictions": {"closed": False, "cta": False, "ctd": False},
            }
        },
        upsert=True,
    )

    await db.inventory.update_one(
        {
            "organization_id": org_id,
            "product_id": product_oid,
            "date": date2,
        },
        {
            "$set": {
                "capacity_total": 10,
                "capacity_available": 10,
                "price": 80.0,
                "restrictions": {"closed": False, "cta": False, "ctd": False},
            }
        },
        upsert=True,
    )

    # 4) Baslangic booking (CONFIRMED, EUR, sell_eur=100)
    now = now_utc()
    booking_doc = {
        "organization_id": org_id,
        "agency_id": agency_id,
        "status": "CONFIRMED",
        "currency": "EUR",
        "amounts": {"sell": 100.0, "sell_eur": 100.0},
        "items": [
            {
                "type": "hotel",
                "product_id": str(product_oid),
                "room_type_id": "std",
                "rate_plan_id": "rp_test_dec",
                "check_in": check_in_1.isoformat(),
                "check_out": check_out_1.isoformat(),
                "occupancy": 2,
                "net": 100.0,
                "sell": 100.0,
            }
        ],
        "created_at": now,
        "updated_at": now,
    }

    res = await db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    # 5) Amend quote (daha ucuz tarihe)
    quote_payload = {
        "check_in": check_in_2.isoformat(),
        "check_out": check_out_2.isoformat(),
        "request_id": "test_dec_delta_1",
    }

    r_quote = await client.post(
        f"/api/b2b/bookings/{booking_id}/amend/quote",
        json=quote_payload,
        headers=headers,
    )
    assert r_quote.status_code == 200, r_quote.text
    q = r_quote.json()

    assert q["booking_id"] == booking_id
    assert q["status"] == "PROPOSED"
    delta = q.get("delta") or {}
    delta_sell_eur = float(delta.get("sell_eur", 0.0))

    # Beklenti: delta < 0 (fiyat dususu)
    assert delta_sell_eur < 0.0

    amend_id = q.get("amend_id")
    assert amend_id

    # 6) Confirm
    r_conf = await client.post(
        f"/api/b2b/bookings/{booking_id}/amend/confirm",
        json={"amend_id": amend_id},
        headers=headers,
    )
    assert r_conf.status_code == 200, r_conf.text
    c = r_conf.json()
    assert c["booking_id"] == booking_id
    assert c["status"] == "CONFIRMED"

    # 7) Booking dokumani guncellenmis mi?
    booking_after = await db.bookings.find_one({"_id": res.inserted_id, "organization_id": org_id})
    assert booking_after is not None
    item_after = (booking_after.get("items") or [{}])[0]

    assert item_after.get("check_in") == check_in_2.isoformat()
    assert item_after.get("check_out") == check_out_2.isoformat()

    amounts_after = booking_after.get("amounts") or {}
    sell_after = float(amounts_after.get("sell", 0.0))
    sell_eur_after = float(amounts_after.get("sell_eur", 0.0))

    assert sell_after > 0
    assert sell_eur_after > 0

    # 8) booking_financials mirror: totals booking ile ayni olmali
    bf = await db.booking_financials.find_one(
        {"organization_id": org_id, "booking_id": booking_id}
    )
    assert bf is not None, "booking_financials must exist after amend confirm"
    assert float(bf.get("sell_total", 0.0)) == pytest.approx(sell_after)
    assert float(bf.get("sell_total_eur", 0.0)) == pytest.approx(sell_eur_after)

    # 9) Ledger: BOOKING_AMENDED delta posting (mutlak deger + yon kontrolu)
    postings = await db.ledger_postings.find(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": booking_id,
            "event": "BOOKING_AMENDED",
            "meta.amend_id": amend_id,
        }
    ).to_list(length=10)

    assert len(postings) == 1, f"Expected 1 BOOKING_AMENDED posting, got {len(postings)}"
    p = postings[0]
    posting_id = p.get("_id")
    assert p.get("currency") == "EUR"

    lines = p.get("lines") or []
    assert len(lines) == 2

    # Direction & amount: delta < 0 => agency credit, platform debit, amount = |delta_eur|
    agency_accounts = await db.finance_accounts.find(
        {"organization_id": org_id, "type": "agency", "owner_id": agency_id}
    ).to_list(length=10)
    platform_accounts = await db.finance_accounts.find(
        {"organization_id": org_id, "type": "platform"}
    ).to_list(length=10)
    agency_ids = {str(a["_id"]) for a in agency_accounts}
    platform_ids = {str(a["_id"]) for a in platform_accounts}

    agency_lines = [ln for ln in lines if ln.get("account_id") in agency_ids]
    platform_lines = [ln for ln in lines if ln.get("account_id") in platform_ids]

    assert len(agency_lines) == 1, f"Expected 1 agency line, got {len(agency_lines)}"
    assert len(platform_lines) == 1, f"Expected 1 platform line, got {len(platform_lines)}"

    agency_line = agency_lines[0]
    platform_line = platform_lines[0]

    assert agency_line.get("direction") == "credit"
    assert platform_line.get("direction") == "debit"

    amt_agency = float(agency_line.get("amount", 0.0))
    amt_platform = float(platform_line.get("amount", 0.0))
    assert amt_agency == pytest.approx(abs(delta_sell_eur), abs=0.05)
    assert amt_platform == pytest.approx(abs(delta_sell_eur), abs=0.05)

    total_debit = sum(float(ln.get("amount", 0.0)) for ln in lines if ln.get("direction") == "debit")
    total_credit = sum(float(ln.get("amount", 0.0)) for ln in lines if ln.get("direction") == "credit")

    assert total_debit == pytest.approx(total_credit, abs=0.01)
    assert total_debit == pytest.approx(abs(delta_sell_eur), abs=0.05)

    # 10) Confirm idempotency: ikinci confirm yeni posting olusturmamali
    r_conf2 = await client.post(
        f"/api/b2b/bookings/{booking_id}/amend/confirm",
        json={"amend_id": amend_id},
        headers=headers,
    )
    assert r_conf2.status_code == 200, r_conf2.text

    postings_after = await db.ledger_postings.find(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": booking_id,
            "event": "BOOKING_AMENDED",
            "meta.amend_id": amend_id,
        }
    ).to_list(length=10)

    assert len(postings_after) == 1
    assert postings_after[0].get("_id") == posting_id
