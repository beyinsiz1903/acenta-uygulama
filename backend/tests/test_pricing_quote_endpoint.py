from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.db import get_db


@pytest.mark.anyio
async def test_pricing_quote_endpoint_with_simple_rule(async_client, admin_token):
    """End-to-end test for POST /api/pricing/quote using existing simple rules.

    Flow:
    - Resolve org_id for current test context
    - Clean previous test rules for this org (by notes)
    - Create a simple pricing rule via /api/admin/pricing/rules/simple
    - Call /api/pricing/quote with matching context
    - Expect markup_percent and final_price consistent with rule
    """

    client = async_client
    headers = {"Authorization": f"Bearer {admin_token}"}

    db = await get_db()
    org = await db.organizations.find_one({})
    org_id = org.get("id") or str(org.get("_id"))

    # Clean previous test rules for idempotency
    await db.pricing_rules.delete_many({"organization_id": org_id, "notes": "test_pricing_quote"})

    today = date.today()
    v_from = today.strftime("%Y-%m-%d")
    v_to = (today + timedelta(days=365)).strftime("%Y-%m-%d")

    # Create a high-priority simple rule: 10% markup for all hotels
    rule_payload = {
        "priority": 10_000,
        "scope": {"product_type": "hotel"},
        "validity": {"from": v_from, "to": v_to},
        "action": {"type": "markup_percent", "value": 10.0},
        "notes": "test_pricing_quote",
    }

    resp_rule = await client.post("/api/admin/pricing/rules/simple", json=rule_payload, headers=headers)
    assert resp_rule.status_code == 200, resp_rule.text

    # Now call the pricing quote endpoint with base_price=1000
    quote_payload = {
        "base_price": 1000.0,
        "currency": "TRY",
        "context": {
            "product_type": "hotel",
            "check_in": v_from,
        },
    }

    resp_quote = await client.post("/api/pricing/quote", json=quote_payload, headers=headers)
    assert resp_quote.status_code == 200, resp_quote.text

    data = resp_quote.json()
    assert data["currency"] == "TRY"
    assert data["base_price"] == 1000.0
    # Expect 10% markup on 1000 -> 1100
    assert data["markup_percent"] == pytest.approx(10.0)
    assert data["final_price"] == pytest.approx(1100.0)
    assert data["breakdown"]["markup_amount"] == pytest.approx(100.0)
