from __future__ import annotations

import pytest
from datetime import date, datetime, timedelta

from app.db import get_db
from app.services.pricing_rules import PricingRulesService
from app.utils import now_utc


@pytest.mark.anyio
async def test_pricing_rules_resolve_default_when_no_rules():
    db = await get_db()
    svc = PricingRulesService(db)

    # Use org_demo
    org = await db.organizations.find_one({})
    org_id = org.get("id") or str(org.get("_id"))

    # Ensure there are no test rules for this org
    await db.pricing_rules.delete_many({"organization_id": org_id, "notes": "test_p1_2"})

    value = await svc.resolve_markup_percent(
        organization_id=org_id,
        agency_id=None,
        product_id=None,
        product_type=None,
        check_in=date.today(),
    )

    assert value == pytest.approx(10.0)


@pytest.mark.anyio
async def test_pricing_rules_selects_highest_priority_and_scope_match():
    db = await get_db()
    svc = PricingRulesService(db)

    org = await db.organizations.find_one({})
    org_id = org.get("id") or str(org.get("_id"))

    # Clean previous test rules
    await db.pricing_rules.delete_many({"organization_id": org_id, "notes": "test_p1_2"})

    today = date.today()
    v_from = today.strftime("%Y-%m-%d")
    v_to = (today + timedelta(days=365)).strftime("%Y-%m-%d")

    now = now_utc()

    # Default hotel rule: 10%
    await db.pricing_rules.insert_one(
        {
            "organization_id": org_id,
            "status": "active",
            "priority": 100,
            "scope": {"product_type": "hotel"},
            "validity": {"from": v_from, "to": v_to},
            "action": {"type": "markup_percent", "value": 10.0},
            "notes": "test_p1_2",
            "created_at": now,
            "updated_at": now,
        }
    )

    # Agency-specific rule: 12%
    agency_id = "agency_test_1"
    await db.pricing_rules.insert_one(
        {
            "organization_id": org_id,
            "status": "active",
            "priority": 200,
            "scope": {"agency_id": agency_id, "product_type": "hotel"},
            "validity": {"from": v_from, "to": v_to},
            "action": {"type": "markup_percent", "value": 12.0},
            "notes": "test_p1_2",
            "created_at": now,
            "updated_at": now,
        }
    )

    # 1) agency-specific match -> 12%
    value_agency = await svc.resolve_markup_percent(
        organization_id=org_id,
        agency_id=agency_id,
        product_id="prod1",
        product_type="hotel",
        check_in=today,
    )
    assert value_agency == pytest.approx(12.0)

    # 2) other agency -> default hotel rule 10%
    value_other = await svc.resolve_markup_percent(
        organization_id=org_id,
        agency_id="another_agency",
        product_id="prod1",
        product_type="hotel",
        check_in=today,
    )
    assert value_other == pytest.approx(10.0)


@pytest.mark.anyio
async def test_pricing_rules_ignores_inactive_and_out_of_range():
    db = await get_db()
    svc = PricingRulesService(db)

    org = await db.organizations.find_one({})
    org_id = org.get("id") or str(org.get("_id"))

    await db.pricing_rules.delete_many({"organization_id": org_id, "notes": "test_p1_2_range"})

    today = date.today()
    now = now_utc()

    # Inactive rule (should be ignored)
    await db.pricing_rules.insert_one(
        {
            "organization_id": org_id,
            "status": "inactive",
            "priority": 300,
            "scope": {"product_type": "hotel"},
            "validity": {"from": "2026-01-01", "to": "2027-01-01"},
            "action": {"type": "markup_percent", "value": 50.0},
            "notes": "test_p1_2_range",
            "created_at": now,
            "updated_at": now,
        }
    )

    # Out-of-range rule (date window geçmişte)
    await db.pricing_rules.insert_one(
        {
            "organization_id": org_id,
            "status": "active",
            "priority": 400,
            "scope": {"product_type": "hotel"},
            "validity": {"from": "2000-01-01", "to": "2001-01-01"},
            "action": {"type": "markup_percent", "value": 30.0},
            "notes": "test_p1_2_range",
            "created_at": now,
            "updated_at": now,
        }
    )

    # No active/in-range rules for today -> fallback 10%
    value = await svc.resolve_markup_percent(
        organization_id=org_id,
        agency_id=None,
        product_id=None,
        product_type="hotel",
        check_in=today,
    )

    assert value == pytest.approx(10.0)
