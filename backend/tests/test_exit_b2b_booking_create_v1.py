from __future__ import annotations

from typing import Any

import jwt
import pytest
from bson import Decimal128, ObjectId
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.exit_b2b_booking_create_v1
@pytest.mark.anyio
async def test_b2b_booking_create_happy_path(test_db: Any, async_client: AsyncClient) -> None:
    """Buyer can create a B2B booking draft from a visible marketplace listing.

    - Listing must be published
    - Buyer must have marketplace_access
    - Pricing block must be populated
    - PRICING_RULE_APPLIED audit emitted once (idempotent helper)
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Org + tenants
    org = await test_db.organizations.insert_one(
        {"name": "B2B Org", "slug": "b2b_org", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    seller = await test_db.tenants.insert_one(
        {
            "tenant_key": "seller-b2b",
            "organization_id": org_id,
            "brand_name": "Seller B2B",
            "primary_domain": "seller-b2b.example.com",
            "subdomain": "seller-b2b",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    seller_tenant_id = str(seller.inserted_id)

    buyer = await test_db.tenants.insert_one(
        {
            "tenant_key": "buyer-b2b",
            "organization_id": org_id,
            "brand_name": "Buyer B2B",
            "primary_domain": "buyer-b2b.example.com",
            "subdomain": "buyer-b2b",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    buyer_tenant_id = str(buyer.inserted_id)

    # Users
    email = "b2b_admin@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    # Simple pricing rule so pricing engine produces a non-trivial result
    await test_db.pricing_rules.insert_one(
        {
            "organization_id": org_id,
            "tenant_id": buyer_tenant_id,
            "rule_type": "markup_pct",
            "value": Decimal128("10.0"),
            "priority": 10,
            "stackable": True,
            "valid_from": now,
            "valid_to": now,
            "created_at": now,
            "updated_at": now,
        }
    )

    # Listing (published) under seller tenant
    listing_res = await test_db.marketplace_listings.insert_one(
        {
            "organization_id": org_id,
            "tenant_id": seller_tenant_id,
            "status": "published",
            "title": "B2B Hotel Listing",
            "currency": "TRY",
            "base_price": Decimal128("100.00"),
            "tags": ["b2b"],
            "created_at": now,
            "updated_at": now,
        }
    )
    listing_id = str(listing_res.inserted_id)

    # Access grant seller->buyer
    await test_db.marketplace_access.insert_one(
        {
            "organization_id": org_id,
            "seller_tenant_id": seller_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
            "created_at": now,
        }
    )

    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Key": "buyer-b2b"}

    payload = {
        "source": "marketplace",
        "listing_id": listing_id,
        "customer": {
            "full_name": "B2B Customer",
            "email": "b2b-customer@example.com",
            "phone": "+900000000000",
        },
    }

    resp = await client.post("/api/b2b/bookings-from-marketplace", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    data = resp.json()
    booking_id = data["booking_id"]
    assert data["state"] == "draft"

    # DB assertions
    booking_doc = await test_db.bookings.find_one({"_id": ObjectId(booking_id)})
    assert booking_doc is not None
    assert booking_doc["organization_id"] == org_id

    pricing = booking_doc.get("pricing")
    assert pricing is not None
    assert pricing.get("currency") == "TRY"
    assert pricing.get("base_amount") == "100.00"
    assert pricing.get("final_amount") is not None
    assert isinstance(pricing.get("applied_rules"), list)
    assert pricing.get("applied_rules"), "Expected at least one applied rule"

    # Audit: PRICING_RULE_APPLIED for this booking
    audit_cursor = test_db.audit_logs.find(
        {
            "organization_id": org_id,
            "action": "PRICING_RULE_APPLIED",
            "target.id": booking_id,
        }
    )
    audit_docs = await audit_cursor.to_list(length=10)
    assert len(audit_docs) == 1


@pytest.mark.exit_b2b_booking_create_v1
@pytest.mark.anyio
async def test_b2b_booking_create_forbidden_without_access(test_db: Any, async_client: AsyncClient) -> None:
    """If marketplace_access does not exist, booking creation must be forbidden."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "B2B Org2", "slug": "b2b_org2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    seller = await test_db.tenants.insert_one(
        {
            "tenant_key": "seller-b2b2",
            "organization_id": org_id,
            "brand_name": "Seller B2B2",
            "primary_domain": "seller-b2b2.example.com",
            "subdomain": "seller-b2b2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    seller_tenant_id = str(seller.inserted_id)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "buyer-b2b2",
            "organization_id": org_id,
            "brand_name": "Buyer B2B2",
            "primary_domain": "buyer-b2b2.example.com",
            "subdomain": "buyer-b2b2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "b2b_admin2@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    listing_res = await test_db.marketplace_listings.insert_one(
        {
            "organization_id": org_id,
            "tenant_id": seller_tenant_id,
            "status": "published",
            "title": "Forbidden Listing",
            "currency": "TRY",
            "base_price": Decimal128("200.00"),
            "tags": [],
            "created_at": now,
            "updated_at": now,
        }
    )
    listing_id = str(listing_res.inserted_id)

    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Key": "buyer-b2b2"}
    payload = {
        "source": "marketplace",
        "listing_id": listing_id,
        "customer": {
            "full_name": "B2B Customer2",
            "email": "b2b2@example.com",
            "phone": "+900000000001",
        },
    }

    resp = await client.post("/api/b2b/bookings-from-marketplace", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    err = resp.json().get("error", {})
    assert err.get("message") == "MARKETPLACE_ACCESS_FORBIDDEN"


@pytest.mark.exit_b2b_booking_create_v1
@pytest.mark.anyio
async def test_b2b_booking_create_requires_tenant_context(test_db: Any, async_client: AsyncClient) -> None:
    """Tenant context is required; without X-Tenant-Key booking creation is forbidden."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "B2B Org3", "slug": "b2b_org3", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    seller = await test_db.tenants.insert_one(
        {
            "tenant_key": "seller-b2b3",
            "organization_id": org_id,
            "brand_name": "Seller B2B3",
            "primary_domain": "seller-b2b3.example.com",
            "subdomain": "seller-b2b3",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    seller_tenant_id = str(seller.inserted_id)

    email = "b2b_admin3@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    listing_res = await test_db.marketplace_listings.insert_one(
        {
            "organization_id": org_id,
            "tenant_id": seller_tenant_id,
            "status": "published",
            "title": "No Tenant Listing",
            "currency": "TRY",
            "base_price": Decimal128("300.00"),
            "tags": [],
            "created_at": now,
            "updated_at": now,
        }
    )
    listing_id = str(listing_res.inserted_id)

    headers = {"Authorization": f"Bearer {token}"}  # No X-Tenant-Key
    payload = {
        "source": "marketplace",
        "listing_id": listing_id,
        "customer": {
            "full_name": "B2B Customer3",
            "email": "b2b3@example.com",
            "phone": "+900000000002",
        },
    }

    resp = await client.post("/api/b2b/bookings-from-marketplace", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    err = resp.json().get("error", {})
    assert err.get("message") == "TENANT_CONTEXT_REQUIRED"
