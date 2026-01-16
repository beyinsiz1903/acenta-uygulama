from __future__ import annotations

import pytest

from app.db import get_db
from app.services.integration_hub import (
  INTEGRATION_SYNC_RATES,
  enqueue_sync_jobs_for_provider,
  register_integration_job_handlers,
)
from app.services.jobs import claim_job, process_claimed_job


@pytest.mark.asyncio
async def test_integration_sync_mock_provider_updates_rate_plans():
  db = await get_db()

  await db.integration_providers.delete_many({})
  await db.integration_provider_credentials.delete_many({})
  await db.integration_mappings.delete_many({})
  await db.rate_plans.delete_many({})
  await db.jobs.delete_many({})

  org_id = "org_mock_integration"

  # Seed a provider and credentials
  await db.integration_providers.insert_one(
    {
      "key": "mock_hotel_provider",
      "name": "Mock Hotel Provider",
      "category": "hotel",
    }
  )

  await db.integration_provider_credentials.insert_one(
    {
      "organization_id": org_id,
      "provider_key": "mock_hotel_provider",
      "name": "default",
      "status": "active",
      "config": {},
    }
  )

  # Seed a rate_plan and mapping
  rp = {
    "_id": "rp_1",
    "organization_id": org_id,
    "name": "Test Plan",
  }
  await db.rate_plans.insert_one(rp)

  await db.integration_mappings.insert_one(
    {
      "organization_id": org_id,
      "provider_key": "mock_hotel_provider",
      "mapping_type": "rate_plan",
      "internal_id": "rp_1",
      "external_id": "EXT_RP_1",
      "meta": {},
    }
  )

  register_integration_job_handlers()

  # Enqueue a rates sync job
  await enqueue_sync_jobs_for_provider(
    organization_id=org_id,
    provider_key="mock_hotel_provider",
    scope="rates",
  )

  # Claim + process all jobs
  while True:
    job = await claim_job(db, worker_id="w_integration", now=None, lock_ttl_seconds=60)
    if not job:
      break
    await process_claimed_job(db, job)

  # Assert the rate_plan has a last_mock_sync_at field set
  doc = await db.rate_plans.find_one({"_id": "rp_1", "organization_id": org_id})
  assert doc is not None
  assert "last_mock_sync_at" in doc
