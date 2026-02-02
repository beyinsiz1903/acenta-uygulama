from __future__ import annotations

from typing import Any

import jwt
import pytest
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


async def _seed_pricing_rule(test_db: Any, organization_id: str, agency_id: str, markup_pct: float) -> None:
    now = now_utc()
    doc = {
        "organization_id": organization_id,
        "status": "active",
        "priority": 100,
        "scope": {"agency_id": agency_id, "product_type": "hotel"},
        "validity": {},
        "action": {"type": "markup_percent", "value": markup_pct},
        "updated_at": now,
    }
    await test_db.pricing_rules.insert_one(doc)


@pytest.mark.exit_b2b_pricing_overlay_applied
@pytest.mark.anyio
async def test_b2b_pricing_overlay_applied_on_canonical_offers(test_db: Any, async_client: AsyncClient) -> None:
    """When pricing rule exists, b2b_pricing overlay should be applied with correct markup."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "PR18 Org1", "slug": "pr18_org1", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "tenant-pr18-1",
            "organization_id": org_id,
            "brand_name": "Tenant PR18 1",
            "primary_domain": "tenant-pr18-1.example.com",
            "subdomain": "tenant-pr18-1",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "pr18-1@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    # Seed pricing rule with 10% markup
    await _seed_pricing_rule(test_db, organization_id=org_id, agency_id="tenant-pr18-1", markup_pct=10.0)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "tenant-pr18-1",
    }

    payload = {
        "destination": "IST",
        "check_in": "2025-06-01",
        "check_out": "2025-06-05",
        "adults": 2,
        "children": 0,
        "supplier_codes": ["mock"],
    }

    resp = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    offers = data.get("offers") or []
    assert offers

    offer = offers[0]
    price = offer["price"]
    b2b = offer.get("b2b_pricing")
    assert b2b is not None

    base_amount = float(price["amount"])
    final_amount = float(b2b["final_price"]["amount"])

    # Base price must remain unchanged
    assert b2b["base_price"]["amount"] == base_amount
    assert b2b["base_price"]["currency"] == price["currency"]

    # Final price currency must match base price currency
    assert b2b["final_price"]["currency"] == price["currency"]

    # 10% markup applied
    expected_final = round(base_amount * 1.10, 2)
    assert final_amount == expected_final
    assert float(b2b["applied_markup_pct"]) == 10.0
    assert isinstance(b2b.get("pricing_rule_id"), str) or b2b.get("pricing_rule_id") is None


@pytest.mark.exit_b2b_pricing_no_rule
@pytest.mark.anyio
async def test_b2b_pricing_default_when_no_rule(test_db: Any, async_client: AsyncClient) -> None:
    """When no pricing rule is present, overlay should default to 0% markup."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "PR18 Org2", "slug": "pr18_org2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "tenant-pr18-2",
            "organization_id": org_id,
            "brand_name": "Tenant PR18 2",
            "primary_domain": "tenant-pr18-2.example.com",
            "subdomain": "tenant-pr18-2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "pr18-2@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "tenant-pr18-2",
    }

    payload = {
        "destination": "IST",
        "check_in": "2025-06-01",
        "check_out": "2025-06-05",
        "adults": 2,
        "children": 0,
        "supplier_codes": ["mock"],
    }

    resp = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    offers = data.get("offers") or []
    assert offers

    offer = offers[0]
    price = offer["price"]
    b2b = offer.get("b2b_pricing")
    assert b2b is not None

    base_amount = float(price["amount"])
    final_amount = float(b2b["final_price"]["amount"])

    # 0% markup: final == base
    assert float(b2b["applied_markup_pct"]) == 0.0
    assert final_amount == round(base_amount, 2)
    assert b2b.get("pricing_rule_id") is None


@pytest.mark.exit_booking_repricing_consistency
@pytest.mark.anyio
async def test_booking_repricing_consistency_with_canonical_offer(test_db: Any, async_client: AsyncClient) -> None:
    """Booking amount should match b2b_pricing.final_price from canonical offer re-evaluation."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "PR18 Org3", "slug": "pr18_org3", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "tenant-pr18-3",
            "organization_id": org_id,
            "brand_name": "Tenant PR18 3",
            "primary_domain": "tenant-pr18-3.example.com",
            "subdomain": "tenant-pr18-3",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "pr18-3@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    # Seed pricing rule with 15% markup
    await _seed_pricing_rule(test_db, organization_id=org_id, agency_id="tenant-pr18-3", markup_pct=15.0)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "tenant-pr18-3",
    }

    # 1) Search canonical offers
    payload = {
        "destination": "IST",
        "check_in": "2025-06-01",
        "check_out": "2025-06-02",
        "adults": 1,
        "children": 0,
        "supplier_codes": ["mock"],
    }

    resp_search = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp_search.status_code == status.HTTP_200_OK, resp_search.text
    search_data = resp_search.json()
    session_id = search_data["session_id"]
    offers = search_data.get("offers") or []
    assert offers
    offer = offers[0]

    price = offer["price"]
    b2b = offer.get("b2b_pricing")
    assert b2b is not None

    # 2) Create booking from canonical offer
    create_payload = {
        "session_id": session_id,
        "offer_token": offer["offer_token"],
        "buyer_tenant_id": "tenant-pr18-3",
        "customer": {
            "full_name": "PR18 Customer",
            "email": "pr18-3@example.com",
        },
    }

    resp_booking = await client.post("/api/bookings/from-canonical-offer", json=create_payload, headers=headers)
    assert resp_booking.status_code == status.HTTP_201_CREATED, resp_booking.text
    booking = resp_booking.json()

    # booking.pricing.base_amount must equal canonical base price
    pricing = booking.get("pricing") or {}
    assert float(pricing.get("base_amount")) == float(price["amount"])
    # booking.amount must equal final_amount from repricing
    assert float(booking.get("amount")) == float(pricing.get("final_amount"))
    # pricing_rule_id must be string or null
    assert isinstance(pricing.get("pricing_rule_id"), str) or pricing.get("pricing_rule_id") is None
