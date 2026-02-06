"""Tests for Usage Ledger tracking and quota logic."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.usage_service import track_usage, check_quota, get_usage_summary
from app.services.feature_service import feature_service


@pytest.mark.anyio
async def test_usage_tracking_writes_to_ledger(test_db) -> None:
  """track_usage should write to usage_ledger collection."""
  tid = "usage_test_track_1"
  await test_db.usage_ledger.delete_many({"tenant_id": tid})
  await test_db.tenant_capabilities.delete_many({"tenant_id": tid})

  # Set plan to pro (starter skips tracking)
  await feature_service.set_plan(tid, "pro")

  await track_usage(tid, "b2b.match_request", 1, "b2b", "mreq_test_001")

  doc = await test_db.usage_ledger.find_one(
    {"tenant_id": tid, "source_event_id": "mreq_test_001"},
    {"_id": 0},
  )
  assert doc is not None
  assert doc["metric"] == "b2b.match_request"
  assert doc["quantity"] == 1
  assert doc["source"] == "b2b"
  assert doc["billed"] is False


@pytest.mark.anyio
async def test_usage_idempotency(test_db) -> None:
  """Same source_event_id should not create duplicate entries."""
  tid = "usage_test_idemp"
  await test_db.usage_ledger.delete_many({"tenant_id": tid})
  await test_db.tenant_capabilities.delete_many({"tenant_id": tid})
  await feature_service.set_plan(tid, "pro")

  # Ensure unique index
  from app.repositories.usage_ledger_repository import usage_ledger_repo
  await usage_ledger_repo.ensure_indexes()

  await track_usage(tid, "b2b.match_request", 1, "b2b", "mreq_dup_001")
  await track_usage(tid, "b2b.match_request", 1, "b2b", "mreq_dup_001")  # duplicate

  count = await test_db.usage_ledger.count_documents(
    {"tenant_id": tid, "source_event_id": "mreq_dup_001"}
  )
  assert count == 1, f"Expected 1 entry, got {count}"


@pytest.mark.anyio
async def test_starter_plan_skips_tracking(test_db) -> None:
  """Starter plan should not track usage."""
  tid = "usage_test_starter"
  await test_db.usage_ledger.delete_many({"tenant_id": tid})
  await test_db.tenant_capabilities.delete_many({"tenant_id": tid})
  await feature_service.set_plan(tid, "starter")

  await track_usage(tid, "b2b.match_request", 1, "b2b", "mreq_starter_001")

  count = await test_db.usage_ledger.count_documents({"tenant_id": tid})
  assert count == 0


@pytest.mark.anyio
async def test_quota_check_within_limit(test_db) -> None:
  """check_quota should return not exceeded when within limit."""
  tid = "usage_test_quota_ok"
  await test_db.usage_ledger.delete_many({"tenant_id": tid})
  await test_db.tenant_capabilities.delete_many({"tenant_id": tid})
  await feature_service.set_plan(tid, "pro")  # pro has 100 quota for b2b.match_request

  # Track 5 requests
  for i in range(5):
    await track_usage(tid, "b2b.match_request", 1, "b2b", f"mreq_quota_{i}")

  result = await check_quota(tid, "b2b.match_request")
  assert result["quota"] == 100
  assert result["used"] == 5
  assert result["remaining"] == 95
  assert result["exceeded"] is False


@pytest.mark.anyio
async def test_quota_exceeded(test_db) -> None:
  """check_quota should detect exceeded quota."""
  tid = "usage_test_quota_exceeded"
  await test_db.usage_ledger.delete_many({"tenant_id": tid})
  await test_db.tenant_capabilities.delete_many({"tenant_id": tid})
  await test_db.audit_logs.delete_many({"tenant_id": tid})
  await feature_service.set_plan(tid, "pro")  # 100 quota

  from app.repositories.usage_ledger_repository import usage_ledger_repo
  await usage_ledger_repo.ensure_indexes()

  # Track 100 requests to hit quota
  for i in range(100):
    await track_usage(tid, "b2b.match_request", 1, "b2b", f"mreq_exc_{i}")

  result = await check_quota(tid, "b2b.match_request")
  assert result["exceeded"] is True
  assert result["used"] == 100
  assert result["remaining"] == 0

  # Should have written audit log
  log = await test_db.audit_logs.find_one(
    {"tenant_id": tid, "action": "usage.quota_exceeded"},
    {"_id": 0},
  )
  assert log is not None


@pytest.mark.anyio
async def test_usage_summary_endpoint(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """GET /api/admin/billing/tenants/{id}/usage should return summary."""
  tid = "usage_test_summary"
  await test_db.usage_ledger.delete_many({"tenant_id": tid})
  await test_db.tenant_capabilities.delete_many({"tenant_id": tid})
  await feature_service.set_plan(tid, "pro")

  await track_usage(tid, "b2b.match_request", 1, "b2b", "mreq_sum_001")

  resp = await async_client.get(
    f"/api/admin/billing/tenants/{tid}/usage",
    headers=admin_headers,
  )
  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert body["plan"] == "pro"
  assert "b2b.match_request" in body["metrics"]
  assert body["metrics"]["b2b.match_request"]["used"] == 1
  assert body["metrics"]["b2b.match_request"]["quota"] == 100
