"""Tests for GET /api/tenant/features endpoint (Plan Inheritance model)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.constants.features import FEATURE_REPORTS, FEATURE_CRM
from app.constants.plan_matrix import PLAN_MATRIX
from tests.integration.feature_flags.conftest import clear_features, enable_feature


@pytest.mark.anyio
async def test_get_tenant_features_empty(
  feature_test_client: AsyncClient,
  test_db,
  tenant_for_feature_test,
) -> None:
  """Tenant with no capabilities or legacy features should return empty list."""
  tenant_id = str(tenant_for_feature_test["_id"])
  await test_db.tenant_capabilities.delete_many({"tenant_id": tenant_id})
  await test_db.tenant_features.delete_many({"tenant_id": tenant_id})

  resp = await feature_test_client.get("/api/tenant/features")
  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert body["tenant_id"] == tenant_id
  assert body["features"] == []


@pytest.mark.anyio
async def test_get_tenant_features_with_plan(
  feature_test_client: AsyncClient,
  test_db,
  tenant_for_feature_test,
) -> None:
  """Tenant with capabilities returns plan defaults + add_ons."""
  tenant_id = str(tenant_for_feature_test["_id"])
  await test_db.tenant_capabilities.delete_many({"tenant_id": tenant_id})
  await test_db.tenant_features.delete_many({"tenant_id": tenant_id})

  # Enable features (creates capability with starter plan + features as add_ons)
  await enable_feature(tenant_id, FEATURE_REPORTS)
  await enable_feature(tenant_id, FEATURE_CRM)

  resp = await feature_test_client.get("/api/tenant/features")
  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert body["tenant_id"] == tenant_id
  assert body["source"] == "capabilities"
  # Should contain add_ons + plan defaults
  assert FEATURE_REPORTS in body["features"]
  assert FEATURE_CRM in body["features"]
  # Starter plan includes dashboard, reservations, etc.
  for f in PLAN_MATRIX["starter"]["features"]:
    assert f in body["features"], f"Starter plan feature '{f}' missing"
