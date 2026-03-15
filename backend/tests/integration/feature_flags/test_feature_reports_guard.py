"""Feature guard tests for the Reports module.

Tests that /api/reports/* endpoints are gated by the 'reports' feature flag.
These endpoints go through TenantResolutionMiddleware, so require_tenant_feature
reads tenant_id from request.state.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.constants.features import FEATURE_REPORTS
from tests.integration.feature_flags.conftest import clear_features, enable_feature


REPORTS_PATH = "/api/reports/reservations-summary"


@pytest.mark.anyio
async def test_reports_blocked_when_feature_disabled(
  feature_test_client: AsyncClient,
  test_db,
  tenant_for_feature_test,
) -> None:
  """Tenant without 'reports' feature must receive 403 feature_not_enabled."""
  tenant_id = str(tenant_for_feature_test["_id"])
  await clear_features(test_db, tenant_id)

  resp = await feature_test_client.get(REPORTS_PATH)
  assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
  body = resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "feature_not_enabled", body
  assert error.get("details", {}).get("feature") == FEATURE_REPORTS


@pytest.mark.anyio
async def test_reports_allowed_when_feature_enabled(
  feature_test_client: AsyncClient,
  test_db,
  tenant_for_feature_test,
) -> None:
  """When 'reports' feature is enabled, endpoint must NOT return feature_not_enabled."""
  tenant_id = str(tenant_for_feature_test["_id"])
  await enable_feature(tenant_id, FEATURE_REPORTS)

  resp = await feature_test_client.get(REPORTS_PATH)
  # The endpoint may return 200 or empty data, but must NOT be blocked by feature guard
  assert resp.status_code != 403 or resp.json().get("error", {}).get("code") != "feature_not_enabled", (
    f"Feature guard still blocking: {resp.text}"
  )
