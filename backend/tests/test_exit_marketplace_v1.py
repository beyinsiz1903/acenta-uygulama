from __future__ import annotations

from typing import Any, Dict

import jwt
import pytest
from httpx import AsyncClient
from fastapi import status

from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.exit_marketplace_v1
@pytest.mark.anyio
async def test_marketplace_publish_and_access_flow(test_db: Any, async_client: AsyncClient) -> None:
    """Seller can publish listing and buyer with access can see it in catalog.

    Flow:
    - Org with two tenants: seller_tenant, buyer_tenant
    - Seller user creates draft listing and publishes it
    - Admin grants marketplace_access from seller->buyer
    - Buyer catalog call returns the listing
    - Revoke access -> listing disappears from buyer catalog
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Create organization
    org = await test_db.organizations.insert_one(
        {"name": "MP Org", "slug": "mporg", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    # Create two tenants within same org
    seller_tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "seller-tenant",
            "organization_id": org_id,
            "brand_name": "Seller Tenant",
            "primary_domain": "seller.example.com",
            "subdomain": "seller",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    seller_tenant_id = str(seller_tenant.inserted_id)

    buyer_tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "buyer-tenant",
            "organization_id": org_id,
            "brand_name": "Buyer Tenant",
            "primary_domain": "buyer.example.com",
            "subdomain": "buyer",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    buyer_tenant_id = str(buyer_tenant.inserted_id)

    # Create users (simple admin roles)
    seller_email = "seller_admin@example.com"
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

    buyer_email = "buyer_admin@example.com"
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

    # 1) Seller creates draft listing
    seller_headers = {"Authorization": f"Bearer {seller_token}", "X-Tenant-Key": "seller-tenant"}
    payload = {
        "title": "Test Listing",
        "description": "Marketplace test product",
        "category": "hotel",
        "currency": "TRY",
        "base_price": "100.00",
        "tags": ["test", "hotel"],
    }

    resp_create = await client.post("/api/marketplace/listings", json=payload, headers=seller_headers)
    assert resp_create.status_code == status.HTTP_201_CREATED, resp_create.text
    listing = resp_create.json()
    assert listing["organization_id"] == org_id
    assert listing["tenant_id"] == seller_tenant_id
    assert listing["status"] == "draft"

    listing_id = listing["id"]

    # 2) Seller publishes listing
    resp_publish = await client.post(
        f"/api/marketplace/listings/{listing_id}/publish", headers=seller_headers
    )
    assert resp_publish.status_code == status.HTTP_200_OK, resp_publish.text
    published = resp_publish.json()
    assert published["status"] == "published"

    # 3) Admin grants access seller->buyer
    admin_headers = {"Authorization": f"Bearer {seller_token}"}
    grant_payload = {
        "seller_tenant_id": seller_tenant_id,
        "buyer_tenant_id": buyer_tenant_id,
    }

    resp_grant = await client.post(
        "/api/marketplace/access/grant", json=grant_payload, headers=admin_headers
    )
    assert resp_grant.status_code == status.HTTP_201_CREATED, resp_grant.text

    # 4) Buyer catalog sees listing
    buyer_headers = {"Authorization": f"Bearer {buyer_token}", "X-Tenant-Key": "buyer-tenant"}
    resp_catalog = await client.get("/api/marketplace/catalog", headers=buyer_headers)
    assert resp_catalog.status_code == status.HTTP_200_OK, resp_catalog.text
    data = resp_catalog.json()
    items = data.get("items") or []
    assert any(i["id"] == listing_id for i in items)

    # 5) Revoke access -> listing disappears
    resp_revoke = await client.post(
        "/api/marketplace/access/revoke", json=grant_payload, headers=admin_headers
    )
    assert resp_revoke.status_code == status.HTTP_200_OK, resp_revoke.text

    resp_catalog2 = await client.get("/api/marketplace/catalog", headers=buyer_headers)
    assert resp_catalog2.status_code == status.HTTP_200_OK, resp_catalog2.text
    data2 = resp_catalog2.json()
    items2 = data2.get("items") or []
    assert all(i["id"] != listing_id for i in items2)


@pytest.mark.exit_marketplace_v1
@pytest.mark.anyio
async def test_marketplace_org_and_tenant_scoping(test_db: Any, async_client: AsyncClient) -> None:
    """Ensure org and tenant scoping is enforced for listings and catalog.

    - Cross-org access to listings not allowed
    - Buyer without tenant context cannot access catalog
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Two orgs
    org1 = await test_db.organizations.insert_one(
        {"name": "Org1", "slug": "org1", "created_at": now, "updated_at": now}
    )
    org2 = await test_db.organizations.insert_one(
        {"name": "Org2", "slug": "org2", "created_at": now, "updated_at": now}
    )
    org1_id = str(org1.inserted_id)
    org2_id = str(org2.inserted_id)

    # Tenants
    t1 = await test_db.tenants.insert_one(
        {
            "tenant_key": "t1",
            "organization_id": org1_id,
            "brand_name": "T1",
            "primary_domain": "t1.example.com",
            "subdomain": "t1",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    t1_id = str(t1.inserted_id)

    t2 = await test_db.tenants.insert_one(
        {
            "tenant_key": "t2",
            "organization_id": org2_id,
            "brand_name": "T2",
            "primary_domain": "t2.example.com",
            "subdomain": "t2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    t2_id = str(t2.inserted_id)

    # Users
    email1 = "admin1@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org1_id,
            "email": email1,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email2 = "admin2@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org2_id,
            "email": email2,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    token1 = jwt.encode({"sub": email1, "org": org1_id}, _jwt_secret(), algorithm="HS256")
    token2 = jwt.encode({"sub": email2, "org": org2_id}, _jwt_secret(), algorithm="HS256")

    headers1 = {"Authorization": f"Bearer {token1}", "X-Tenant-Key": "t1"}
    headers2 = {"Authorization": f"Bearer {token2}", "X-Tenant-Key": "t2"}

    # Org1 creates and publishes listing
    payload = {
        "title": "Org1 Listing",
        "base_price": "50.00",
        "currency": "TRY",
    }
    resp_create = await client.post("/api/marketplace/listings", json=payload, headers=headers1)
    assert resp_create.status_code == status.HTTP_201_CREATED, resp_create.text
    listing = resp_create.json()
    listing_id = listing["id"]

    resp_publish = await client.post(f"/api/marketplace/listings/{listing_id}/publish", headers=headers1)
    assert resp_publish.status_code == status.HTTP_200_OK, resp_publish.text

    # Org2 cannot access Org1 listing by id
    resp_get_cross = await client.get(f"/api/marketplace/listings/{listing_id}", headers=headers2)
    assert resp_get_cross.status_code == status.HTTP_404_NOT_FOUND

    # Buyer without tenant context cannot access catalog
    buyer_no_tenant_headers = {"Authorization": f"Bearer {token1}"}
    resp_catalog_no_tenant = await client.get("/api/marketplace/catalog", headers=buyer_no_tenant_headers)
    assert resp_catalog_no_tenant.status_code == status.HTTP_403_FORBIDDEN

