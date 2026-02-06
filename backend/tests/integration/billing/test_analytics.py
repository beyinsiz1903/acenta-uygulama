"""Tests for Revenue Analytics endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.services.feature_service import feature_service
from app.services.usage_service import track_usage


@pytest.mark.anyio
async def test_revenue_summary_empty(
  async_client: AsyncClient,
  admin_headers: dict,
) -> None:
  """Revenue summary with no subscriptions returns zero metrics."""
  resp = await async_client.get("/api/admin/analytics/revenue-summary", headers=admin_headers)
  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert "active_subscriptions_count" in body
  assert "mrr_gross_active" in body
  assert "mrr_at_risk" in body
  assert "generated_at" in body


@pytest.mark.anyio
async def test_revenue_summary_with_subscription(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """Revenue summary counts active subscriptions correctly."""
  now = datetime.now(timezone.utc)

  # Seed plan catalog
  await test_db.billing_plan_catalog.update_one(
    {"plan": "pro", "interval": "monthly", "currency": "TRY"},
    {"$set": {"plan": "pro", "interval": "monthly", "currency": "TRY", "amount": 999.0, "active": True, "updated_at": now}},
    upsert=True,
  )

  # Create a subscription
  await test_db.billing_subscriptions.update_one(
    {"tenant_id": "analytics_test_1"},
    {"$set": {
      "tenant_id": "analytics_test_1",
      "provider": "stripe",
      "provider_subscription_id": "sub_analytics_1",
      "plan": "pro",
      "status": "active",
      "cancel_at_period_end": False,
      "mode": "test",
      "updated_at": now,
    }, "$setOnInsert": {"created_at": now}},
    upsert=True,
  )

  resp = await async_client.get("/api/admin/analytics/revenue-summary", headers=admin_headers)
  body = resp.json()
  assert body["active_subscriptions_count"] >= 1
  assert body["mrr_gross_active"] >= 999.0


@pytest.mark.anyio
async def test_revenue_summary_past_due_at_risk(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """past_due subscription contributes to mrr_at_risk."""
  now = datetime.now(timezone.utc)

  await test_db.billing_plan_catalog.update_one(
    {"plan": "starter", "interval": "monthly", "currency": "TRY"},
    {"$set": {"plan": "starter", "interval": "monthly", "currency": "TRY", "amount": 499.0, "active": True, "updated_at": now}},
    upsert=True,
  )

  await test_db.billing_subscriptions.update_one(
    {"tenant_id": "analytics_pastdue_1"},
    {"$set": {
      "tenant_id": "analytics_pastdue_1",
      "provider": "stripe",
      "provider_subscription_id": "sub_pastdue_1",
      "plan": "starter",
      "status": "past_due",
      "grace_period_until": (now + timedelta(days=5)).isoformat(),
      "cancel_at_period_end": False,
      "mode": "test",
      "updated_at": now,
    }, "$setOnInsert": {"created_at": now}},
    upsert=True,
  )

  resp = await async_client.get("/api/admin/analytics/revenue-summary", headers=admin_headers)
  body = resp.json()
  assert body["past_due_count"] >= 1
  assert body["mrr_at_risk"] >= 499.0
  assert body["grace_count"] >= 1


@pytest.mark.anyio
async def test_usage_overview_buckets(
  async_client: AsyncClient,
  admin_headers: dict,
  test_db,
) -> None:
  """Usage overview returns quota buckets."""
  resp = await async_client.get("/api/admin/analytics/usage-overview", headers=admin_headers)
  assert resp.status_code == 200
  body = resp.json()
  assert "quota_buckets" in body
  assert len(body["quota_buckets"]) == 5
  bucket_names = [b["bucket"] for b in body["quota_buckets"]]
  assert "0-20%" in bucket_names
  assert "100%+" in bucket_names


@pytest.mark.anyio
async def test_non_admin_rejected(
  async_client: AsyncClient,
  agency_headers: dict,
) -> None:
  """Non-admin users cannot access analytics."""
  resp = await async_client.get("/api/admin/analytics/revenue-summary", headers=agency_headers)
  assert resp.status_code == 403
