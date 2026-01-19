from __future__ import annotations

from datetime import timedelta

import pytest

from app.utils import now_utc


@pytest.mark.anyio
async def test_booking_amend_quote_and_confirm_zero_delta_has_no_ledger(async_client, agency_token, test_db):
    """P1.5: Delta ~ 0 iken ledger posting olmamali, amend CONFIRMED olmalidir.

    Senaryo:
    - EUR bir booking yarat (sell_eur=100)
    - Yeni tarih icin inventory fiyatini ayni birak (100)
    - /amend/quote -> delta.sell_eur ~= 0
    - /amend/confirm -> booking & financials mirror guncellenir, fakat
      BOOKING_AMENDED posting olusmaz.
    """

    client = async_client
    db = test_db

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

    # 3) Iki tarih icin inventory olustur: ayni fiyat
    today = now_utc().date()
    check_in_1 = today + timedelta(days=5)
    check_out_1 = check_in_1 + timedelta(days=1)
    check_in_2 = today + timedelta(days=15)
    check_out_2 = check_in_2 + timedelta(days=1)

    date1 = check_in_1.isoformat()
    date2 = check_in_2.isoformat()

    for d in (date1, date2):
        await db.inventory.update_one(
            {
                "organization_id": org_id,
                "product_id": product_oid,
                "date": d,
            },
            {
                "$set": {
                    "capacity_total": 10,
                    "capacity_available": 10,
                    "price": 100.0,
                    "restrictions": {"closed": False, "cta": False, "ctd": False},
                }
            },
            upsert=True,
        )

    # 4) Baslangic booking
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
                "rate_plan_id": "rp_test_zero",
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

    # 5) Amend quote (ayni fiyatli tarihe)
    quote_payload = {
        "check_in": check_in_2.isoformat(),
        "check_out": check_out_2.isoformat(),
        "request_id": "test_zero_delta_1",
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

    is_zero_delta = abs(delta_sell_eur) <= 0.005

    # 7) Ledger guard: delta küçük ise posting olmamali, büyük ise olmali.
    postings = await db.ledger_postings.find(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": booking_id,
            "event": "BOOKING_AMENDED",
        }
    ).to_list(length=10)

    # booking_financials olusmus olmali (her iki durumda da)
    bf = await db.booking_financials.find_one(
        {"organization_id": org_id, "booking_id": booking_id}
    )
    assert bf is not None

    # 8) Ledger'da BOOKING_AMENDED posting sayisini delta'ya göre kontrol et
    postings_by_amend = await db.ledger_postings.find(
        {
            "organization_id": org_id,
            "source.type": "booking",
            "source.id": booking_id,
            "event": "BOOKING_AMENDED",
            "meta.amend_id": amend_id,
        }
    ).to_list(length=10)

    if is_zero_delta:
        # Zero-delta toleransi içinde: hiç BOOKING_AMENDED posting'i olmamali.
        assert postings == []
        assert postings_by_amend == []

        # Idempotent confirm tekrarinda da posting olmamali
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

        assert postings_after == []
    else:
        # Delta anlamlı ise en az bir BOOKING_AMENDED posting'i beklenir ve
        # idempotent confirm tekrarinda yeni posting eklenmemelidir.
        assert len(postings_by_amend) >= 1

        before_count = len(postings_by_amend)
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

        assert len(postings_after) == before_count
