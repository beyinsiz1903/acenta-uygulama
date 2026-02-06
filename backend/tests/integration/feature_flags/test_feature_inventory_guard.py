"""Feature guard tests for the Inventory module.

Tests that /api/inventory endpoints are gated by the 'inventory' feature flag.
These endpoints go through TenantResolutionMiddleware, so require_tenant_feature
reads tenant_id from request.state.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.constants.features import FEATURE_INVENTORY
from tests.integration.feature_flags.conftest import clear_features, enable_feature


# GET /api/inventory requires product_id, start, end query params
INVENTORY_PATH = "/api/inventory?product_id=test&start=2026-01-01&end=2026-01-31"


@pytest.mark.anyio
async def test_inventory_blocked_when_feature_disabled(
  feature_test_client: AsyncClient,
  test_db,
  tenant_for_feature_test,
) -> None:
  """Tenant without 'inventory' feature must receive 403 feature_not_enabled."""
  tenant_id = str(tenant_for_feature_test["_id"])
  await clear_features(test_db, tenant_id)

  resp = await feature_test_client.get(INVENTORY_PATH)
  assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
  body = resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "feature_not_enabled", body
  assert error.get("details", {}).get("feature") == FEATURE_INVENTORY


@pytest.mark.anyio
async def test_inventory_allowed_when_feature_enabled(
  feature_test_client: AsyncClient,
  test_db,
  tenant_for_feature_test,
) -> None:
  """When 'inventory' feature is enabled, endpoint must NOT return feature_not_enabled."""
  tenant_id = str(tenant_for_feature_test["_id"])
  await enable_feature(tenant_id, FEATURE_INVENTORY)

  resp = await feature_test_client.get(INVENTORY_PATH)
  # Endpoint may return 200, 400 (bad product_id), etc. - just not feature_not_enabled 403
  assert resp.status_code != 403 or resp.json().get("error", {}).get("code") != "feature_not_enabled", (
    f"Feature guard still blocking: {resp.text}"
  )
