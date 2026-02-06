"""Tests for GET /api/tenant/features endpoint."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.constants.features import FEATURE_REPORTS, FEATURE_CRM
from tests.integration.feature_flags.conftest import clear_features, enable_feature


@pytest.mark.anyio
async def test_get_tenant_features_empty(
  feature_test_client: AsyncClient,
  test_db,
  tenant_for_feature_test,
) -> None:
  """Tenant with no features should return empty list."""
  tenant_id = str(tenant_for_feature_test["_id"])
  await clear_features(test_db, tenant_id)

  resp = await feature_test_client.get("/api/tenant/features")
  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert body["tenant_id"] == tenant_id
  assert body["features"] == []


@pytest.mark.anyio
async def test_get_tenant_features_with_enabled(
  feature_test_client: AsyncClient,
  test_db,
  tenant_for_feature_test,
) -> None:
  """Tenant with enabled features should return them."""
  tenant_id = str(tenant_for_feature_test["_id"])
  await clear_features(test_db, tenant_id)
  await enable_feature(tenant_id, FEATURE_REPORTS)
  await enable_feature(tenant_id, FEATURE_CRM)

  resp = await feature_test_client.get("/api/tenant/features")
  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert body["tenant_id"] == tenant_id
  assert set(body["features"]) == {FEATURE_REPORTS, FEATURE_CRM}
