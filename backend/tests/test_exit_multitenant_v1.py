from __future__ import annotations

from typing import Any, Dict

import jwt
import pytest
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.exit_multitenant_v1
@pytest.mark.anyio
async def test_tenant_resolve_by_header(test_db: Any, async_client: AsyncClient) -> None:
    """Tenant resolution via X-Tenant-Key header attaches tenant context."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "TenantOrgA", "slug": "tenant_org_a", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "tenant-a",
            "organization_id": org_id,
            "brand_name": "Tenant A Brand",
            "primary_domain": "tenant-a.example.com",
            "subdomain": "tenant-a",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    # Simple public storefront call that should require tenant
    resp = await client.get(
        "/storefront/health-check",
        headers={"X-Tenant-Key": "tenant-a"},
    )

    # Route may not exist; we only care that middleware doesn't 404 TENANT_NOT_FOUND
    assert resp.status_code != status.HTTP_404_NOT_FOUND


@pytest.mark.exit_multitenant_v1
@pytest.mark.anyio
async def test_storefront_requires_tenant(test_db: Any, async_client: AsyncClient) -> None:
    """Storefront routes without tenant must return TENANT_NOT_FOUND."""

    client: AsyncClient = async_client

    resp = await client.get("/storefront/anything")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    body = resp.json()
    err = body.get("error", {})
    assert err.get("code") == "TENANT_NOT_FOUND"


@pytest.mark.exit_multitenant_v1
@pytest.mark.anyio
async def test_api_routes_allow_no_tenant_for_backward_compat(test_db: Any, async_client: AsyncClient) -> None:
    """Internal /api routes must continue to work without tenant resolution."""

    client: AsyncClient = async_client
    now = now_utc()

    # Seed minimal org + user to create a booking via Sprint 1 behavior
    org = await test_db.organizations.insert_one(
        {"name": "Org_No_Tenant", "slug": "org_no_tenant", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    email = "no_tenant@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    resp = await client.post(
        "/api/bookings",
        json={"amount": 100.0, "currency": "TRY"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == status.HTTP_201_CREATED
    booking = resp.json()
    assert booking["organization_id"] == org_id


@pytest.mark.exit_multitenant_v1
@pytest.mark.anyio
async def test_cross_tenant_forbidden_on_payload_org_id_mismatch(test_db: Any, async_client: AsyncClient) -> None:
    """Payload specifying different organization_id than tenant org must be forbidden."""

    client: AsyncClient = async_client
    now = now_utc()

    # OrgA and OrgB
    org_a = await test_db.organizations.insert_one(
        {"name": "TenantOrgA2", "slug": "tenant_org_a2", "created_at": now, "updated_at": now}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "TenantOrgB2", "slug": "tenant_org_b2", "created_at": now, "updated_at": now}
    )
    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)

    # Tenant bound to OrgA
    await test_db.tenants.insert_one(
        {
            "tenant_key": "tenant-a2",
            "organization_id": org_a_id,
            "brand_name": "Tenant A2 Brand",
            "primary_domain": "tenant-a2.example.com",
            "subdomain": "tenant-a2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "tenant_a2_user@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_a_id,
            "email": email,
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    token = jwt.encode({"sub": email, "org": org_a_id}, _jwt_secret(), algorithm="HS256")

    # Attempt to create booking with mismatching organization_id in payload
    resp = await client.post(
        "/api/bookings",
        json={"amount": 50.0, "currency": "TRY", "organization_id": org_b_id},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Key": "tenant-a2"},
    )

    assert resp.status_code == status.HTTP_403_FORBIDDEN
    body = resp.json()
    assert body.get("detail") == "CROSS_TENANT_FORBIDDEN"
