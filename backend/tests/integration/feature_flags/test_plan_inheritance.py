"""Tests for Plan Inheritance Engine (plan_defaults + add_ons = effective_features)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.constants.plan_matrix import PLAN_MATRIX


@pytest.mark.anyio
async def test_starter_plan_no_b2b(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """Starter plan should NOT include b2b."""
  target = "plan_test_starter"
  await test_db.tenant_capabilities.delete_many({"tenant_id": target})
  await test_db.tenant_features.delete_many({"tenant_id": target})

  # Set plan to starter with no add-ons
  resp = await async_client.patch(
    f"/api/admin/tenants/{target}/plan",
    headers=admin_headers,
    json={"plan": "starter"},
  )
  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert "b2b" not in body["features"]
  assert body["plan"] == "starter"
  assert body["source"] == "capabilities"


@pytest.mark.anyio
async def test_enterprise_plan_has_b2b(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """Enterprise plan should include b2b."""
  target = "plan_test_enterprise"
  await test_db.tenant_capabilities.delete_many({"tenant_id": target})

  resp = await async_client.patch(
    f"/api/admin/tenants/{target}/plan",
    headers=admin_headers,
    json={"plan": "enterprise"},
  )
  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert "b2b" in body["features"]
  assert "accounting" in body["features"]
  assert body["plan"] == "enterprise"


@pytest.mark.anyio
async def test_add_on_override_starter(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """Starter + add_on b2b should include b2b in effective features."""
  target = "plan_test_addon"
  await test_db.tenant_capabilities.delete_many({"tenant_id": target})

  # Set starter plan
  await async_client.patch(
    f"/api/admin/tenants/{target}/plan",
    headers=admin_headers,
    json={"plan": "starter"},
  )

  # Add b2b as add-on
  resp = await async_client.patch(
    f"/api/admin/tenants/{target}/add-ons",
    headers=admin_headers,
    json={"add_ons": ["b2b"]},
  )
  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert "b2b" in body["features"]
  assert body["plan"] == "starter"
  assert "b2b" in body["add_ons"]

  # Also verify via GET
  resp2 = await async_client.get(
    f"/api/admin/tenants/{target}/features",
    headers=admin_headers,
  )
  assert "b2b" in resp2.json()["features"]


@pytest.mark.anyio
async def test_plan_downgrade_removes_features(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """Downgrading from enterprise to pro should remove b2b (if no add-on)."""
  target = "plan_test_downgrade"
  await test_db.tenant_capabilities.delete_many({"tenant_id": target})

  # Start with enterprise
  await async_client.patch(
    f"/api/admin/tenants/{target}/plan",
    headers=admin_headers,
    json={"plan": "enterprise"},
  )

  # Clear add-ons
  await async_client.patch(
    f"/api/admin/tenants/{target}/add-ons",
    headers=admin_headers,
    json={"add_ons": []},
  )

  # Verify b2b is in enterprise
  resp1 = await async_client.get(
    f"/api/admin/tenants/{target}/features",
    headers=admin_headers,
  )
  assert "b2b" in resp1.json()["features"]

  # Downgrade to pro
  resp2 = await async_client.patch(
    f"/api/admin/tenants/{target}/plan",
    headers=admin_headers,
    json={"plan": "pro"},
  )
  assert resp2.status_code == 200
  assert "b2b" not in resp2.json()["features"]


@pytest.mark.anyio
async def test_legacy_fallback(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """Tenant with only legacy tenant_features should fallback correctly."""
  target = "plan_test_legacy"
  await test_db.tenant_capabilities.delete_many({"tenant_id": target})
  await test_db.tenant_features.delete_many({"tenant_id": target})

  # Write directly to legacy collection
  from datetime import datetime, timezone
  await test_db.tenant_features.insert_one({
    "tenant_id": target,
    "plan": "core",
    "features": ["b2b", "crm"],
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
  })

  resp = await async_client.get(
    f"/api/admin/tenants/{target}/features",
    headers=admin_headers,
  )
  assert resp.status_code == 200
  body = resp.json()
  assert body["source"] == "legacy_fallback"
  assert "b2b" in body["features"]
  assert "crm" in body["features"]


@pytest.mark.anyio
async def test_invalid_plan_rejected(
  async_client: AsyncClient,
  admin_headers: dict,
) -> None:
  """Invalid plan name should be rejected with 422."""
  resp = await async_client.patch(
    "/api/admin/tenants/test/plan",
    headers=admin_headers,
    json={"plan": "ultra_premium"},
  )
  assert resp.status_code == 422, resp.text
  assert resp.json()["error"]["code"] == "invalid_plan"


@pytest.mark.anyio
async def test_plan_update_creates_audit_log(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """Plan update should write to audit_logs."""
  target = "plan_audit_test"
  await test_db.audit_logs.delete_many({"tenant_id": target})

  await async_client.patch(
    f"/api/admin/tenants/{target}/plan",
    headers=admin_headers,
    json={"plan": "pro"},
  )

  log = await test_db.audit_logs.find_one(
    {"tenant_id": target, "action": "tenant.plan.updated"},
    {"_id": 0},
  )
  assert log is not None
  assert log["after"]["plan"] == "pro"
