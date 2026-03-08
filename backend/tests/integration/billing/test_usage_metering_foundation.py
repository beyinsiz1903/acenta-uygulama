"""Tests for Usage Metering foundation (PR-UM1)."""
from __future__ import annotations

import pytest

from app.constants.usage_metrics import UsageMetric
from app.errors import AppError
from app.repositories.usage_daily_repository import usage_daily_repo
from app.repositories.usage_ledger_repository import usage_ledger_repo
from app.services.feature_service import feature_service
from app.services.usage_service import get_usage_summary, track_usage_event


@pytest.mark.anyio
async def test_track_usage_event_is_idempotent_and_updates_daily(test_db) -> None:
  tid = "usage_foundation_idempotent"
  org_id = "org_usage_foundation"
  await test_db.usage_ledger.delete_many({"tenant_id": tid})
  await test_db.usage_daily.delete_many({"tenant_id": tid})
  await usage_ledger_repo.ensure_indexes()
  await usage_daily_repo.ensure_indexes()

  inserted_first = await track_usage_event(
    tenant_id=tid,
    organization_id=org_id,
    metric=UsageMetric.RESERVATION_CREATED,
    quantity=1,
    source="test",
    source_event_id="reservation_001",
    metadata={"channel": "unit_test"},
  )
  inserted_second = await track_usage_event(
    tenant_id=tid,
    organization_id=org_id,
    metric=UsageMetric.RESERVATION_CREATED,
    quantity=1,
    source="test",
    source_event_id="reservation_001",
    metadata={"channel": "unit_test"},
  )

  assert inserted_first is True
  assert inserted_second is False

  ledger_count = await test_db.usage_ledger.count_documents({"tenant_id": tid, "metric": UsageMetric.RESERVATION_CREATED})
  assert ledger_count == 1

  daily_doc = await test_db.usage_daily.find_one({"tenant_id": tid, "metric": UsageMetric.RESERVATION_CREATED}, {"_id": 0})
  assert daily_doc is not None
  assert daily_doc["count"] == 1
  assert daily_doc["organization_id"] == org_id


@pytest.mark.anyio
async def test_track_usage_event_rejects_invalid_metric(test_db) -> None:
  tid = "usage_foundation_invalid"
  await test_db.usage_ledger.delete_many({"tenant_id": tid})
  await test_db.usage_daily.delete_many({"tenant_id": tid})

  with pytest.raises(AppError) as exc:
    await track_usage_event(
      tenant_id=tid,
      organization_id="org_invalid",
      metric="invalid.metric",
      source="test",
      source_event_id="invalid_001",
    )

  assert exc.value.code == "invalid_usage_metric"
  assert await test_db.usage_ledger.count_documents({"tenant_id": tid}) == 0
  assert await test_db.usage_daily.count_documents({"tenant_id": tid}) == 0


@pytest.mark.anyio
async def test_get_usage_summary_uses_metering_foundation(test_db) -> None:
  tid = "usage_foundation_summary"
  org_id = "org_usage_summary"
  await test_db.usage_ledger.delete_many({"tenant_id": tid})
  await test_db.usage_daily.delete_many({"tenant_id": tid})
  await test_db.tenant_capabilities.delete_many({"tenant_id": tid})
  await feature_service.set_plan(tid, "starter")

  inserted = await track_usage_event(
    tenant_id=tid,
    organization_id=org_id,
    metric=UsageMetric.RESERVATION_CREATED,
    quantity=3,
    source="test",
    source_event_id="reservation_summary_001",
  )
  assert inserted is True

  summary = await get_usage_summary(tid)
  metric = summary["metrics"][UsageMetric.RESERVATION_CREATED]

  assert summary["organization_id"] == org_id
  assert summary["totals_source"] == "usage_daily"
  assert summary["billing_period"]
  assert metric["used"] == 3
  assert metric["quota"] == 100
  assert metric["remaining"] == 97
  assert metric["ratio"] == 0.03
