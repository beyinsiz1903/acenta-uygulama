from __future__ import annotations

import pytest
from datetime import date, timedelta

from app.db import get_db
from app.services.pricing_rules import PricingRulesService
from app.utils import now_utc


@pytest.mark.anyio
async def test_admin_pricing_simple_rule_create_list_and_resolve(async_client, admin_token):
    """Create a simple pricing rule over Admin API and verify it is used by PricingRulesService.

    Flow:
    - Clean previous test rules for org
    - Create a simple rule via POST /api/admin/pricing/rules/simple
    - List rules via GET /api/admin/pricing/rules
    - Call PricingRulesService.resolve_markup_percent and expect the created value
    """

    client = async_client
    headers = {"Authorization": f"Bearer {admin_token}"}
    db = await get_db()

    # Resolve org_id from admin token context
    org = await db.organizations.find_one({})
    org_id = org.get("id") or str(org.get("_id"))

    # Clean previous test rules
    await db.pricing_rules.delete_many({"organization_id": org_id, "notes": "test_admin_simple"})

    today = date.today()
    v_from = today.strftime("%Y-%m-%d")
    v_to = (today + timedelta(days=365)).strftime("%Y-%m-%d")

    # Create simple rule via API: 15% markup for all hotels
    payload = {
        "priority": 150,
        "scope": {"product_type": "hotel"},
        "validity": {"from": v_from, "to": v_to},
        "action": {"type": "markup_percent", "value": 15.0},
        "notes": "test_admin_simple",
    }

    resp = await client.post("/api/admin/pricing/rules/simple", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["priority"] == 150
    assert data["action"]["type"] == "markup_percent"
    assert data["action"]["value"] == 15.0

    # List rules and ensure our rule appears
    resp_list = await client.get("/api/admin/pricing/rules", headers=headers)
    assert resp_list.status_code == 200, resp_list.text
    items = resp_list.json()
    assert any(r.get("notes") == "test_admin_simple" for r in items)

    # Now resolve via service and expect 15.0
    svc = PricingRulesService(db)
    value = await svc.resolve_markup_percent(
        organization_id=org_id,
        agency_id=None,
        product_id=None,
        product_type="hotel",
        check_in=today,
    )
    assert value == pytest.approx(15.0)


@pytest.mark.anyio
async def test_admin_pricing_simple_rule_update_priority_changes_resolution(async_client, admin_token):
    """Update rule priority and verify resolution changes accordingly."""

    client = async_client
    headers = {"Authorization": f"Bearer {admin_token}"}
    db = await get_db()

    org = await db.organizations.find_one({})
    org_id = org.get("id") or str(org.get("_id"))

    await db.pricing_rules.delete_many({"organization_id": org_id, "notes": "test_admin_simple_update"})

    today = date.today()
    v_from = today.strftime("%Y-%m-%d")
    v_to = (today + timedelta(days=365)).strftime("%Y-%m-%d")

    # Rule A: priority 100, 10%
    payload_a = {
        "priority": 100,
        "scope": {"product_type": "hotel"},
        "validity": {"from": v_from, "to": v_to},
        "action": {"type": "markup_percent", "value": 10.0},
        "notes": "test_admin_simple_update",
    }
    resp_a = await client.post("/api/admin/pricing/rules/simple", json=payload_a, headers=headers)
    assert resp_a.status_code == 200, resp_a.text

    # Rule B: priority 200, 20%
    payload_b = {
        "priority": 200,
        "scope": {"product_type": "hotel"},
        "validity": {"from": v_from, "to": v_to},
        "action": {"type": "markup_percent", "value": 20.0},
        "notes": "test_admin_simple_update",
    }
    resp_b = await client.post("/api/admin/pricing/rules/simple", json=payload_b, headers=headers)
    assert resp_b.status_code == 200, resp_b.text
    rule_b = resp_b.json()

    svc = PricingRulesService(db)

    # With priorities 100 and 200, expect 20%
    value_initial = await svc.resolve_markup_percent(
        organization_id=org_id,
        agency_id=None,
        product_id=None,
        product_type="hotel",
        check_in=today,
    )
    assert value_initial == pytest.approx(20.0)

    # Downgrade rule B priority to 50
    update_payload = {"priority": 50}
    resp_upd = await client.put(f"/api/admin/pricing/rules/{rule_b['rule_id']}", json=update_payload, headers=headers)
    assert resp_upd.status_code == 200, resp_upd.text

    # Now highest priority is 100 (rule A) -> expect 10%
    value_after = await svc.resolve_markup_percent(
        organization_id=org_id,
        agency_id=None,
        product_id=None,
        product_type="hotel",
        check_in=today,
    )
    assert value_after == pytest.approx(10.0)
