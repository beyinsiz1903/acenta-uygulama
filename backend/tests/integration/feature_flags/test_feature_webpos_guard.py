from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.db import get_db
from app.services.feature_service import feature_service
from app.constants.features import FEATURE_WEBPOS


WEBPOS_PATH = "/api/pos/orders"  # adjust to actual WebPOS endpoint if differs


@pytest.mark.anyio
async def test_webpos_requires_feature_flag(async_client: AsyncClient, agency_headers: dict[str, str]) -> None:
  """Tenant without 'webpos' feature must receive feature_not_enabled on WebPOS endpoints."""
  client = AsyncClient(transport=async_client._transport, base_url=str(async_client.base_url), headers=agency_headers)

  db = await get_db()
  tenant_id = agency_headers.get("X-Tenant-Id")
  assert tenant_id
  await db.tenant_features.delete_many({"tenant_id": tenant_id})

  resp = await client.get(WEBPOS_PATH)
  assert resp.status_code == 403, resp.text
  body: dict[str, Any] = resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "feature_not_enabled", body
  assert error.get("details", {}).get("feature") == FEATURE_WEBPOS

  await client.aclose()


@pytest.mark.anyio
async def test_webpos_endpoint_succeeds_when_feature_enabled(async_client: AsyncClient, agency_headers: dict[str, str]) -> None:
  """When 'webpos' feature is enabled, endpoint should not be blocked by feature flag."""
  client = AsyncClient(transport=async_client._transport, base_url=str(async_client.base_url), headers=agency_headers)

  tenant_id = agency_headers.get("X-Tenant-Id")
  assert tenant_id

  await feature_service.set_features(tenant_id, [FEATURE_WEBPOS])

  resp = await client.get(WEBPOS_PATH)
  assert resp.status_code != 403, resp.text
  if resp.status_code == 403:
    body: dict[str, Any] = resp.json()
    assert body.get("error", {}).get("code") != "feature_not_enabled"

  await client.aclose()
