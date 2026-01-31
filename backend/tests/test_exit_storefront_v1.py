from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
import pytest
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.exit_storefront_v1
@pytest.mark.anyio
async def test_storefront_health_requires_tenant(test_db: Any, async_client: AsyncClient) -> None:
    client: AsyncClient = async_client
    now = now_utc()

    # Seed org and tenant
    org = await test_db.organizations.insert_one(
        {"name": "StorefrontOrgA", "slug": "storefront_org_a", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "sf-tenant-a",
            "organization_id": org_id,
            "brand_name": "Storefront Tenant A",
            "primary_domain": "sf-a.example.com",
            "subdomain": "sf-a",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    # Without tenant -> TENANT_NOT_FOUND
    resp_no = await client.get("/storefront/health")
    assert resp_no.status_code == status.HTTP_404_NOT_FOUND
    err_no = resp_no.json().get("error", {})
    assert err_no.get("code") == "TENANT_NOT_FOUND"

    # With tenant header -> 200
    resp_yes = await client.get("/storefront/health", headers={"X-Tenant-Key": "sf-tenant-a"})
    assert resp_yes.status_code == status.HTTP_200_OK
    body = resp_yes.json()
    assert body["ok"] is True
    assert body["tenant_key"] == "sf-tenant-a"
    assert body["tenant_id"] is not None


@pytest.mark.exit_storefront_v1
@pytest.mark.anyio
async def test_storefront_full_flow_happy_path(test_db: Any, async_client: AsyncClient) -> None:
    """End-to-end: search -> get offer -> create booking (draft)."""

    client: AsyncClient = async_client
    now = now_utc()

    # Org + tenant + user (user not strictly required for storefront, but org must exist)
    org = await test_db.organizations.insert_one(
        {"name": "StorefrontOrgB", "slug": "storefront_org_b", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "sf-tenant-b",
            "organization_id": org_id,
            "brand_name": "Storefront Tenant B",
            "primary_domain": "sf-b.example.com",
            "subdomain": "sf-b",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    # 1) Search
    resp_search = await client.get(
        "/storefront/search",
        headers={"X-Tenant-Key": "sf-tenant-b"},
    )
    assert resp_search.status_code == status.HTTP_200_OK
    data_search = resp_search.json()
    search_id = data_search["search_id"]
    offers = data_search.get("offers") or []
    assert offers
    first_offer = offers[0]

    # 2) Get offer
    resp_offer = await client.get(
        f"/storefront/offers/{first_offer['offer_id']}",
        params={"search_id": search_id},
        headers={"X-Tenant-Key": "sf-tenant-b"},
    )
    assert resp_offer.status_code == status.HTTP_200_OK
    data_offer = resp_offer.json()
    assert data_offer["offer_id"] == first_offer["offer_id"]

    # 3) Create booking
    payload = {
        "search_id": search_id,
        "offer_id": first_offer["offer_id"],
        "customer": {
            "full_name": "Test Customer",
            "email": "customer@example.com",
            "phone": "+900000000000",
        },
    }

    resp_book = await client.post(
        "/storefront/bookings",
        json=payload,
        headers={"X-Tenant-Key": "sf-tenant-b"},
    )
    assert resp_book.status_code == status.HTTP_201_CREATED
    data_book = resp_book.json()
    assert data_book["state"] == "draft"
    assert data_book["booking_id"]


@pytest.mark.exit_storefront_v1
@pytest.mark.anyio
async def test_storefront_session_expired_behaviour(test_db: Any, async_client: AsyncClient) -> None:
    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "StorefrontOrgC", "slug": "storefront_org_c", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "sf-tenant-c",
            "organization_id": org_id,
            "brand_name": "Storefront Tenant C",
            "primary_domain": "sf-c.example.com",
            "subdomain": "sf-c",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    # Create an expired session directly in DB
    expired_at = now - timedelta(minutes=5)
    session = await test_db.storefront_sessions.insert_one(
        {
            "tenant_id": "sf-tenant-c-id",
            "search_id": "expired-search",
            "offers_snapshot": [],
            "expires_at": expired_at,
            "created_at": now,
        }
    )

    # offers endpoint should report SESSION_EXPIRED
    resp_offer = await client.get(
        "/storefront/offers/ANY",
        params={"search_id": "expired-search"},
        headers={"X-Tenant-Key": "sf-tenant-c"},
    )
    assert resp_offer.status_code == status.HTTP_410_GONE
    err_offer = resp_offer.json().get("error", {})
    assert err_offer.get("code") == "SESSION_EXPIRED"

    # bookings endpoint should also report SESSION_EXPIRED
    resp_book = await client.post(
        "/storefront/bookings",
        json={
            "search_id": "expired-search",
            "offer_id": "ANY",
            "customer": {
                "full_name": "Expired Customer",
                "email": "expired@example.com",
                "phone": "+900000000000",
            },
        },
        headers={"X-Tenant-Key": "sf-tenant-c"},
    )
    assert resp_book.status_code == status.HTTP_410_GONE
    err_book = resp_book.json().get("error", {})
    assert err_book.get("code") == "SESSION_EXPIRED"


@pytest.mark.exit_storefront_v1
@pytest.mark.anyio
async def test_storefront_cross_tenant_isolation_on_search_id(test_db: Any, async_client: AsyncClient) -> None:
    """search_id from TenantA must not be usable from TenantB."""

    client: AsyncClient = async_client
    now = now_utc()

    # OrgA + TenantA
    org_a = await test_db.organizations.insert_one(
        {"name": "StorefrontOrgD1", "slug": "storefront_org_d1", "created_at": now, "updated_at": now}
    )
    org_a_id = str(org_a.inserted_id)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "sf-tenant-d1",
            "organization_id": org_a_id,
            "brand_name": "Storefront Tenant D1",
            "primary_domain": "sf-d1.example.com",
            "subdomain": "sf-d1",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    # OrgB + TenantB
    org_b = await test_db.organizations.insert_one(
        {"name": "StorefrontOrgD2", "slug": "storefront_org_d2", "created_at": now, "updated_at": now}
    )
    org_b_id = str(org_b.inserted_id)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "sf-tenant-d2",
            "organization_id": org_b_id,
            "brand_name": "Storefront Tenant D2",
            "primary_domain": "sf-d2.example.com",
            "subdomain": "sf-d2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    # TenantA does a search
    resp_search_a = await client.get(
        "/storefront/search",
        headers={"X-Tenant-Key": "sf-tenant-d1"},
    )
    assert resp_search_a.status_code == status.HTTP_200_OK
    search_id_a = resp_search_a.json()["search_id"]

    # TenantB tries to re-use TenantA's search_id => SESSION_EXPIRED (no session for that tenant+search_id)
    resp_offer_b = await client.get(
        f"/storefront/offers/ANY",
        params={"search_id": search_id_a},
        headers={"X-Tenant-Key": "sf-tenant-d2"},
    )
    assert resp_offer_b.status_code == status.HTTP_410_GONE
    err_b = resp_offer_b.json().get("error", {})
    assert err_b.get("code") == "SESSION_EXPIRED"
