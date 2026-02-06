"""Test that PATCH /api/admin/tenants/{id}/features writes an audit log."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.db import get_db


@pytest.mark.anyio
async def test_audit_log_written_on_feature_update(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """Feature update should create an audit_logs entry."""
  target = "audit_test_tenant_1"

  # Clear any existing audit logs
  await test_db.audit_logs.delete_many({"tenant_id": target})

  # PATCH features
  resp = await async_client.patch(
    f"/api/admin/tenants/{target}/features",
    headers=admin_headers,
    json={"features": ["b2b", "crm"]},
  )
  assert resp.status_code == 200, resp.text

  # Check audit log was written
  log = await test_db.audit_logs.find_one(
    {"tenant_id": target, "action": "tenant_features.updated"},
    {"_id": 0},
  )
  assert log is not None, "Audit log not found"
  assert log["action"] == "tenant_features.updated"
  assert "b2b" in log["after"]["features"]
  assert "crm" in log["after"]["features"]
  assert log["actor_email"] == "admin@acenta.test"
  assert log["id"].startswith("audit_")


@pytest.mark.anyio
async def test_audit_log_captures_before_state(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """Audit log should capture the before-state of features."""
  target = "audit_test_tenant_2"

  # Set initial features
  await async_client.patch(
    f"/api/admin/tenants/{target}/features",
    headers=admin_headers,
    json={"features": ["crm"]},
  )

  # Clear audit logs to isolate next call
  await test_db.audit_logs.delete_many({"tenant_id": target})

  # Update features
  await async_client.patch(
    f"/api/admin/tenants/{target}/features",
    headers=admin_headers,
    json={"features": ["crm", "b2b", "reports"]},
  )

  log = await test_db.audit_logs.find_one(
    {"tenant_id": target, "action": "tenant_features.updated"},
    {"_id": 0},
  )
  assert log is not None
  assert log["before"]["features"] == ["crm"]
  assert set(log["after"]["features"]) == {"crm", "b2b", "reports"}
