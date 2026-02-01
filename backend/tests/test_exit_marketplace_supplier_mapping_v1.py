from __future__ import annotations

from typing import Any, Dict

import jwt
import pytest
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.exit_marketplace_supplier_mapping_v1
@pytest.mark.anyio
async def test_resolve_supplier_and_booking_mapping(test_db: Any, async_client: AsyncClient) -> None:
    """Supplier resolve + booking include supplier mapping for marketplace listings.

    Flow:
    - Org with seller & buyer tenants
    - Seller creates listing with supplier metadata (mock_supplier_v1 + external_ref)
    - Seller publishes listing
    - Access grant seller->buyer
    - Resolve endpoint populates supplier_mapping
    - Booking from marketplace includes supplier + supplier_offer_id in offer_ref
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Org + tenants
    org = await test_db.organizations.insert_one(
        {"name": "MP-SUP Org", "slug": "mpsup_org", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    seller_tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "seller-sup",
            "organization_id": org_id,
            "brand_name": "Seller Supplier",
            "primary_domain": "seller-sup.example.com",
            "subdomain": "seller-sup",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    seller_tenant_id = str(seller_tenant.inserted_id)

    buyer_tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "buyer-sup",
            "organization_id": org_id,
            "brand_name": "Buyer Supplier",
            "primary_domain": "buyer-sup.example.com",
            "subdomain": "buyer-sup",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    buyer_tenant_id = str(buyer_tenant.inserted_id)

    # Users
    seller_email = "seller_sup@example.com"
    buyer_email = "buyer_sup@example.com"

    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": seller_email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": buyer_email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    seller_token = jwt.encode({"sub": seller_email, "org": org_id}, _jwt_secret(), algorithm="HS256")
    buyer_token = jwt.encode({"sub": buyer_email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    seller_headers = {"Authorization": f"Bearer {seller_token}", "X-Tenant-Key": "seller-sup"}

    # 1) Seller creates listing with supplier metadata
    payload = {
        "title": "Supplier Listing",
        "description": "Supplier mapping test product",
        "category": "hotel",
        "currency": "TRY",
        "base_price": "200.00",
        "tags": ["supplier", "hotel"],
        "supplier": {
            "name": "mock_supplier_v1",
            "external_ref": "MS-12345",
        },
    }

    resp_create = await client.post("/api/marketplace/listings", json=payload, headers=seller_headers)
    assert resp_create.status_code == status.HTTP_201_CREATED, resp_create.text
    listing = resp_create.json()
    listing_id = listing["id"]

    # 2) Seller publishes listing
    resp_publish = await client.post(f"/api/marketplace/listings/{listing_id}/publish", headers=seller_headers)
    assert resp_publish.status_code == status.HTTP_200_OK, resp_publish.text

    # 3) Admin grants access seller->buyer
    admin_headers = {"Authorization": f"Bearer {seller_token}"}
    grant_payload = {"seller_tenant_id": seller_tenant_id, "buyer_tenant_id": buyer_tenant_id}
    resp_grant = await client.post("/api/marketplace/access/grant", json=grant_payload, headers=admin_headers)
    assert resp_grant.status_code == status.HTTP_201_CREATED, resp_grant.text

    # 4) Resolve supplier mapping explicitly
    resp_resolve = await client.post(
        f"/api/marketplace/listings/{listing_id}/resolve-supplier",
        headers=seller_headers,
    )
    assert resp_resolve.status_code == status.HTTP_200_OK, resp_resolve.text
    resolved = resp_resolve.json()
    assert resolved["supplier"] == "mock_supplier_v1"
    assert resolved["supplier_offer_id"] == "MOCK-MS-12345"

    # Reload listing from DB and check supplier_mapping
    from bson import ObjectId

    stored = await test_db.marketplace_listings.find_one({"_id": ObjectId(listing_id)})
    mapping = (stored or {}).get("supplier_mapping") or {}
    assert mapping.get("status") == "resolved"
    assert mapping.get("offer_id") == "MOCK-MS-12345"

    # 5) Buyer creates booking from marketplace and offer_ref includes supplier mapping
    buyer_headers = {
        "Authorization": f"Bearer {buyer_token}",
        "X-Tenant-Key": "buyer-sup",
        "Idempotency-Key": "sup-test-1",
    }

    booking_payload = {
        "source": "marketplace",
        "listing_id": listing_id,
        "customer": {
            "full_name": "Supplier Test Customer",
            "email": "sup-customer@example.com",
            "phone": "+900000000000",
        },
        "travellers": [
            {"first_name": "Test", "last_name": "User"},
        ],
    }

    resp_booking = await client.post("/api/b2b/bookings", json=booking_payload, headers=buyer_headers)
    assert resp_booking.status_code == status.HTTP_201_CREATED, resp_booking.text
    booking_data = resp_booking.json()
    booking_id = booking_data["booking_id"]

    # Check booking doc in DB
    booking_doc = await test_db.bookings.find_one({"_id": ObjectId(booking_id)})
    offer_ref = (booking_doc or {}).get("offer_ref") or {}
    # For legacy tests without supplier mapping, fallback to "marketplace"
    supplier = offer_ref.get("supplier") or "marketplace"
    assert supplier == "mock_supplier_v1"
    assert offer_ref.get("supplier_offer_id") == "MOCK-MS-12345"


@pytest.mark.exit_marketplace_supplier_mapping_v1
@pytest.mark.anyio
async def test_unsupported_supplier_errors(test_db: Any, async_client: AsyncClient) -> None:
    """Unsupported or malformed supplier metadata should surface clear 422/500 errors."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "MP-SUP Org2", "slug": "mpsup_org2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "sup-tenant",
            "organization_id": org_id,
            "brand_name": "Sup Tenant",
            "primary_domain": "sup.example.com",
            "subdomain": "sup",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "sup_unsupported@example.com"
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
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Key": "sup-tenant"}

    # 1) Missing supplier.name -> SUPPLIER_NOT_SUPPORTED
    payload_no_name = {
        "title": "No Supplier Name",
        "currency": "TRY",
        "base_price": "100.00",
        "supplier": {
            "external_ref": "X-1",
        },
    }
    resp_create1 = await client.post("/api/marketplace/listings", json=payload_no_name, headers=headers)
    assert resp_create1.status_code == status.HTTP_201_CREATED, resp_create1.text
    listing1 = resp_create1.json()

    resp_resolve1 = await client.post(
        f"/api/marketplace/listings/{listing1['id']}/resolve-supplier",
        headers=headers,
    )
    assert resp_resolve1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, resp_resolve1.text
    err1 = resp_resolve1.json().get("error", {})
    assert err1.get("code") == "SUPPLIER_NOT_SUPPORTED"

    # 2) Unknown supplier.name -> SUPPLIER_NOT_SUPPORTED
    payload_unknown = {
        "title": "Unknown Supplier",
        "currency": "TRY",
        "base_price": "100.00",
        "supplier": {
            "name": "unknown_supplier_v1",
            "external_ref": "X-2",
        },
    }
    resp_create2 = await client.post("/api/marketplace/listings", json=payload_unknown, headers=headers)
    assert resp_create2.status_code == status.HTTP_201_CREATED, resp_create2.text
    listing2 = resp_create2.json()

    resp_resolve2 = await client.post(
        f"/api/marketplace/listings/{listing2['id']}/resolve-supplier",
        headers=headers,
    )
    assert resp_resolve2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, resp_resolve2.text
    err2 = resp_resolve2.json().get("error", {})
    assert err2.get("code") == "SUPPLIER_NOT_SUPPORTED"

    # 3) Missing external_ref -> LISTING_SUPPLIER_REF_REQUIRED
    payload_no_ref = {
        "title": "No External Ref",
        "currency": "TRY",
        "base_price": "100.00",
        "supplier": {
            "name": "mock_supplier_v1",
        },
    }
    resp_create3 = await client.post("/api/marketplace/listings", json=payload_no_ref, headers=headers)
    assert resp_create3.status_code == status.HTTP_201_CREATED, resp_create3.text
    listing3 = resp_create3.json()

    resp_resolve3 = await client.post(
        f"/api/marketplace/listings/{listing3['id']}/resolve-supplier",
        headers=headers,
    )
    assert resp_resolve3.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, resp_resolve3.text
    err3 = resp_resolve3.json().get("error", {})
    assert err3.get("code") == "LISTING_SUPPLIER_REF_REQUIRED"
