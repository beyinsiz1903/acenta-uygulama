from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.db import get_db
from app.utils import now_utc


@pytest.mark.anyio
async def test_quote_pricing_uses_rules_for_agency1_vs_other(async_client, admin_token, agency_token):
    """P1.2: POST /api/b2b/quotes tarafında rule-based markup oranını doğrular.

    Beklentiler:
    - agency1 (settings.selling_currency=TRY, demo org) için: offer.sell / offer.net ≈ 1.12 (12% markup)
    - başka bir agency için: offer.sell / offer.net ≈ 1.10 (10% markup)

    TRY flow aktif olsun veya olmasın, oranlar aynı kalmalıdır; sadece currency EUR/TRY olabilir.
    """

    client = async_client
    db = await get_db()

    # Hazırlık: org ve agency dokümanlarını bul
    org = await db.organizations.find_one({})
    assert org is not None
    org_id = org.get("id") or str(org.get("_id"))

    agency1 = await db.agencies.find_one({"organization_id": org_id, "name": "Demo Acente A"})
    assert agency1 is not None
    agency1_id = agency1["_id"]

    # Demo'da ikinci bir acente varsa onu "other" agency olarak kullan, yoksa SKIP
    other_agency = await db.agencies.find_one({"organization_id": org_id, "_id": {"$ne": agency1_id}})
    if not other_agency:
        pytest.skip("No second agency found to compare rule-based pricing")

    other_agency_id = other_agency["_id"]

    # Inventory'de satışa açık bir ürün bul (her iki agency de aynı ürünü kullanıyor)
    inv = await db.inventory.find_one({"organization_id": org_id})
    assert inv is not None, "No inventory found for demo org; seed should create one."

    product_id = str(inv["product_id"])
    check_in_str = inv["date"]  # ISO string
    check_in = date.fromisoformat(check_in_str)
    check_out = check_in + timedelta(days=1)

    # Ortak quote payload
    payload = {
        "channel_id": "b2b_demo",
        "items": [
            {
                "product_id": product_id,
                "room_type_id": inv.get("room_type_id", "standard"),
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "adults": 2,
                "children": [],
            }
        ],
        "client_context": {},
    }

    # 1) agency1 için quote oluştur
    # Agency fixture zaten agency1 kullanıcısı ile login olmuş client döndürüyor
    headers_agency1 = {"Authorization": f"Bearer {agency_token}"}

    resp_a1 = await client.post("/api/b2b/quotes", json=payload, headers=headers_agency1)
    assert resp_a1.status_code == 200, resp_a1.text
    qa = resp_a1.json()
    assert qa["offers"], "No offers returned for agency1"

    offer_a1 = qa["offers"][0]
    net_a1 = float(offer_a1["net"])
    sell_a1 = float(offer_a1["sell"])
    ratio_a1 = sell_a1 / net_a1 if net_a1 > 0 else 0.0

    # 2) Diğer agency için admin üzerinden impersonation ile quote oluşturmamız gerekir.
    # Şu an b2b_quotes endpoint'i user'ın agency_id'sini user objesinden alıyor.
    # Bu test için sadece oran bilgisini kontrol etmek istiyoruz; eğer doğrudan
    # ikinci agency kullanıcısı seed'de yoksa bu kısmı SKIP edebiliriz.

    other_user = await db.users.find_one({"agency_id": other_agency_id})
    if not other_user:
        pytest.skip("No user bound to second agency; cannot test cross-agency pricing differences")

    # Diğer agency kullanıcı token'ını manuel olarak al
    from app.auth import create_access_token

    token_other = create_access_token(
        {
            "sub": str(other_user["_id"]),
            "email": other_user["email"],
            "organization_id": org_id,
            "agency_id": other_agency_id,
            "roles": other_user.get("roles", []),
        }
    )
    headers_other = {"Authorization": f"Bearer {token_other}"}

    resp_other = await client.post("/api/b2b/quotes", json=payload, headers=headers_other)
    assert resp_other.status_code == 200, resp_other.text
    qb = resp_other.json()
    assert qb["offers"], "No offers returned for other agency"

    offer_other = qb["offers"][0]
    net_other = float(offer_other["net"])
    sell_other = float(offer_other["sell"])
    ratio_other = sell_other / net_other if net_other > 0 else 0.0

    # Beklenen oranlar: 1.12 ve 1.10 civari (tolerans ile)
    assert 1.11 <= ratio_a1 <= 1.13, f"agency1 markup ratio expected ~1.12, got {ratio_a1}"
    assert 1.09 <= ratio_other <= 1.11, f"other agency markup ratio expected ~1.10, got {ratio_other}"
