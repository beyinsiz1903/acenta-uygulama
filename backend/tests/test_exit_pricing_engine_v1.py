from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict

import jwt
import pytest
from bson.decimal128 import Decimal128
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc
from app.services.pricing_service import calculate_price


@pytest.mark.exit_pricing_engine_v1
@pytest.mark.anyio
async def test_priority_and_stackable_behavior(test_db: Any) -> None:
    """Higher-priority non-stackable rule should dominate same type."""

    now = now_utc()

    org_id = "org-priority"

    await test_db.pricing_rules.insert_many(
        [
            {
                "organization_id": org_id,
                "tenant_id": None,
                "agency_id": None,
                "supplier": None,
                "rule_type": "markup_pct",
                "value": Decimal128("10.0"),
                "priority": 10,
                "stackable": False,
                "valid_from": now - timedelta(days=1),
                "valid_to": now + timedelta(days=1),
                "created_at": now,
            },
            {
                "organization_id": org_id,
                "tenant_id": None,
                "agency_id": None,
                "supplier": None,
                "rule_type": "markup_pct",
                "value": Decimal128("5.0"),
                "priority": 5,
                "stackable": True,
                "valid_from": now - timedelta(days=1),
                "valid_to": now + timedelta(days=1),
                "created_at": now + timedelta(seconds=1),
            },
        ]
    )

    base = Decimal("100.00")
    pricing = await calculate_price(
        test_db,
        base_amount=base,
        organization_id=org_id,
        currency="TRY",
        tenant_id=None,
        agency_id=None,
        supplier=None,
        now=now,
    )

    # Only 10% rule should apply (non-stackable for markup_pct)
    assert pricing["final_amount"] == Decimal("110.00")
    assert any(r["value"] == "10.0" for r in pricing["applied_rules"])
    assert not any(r["value"] == "5.0" for r in pricing["applied_rules"])


@pytest.mark.exit_pricing_engine_v1
@pytest.mark.anyio
async def test_stacking_markup_and_commission(test_db: Any) -> None:
    """Stack markup_pct and markup_fixed + commission rules deterministically."""

    now = now_utc()
    org_id = "org-stack"

    await test_db.pricing_rules.insert_many(
        [
            {
                "organization_id": org_id,
                "rule_type": "markup_pct",
                "value": Decimal128("10.0"),
                "priority": 10,
                "stackable": True,
                "valid_from": now - timedelta(days=1),
                "valid_to": now + timedelta(days=1),
                "created_at": now,
            },
            {
                "organization_id": org_id,
                "rule_type": "markup_fixed",
                "value": Decimal128("100.0"),
                "priority": 5,
                "stackable": True,
                "valid_from": now - timedelta(days=1),
                "valid_to": now + timedelta(days=1),
                "created_at": now + timedelta(seconds=1),
            },
            {
                "organization_id": org_id,
                "rule_type": "commission_pct",
                "value": Decimal128("5.0"),
                "priority": 1,
                "stackable": True,
                "valid_from": now - timedelta(days=1),
                "valid_to": now + timedelta(days=1),
                "created_at": now + timedelta(seconds=2),
            },
        ]
    )

    base = Decimal("1000.00")
    pricing = await calculate_price(
        test_db,
        base_amount=base,
        organization_id=org_id,
        currency="TRY",
        tenant_id=None,
        agency_id=None,
        supplier=None,
        now=now,
    )

    # markup_pct 10% -> 1100, then +100 -> 1200
    assert pricing["final_amount"] == Decimal("1200.00")
    # commission_pct 5% of base (1000) -> 50
    assert pricing["commission_amount"] == Decimal("50.00")
    # margin = final - base = 200
    assert pricing["margin_amount"] == Decimal("200.00")


@pytest.mark.exit_pricing_engine_v1
@pytest.mark.anyio
async def test_tenant_specific_override(test_db: Any) -> None:
    """Tenant rule with higher priority should override org-global rule of same type."""

    now = now_utc()
    org_id = "org-tenant-override"
    tenant_id = "tenant-1"

    await test_db.pricing_rules.insert_many(
        [
            # Org-global 5%
            {
                "organization_id": org_id,
                "tenant_id": None,
                "rule_type": "markup_pct",
                "value": Decimal128("5.0"),
                "priority": 5,
                "stackable": True,
                "valid_from": now - timedelta(days=1),
                "valid_to": now + timedelta(days=1),
                "created_at": now,
            },
            # Tenant-specific 12% with higher priority
            {
                "organization_id": org_id,
                "tenant_id": tenant_id,
                "rule_type": "markup_pct",
                "value": Decimal128("12.0"),
                "priority": 10,
                "stackable": False,
                "valid_from": now - timedelta(days=1),
                "valid_to": now + timedelta(days=1),
                "created_at": now + timedelta(seconds=1),
            },
        ]
    )

    base = Decimal("100.00")
    pricing = await calculate_price(
        test_db,
        base_amount=base,
        organization_id=org_id,
        currency="TRY",
        tenant_id=tenant_id,
        agency_id=None,
        supplier=None,
        now=now,
    )

    # Only 12% rule should apply
    assert pricing["final_amount"] == Decimal("112.00")
    assert any(r["value"] == "12.0" for r in pricing["applied_rules"])
    assert not any(r["value"] == "5.0" for r in pricing["applied_rules"])


@pytest.mark.exit_pricing_engine_v1
@pytest.mark.anyio
async def test_storefront_booking_persists_pricing(test_db: Any, async_client: AsyncClient) -> None:
    """Storefront-created booking should contain pricing breakdown."""

    client: AsyncClient = async_client
    now = now_utc()

    # Org + tenant
    org = await test_db.organizations.insert_one(
        {"name": "PricingOrgStorefront", "slug": "pricing_org_sf", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "pricing-tenant",
            "organization_id": org_id,
            "brand_name": "Pricing Tenant",
            "primary_domain": "pricing.example.com",
            "subdomain": "pricing",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    # Simple markup rule so pricing is non-trivial
    await test_db.pricing_rules.insert_one(
        {
            "organization_id": org_id,
            "rule_type": "markup_pct",
            "value": Decimal128("10.0"),
            "priority": 10,
            "stackable": True,
            "valid_from": now - timedelta(days=1),
            "valid_to": now + timedelta(days=1),
            "created_at": now,
        }
    )

    # 1) Search to get a storefront offer
    resp_search = await client.get(
        "/storefront/search",
        headers={"X-Tenant-Key": "pricing-tenant"},
    )
    assert resp_search.status_code == status.HTTP_200_OK
    data_search = resp_search.json()
    search_id = data_search["search_id"]
    offer = data_search["offers"][0]

    # 2) Create booking from this offer
    resp_book = await client.post(
        "/storefront/bookings",
        json={
            "search_id": search_id,
            "offer_id": offer["offer_id"],
            "customer": {
                "full_name": "Pricing Customer",
                "email": "pricing@example.com",
                "phone": "+900000000000",
            },
        },
        headers={"X-Tenant-Key": "pricing-tenant"},
    )
    assert resp_book.status_code == status.HTTP_201_CREATED
    data_book = resp_book.json()
    booking_id = data_book["booking_id"]

    # 3) Read booking directly from DB to inspect pricing field
    from bson import ObjectId

    booking_doc = await test_db.bookings.find_one({"_id": ObjectId(booking_id)})

    assert booking_doc is not None
    pricing_block = booking_doc.get("pricing")
    assert pricing_block is not None

    assert pricing_block.get("currency") == "TRY"
    assert pricing_block.get("base_amount") is not None
    assert pricing_block.get("final_amount") is not None
    assert isinstance(pricing_block.get("applied_rules"), list)
