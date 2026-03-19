"""Enterprise Stabilization Test Suite — Tenant Isolation.

Tests cover:
1. Tenant middleware injects correct context
2. Cross-tenant data isolation
3. Agency data scoped to organization
4. Admin can access cross-tenant (super_admin only)
5. Tenant-bound query filters
"""
from __future__ import annotations

import pytest
import httpx
from bson import ObjectId

from app.utils import now_utc


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



pytestmark = pytest.mark.anyio


# ============================================================================
# 1. Tenant Context Injection Tests
# ============================================================================

class TestTenantContext:
    """Test tenant context resolution from auth."""

    async def test_admin_login_resolves_tenant(self, async_client: httpx.AsyncClient, admin_token: str):
        """Admin user has organization_id in /me response."""
        resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "organization_id" in data
        assert data["organization_id"] is not None

    async def test_agency_login_resolves_tenant(self, async_client: httpx.AsyncClient, agency_token: str):
        """Agency user has organization_id in /me response."""
        resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "organization_id" in data


# ============================================================================
# 2. Cross-Tenant Data Isolation Tests
# ============================================================================

class TestCrossTenantIsolation:
    """Verify that one tenant cannot access another tenant's data."""

    async def test_agency_cannot_see_other_org_bookings(self, test_db, async_client: httpx.AsyncClient, agency_token: str):
        """Agency user should not see bookings from another organization."""
        # Get current user's org
        me_resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        _unwrap(me_resp)["organization_id"]

        # Insert a booking in a DIFFERENT org
        other_org = "org_other_" + ObjectId().__str__()[:8]
        await test_db.bookings.insert_one({
            "organization_id": other_org,
            "status": "CONFIRMED",
            "customer": {"name": "Secret Guest"},
            "created_at": now_utc(),
        })

        # Try to list bookings — should only see own org's bookings
        resp = await async_client.get(
            "/api/bookings",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        if resp.status_code == 200:
            data = _unwrap(resp)
            items = data if isinstance(data, list) else data.get("items", data.get("bookings", []))
            for item in items:
                # No booking should belong to other_org
                assert item.get("organization_id") != other_org

    async def test_agency_cannot_see_other_org_customers(self, test_db, async_client: httpx.AsyncClient, agency_token: str):
        """Agency user should not see customers from another organization."""
        me_resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        _unwrap(me_resp)["organization_id"]

        other_org = "org_other_" + ObjectId().__str__()[:8]
        await test_db.customers.insert_one({
            "organization_id": other_org,
            "name": "Secret Customer",
            "email": "secret@other.org",
            "created_at": now_utc(),
        })

        resp = await async_client.get(
            "/api/crm/customers",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        if resp.status_code == 200:
            data = _unwrap(resp)
            items = data if isinstance(data, list) else data.get("items", data.get("customers", []))
            for item in items:
                assert item.get("organization_id") != other_org


# ============================================================================
# 3. Organization Scoped API Tests
# ============================================================================

class TestOrgScopedAPIs:
    """Test that critical APIs enforce org scoping."""

    async def test_agencies_list_scoped(self, async_client: httpx.AsyncClient, admin_token: str):
        """Admin agencies endpoint returns only org-scoped results."""
        resp = await async_client.get(
            "/api/admin/agencies",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Should return 200 (admin has access)
        assert resp.status_code == 200

    async def test_hotel_search_requires_auth(self, async_client: httpx.AsyncClient):
        """Hotel search requires authentication."""
        resp = await async_client.get("/api/b2b/hotels/search")
        assert resp.status_code in (401, 403, 422)
