"""Tests for Admin Tenant Feature Management endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.constants.features import FEATURE_B2B, FEATURE_REPORTS, ALL_FEATURE_KEYS


@pytest.mark.anyio
async def test_admin_get_tenant_features(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """Admin can GET features for any tenant (returns empty initially)."""
  resp = await async_client.get(
    "/api/admin/tenants/nonexistent_tenant/features",
    headers=admin_headers,
  )
  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert body["tenant_id"] == "nonexistent_tenant"
  assert body["features"] == []
  assert set(body["available_features"]) == set(ALL_FEATURE_KEYS)


@pytest.mark.anyio
async def test_admin_patch_tenant_features(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """Admin can PATCH features for a tenant (legacy compat writes add_ons)."""
  target = "admin_test_tenant_1"
  await test_db.tenant_capabilities.delete_many({"tenant_id": target})
  await test_db.tenant_features.delete_many({"tenant_id": target})

  # Set features
  resp = await async_client.patch(
    f"/api/admin/tenants/{target}/features",
    headers=admin_headers,
    json={"features": [FEATURE_B2B, FEATURE_REPORTS]},
  )
  assert resp.status_code == 200, resp.text
  body = resp.json()
  # Effective features = starter plan defaults + add_ons (b2b, reports)
  assert FEATURE_B2B in body["features"]
  assert FEATURE_REPORTS in body["features"]

  # Verify via GET
  resp2 = await async_client.get(
    f"/api/admin/tenants/{target}/features",
    headers=admin_headers,
  )
  assert resp2.status_code == 200
  data = resp2.json()
  assert FEATURE_B2B in data["features"]
  assert FEATURE_REPORTS in data["features"]
  assert data["source"] == "capabilities"


@pytest.mark.anyio
async def test_admin_patch_invalid_features(
  async_client: AsyncClient,
  admin_headers: dict,
) -> None:
  """Admin gets 422 when sending invalid feature keys."""
  resp = await async_client.patch(
    "/api/admin/tenants/test/features",
    headers=admin_headers,
    json={"features": ["b2b", "nonexistent_feature"]},
  )
  assert resp.status_code == 422, resp.text
  body = resp.json()
  assert body["error"]["code"] == "invalid_features"
  assert "nonexistent_feature" in body["error"]["details"]["invalid"]


@pytest.mark.anyio
async def test_admin_features_requires_admin_role(
  async_client: AsyncClient,
  agency_headers: dict,
) -> None:
  """Non-admin user should be rejected."""
  resp = await async_client.get(
    "/api/admin/tenants/any/features",
    headers=agency_headers,
  )
  # Should be 403 (forbidden) since agency user doesn't have admin role
  assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
