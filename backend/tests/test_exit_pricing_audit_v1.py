from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

import jwt
import pytest
from bson import ObjectId
from bson.decimal128 import Decimal128
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc
from app.services.pricing_audit_service import emit_pricing_audit_if_needed


@pytest.mark.exit_pricing_audit_v1
@pytest.mark.anyio
async def test_pricing_audit_emitted_for_storefront_booking(test_db: Any, async_client: AsyncClient) -> None:
    """Creating a storefront booking should emit a single PRICING_RULE_APPLIED event."""

    client: AsyncClient = async_client
    now = now_utc()

    # Org + tenant
    org = await test_db.organizations.insert_one(
        {"name": "PricingAuditOrg", "slug": "pricing_audit_org", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "pricing-audit-tenant",
            "organization_id": org_id,
            "brand_name": "Pricing Audit Tenant",
            "primary_domain": "pa.example.com",
            "subdomain": "pa",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    # Pricing rule: 10% markup
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

    # 1) Search
    resp_search = await client.get(
        "/storefront/search",
        headers={"X-Tenant-Key": "pricing-audit-tenant"},
    )
    assert resp_search.status_code == status.HTTP_200_OK
    data_search = resp_search.json()
    search_id = data_search["search_id"]
    offer = data_search["offers"][0]

    # 2) Booking
    resp_book = await client.post(
        "/storefront/bookings",
        json={
            "search_id": search_id,
            "offer_id": offer["offer_id"],
            "customer": {
                "full_name": "Audit Customer",
                "email": "audit@example.com",
                "phone": "+900000000000",
            },
        },
        headers={"X-Tenant-Key": "pricing-audit-tenant"},
    )
    assert resp_book.status_code == status.HTTP_201_CREATED
    data_book = resp_book.json()
    booking_id = data_book["booking_id"]

    # 3) Assert booking.pricing exists
    booking_doc = await test_db.bookings.find_one({"_id": ObjectId(booking_id)})
    assert booking_doc is not None
    pricing = booking_doc.get("pricing") or {}
    assert pricing.get("base_amount") is not None
    assert pricing.get("final_amount") is not None

    # 4) Assert a single PRICING_RULE_APPLIED audit event exists
    logs = await test_db.audit_logs.find(
        {
            "organization_id": org_id,
            "action": "PRICING_RULE_APPLIED",
            "target.id": booking_id,
        }
    ).to_list(length=10)

    assert len(logs) == 1
    log = logs[0]
    meta = log.get("meta") or {}

    assert meta.get("tenant_id") == "pricing-audit-tenant"
    assert meta.get("organization_id") == org_id
    assert meta.get("base_amount") == pricing.get("base_amount")
    assert meta.get("final_amount") == pricing.get("final_amount")
    assert meta.get("currency") == "TRY"

    applied_ids = meta.get("applied_rule_ids") or []
    assert isinstance(applied_ids, list)
    assert applied_ids, "applied_rule_ids should contain the rule id"


@pytest.mark.exit_pricing_audit_v1
@pytest.mark.anyio
async def test_pricing_audit_idempotent_helper(test_db: Any, async_client: AsyncClient) -> None:
    """emit_pricing_audit_if_needed must be idempotent per booking."""

    client: AsyncClient = async_client
    now = now_utc()

    # Org + tenant
    org = await test_db.organizations.insert_one(
        {"name": "PricingAuditOrg2", "slug": "pricing_audit_org2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "pricing-audit-tenant2",
            "organization_id": org_id,
            "brand_name": "Pricing Audit Tenant2",
            "primary_domain": "pa2.example.com",
            "subdomain": "pa2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    # Simple booking doc with pricing but without audit flag
    booking = await test_db.bookings.insert_one(
        {
            "organization_id": org_id,
            "state": "draft",
            "amount": 100.0,
            "currency": "TRY",
            "pricing": {
                "base_amount": "100.00",
                "final_amount": "110.00",
                "commission_amount": "0.00",
                "margin_amount": "10.00",
                "currency": "TRY",
                "applied_rules": [
                    {"rule_id": "rule-1", "rule_type": "markup_pct", "value": "10.0", "priority": 10}
                ],
                "calculated_at": now,
            },
            "created_at": now,
            "updated_at": now,
        }
    )
    booking_id = str(booking.inserted_id)

    # Fake actor/request (minimal) for audit helper
    class DummyRequest:
        def __init__(self) -> None:
            self.headers = {}
            self.url = type("U", (), {"path": "/dummy"})()
            self.method = "POST"
            self.client = None

    dummy_request = DummyRequest()
    actor = {"actor_type": "system", "actor_id": "test", "email": None, "roles": []}

    # Call helper twice
    await emit_pricing_audit_if_needed(test_db, booking_id, None, org_id, actor, dummy_request)  # first
    await emit_pricing_audit_if_needed(test_db, booking_id, None, org_id, actor, dummy_request)  # second

    logs = await test_db.audit_logs.find(
        {
            "organization_id": org_id,
            "action": "PRICING_RULE_APPLIED",
            "target.id": booking_id,
        }
    ).to_list(length=10)

    assert len(logs) == 1

    updated_booking = await test_db.bookings.find_one({"_id": ObjectId(booking_id)})
    assert updated_booking.get("pricing_audit_emitted") is True
