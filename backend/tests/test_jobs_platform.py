from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.db import get_db
from app.services.jobs import enqueue_job, claim_job, process_claimed_job, register_job_handler


def _now() -> datetime:
  return datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_job_claim_is_atomic(monkeypatch):
  db = await get_db()

  # Clear collection for test isolation
  await db.jobs.delete_many({})

  org_id = "org_test_atomic"
  for i in range(3):
    await enqueue_job(db, organization_id=org_id, type="test.noop", payload={"i": i})

  claimed: list[dict] = []

  async def fake_handler(db_, job):  # pragma: no cover - handler is trivial
    claimed.append(job)

  register_job_handler("test.noop", fake_handler)

  # Simulate two workers racing for jobs
  worker_ids = ["w1", "w2"]

  async def worker_run(worker_id: str):
    while True:
      job = await claim_job(db, worker_id=worker_id, now=_now(), lock_ttl_seconds=60)
      if not job:
        break
      await process_claimed_job(db, job)

  await asyncio.gather(*(worker_run(w) for w in worker_ids))

  # All 3 jobs should have been processed exactly once
  assert len(claimed) == 3

  statuses = await db.jobs.find({}, {"_id": 0, "status": 1}).to_list(10)
  assert all(row.get("status") == "succeeded" for row in statuses)


@pytest.mark.asyncio
async def test_retry_backoff_to_dead():
  db = await get_db()
  await db.jobs.delete_many({})

  org_id = "org_test_retry"

  # Handler that always fails
  async def always_fail(db_, job):  # pragma: no cover - error path tested via state
    raise RuntimeError("boom")

  register_job_handler("test.always_fail", always_fail)

  job_doc = await enqueue_job(
    db,
    organization_id=org_id,
    type="test.always_fail",
    payload={},
    max_attempts=2,
  )

  # Run small loop until job becomes dead
  for _ in range(5):
    job = await claim_job(db, worker_id="w1", now=_now(), lock_ttl_seconds=60)
    if not job:
      # Wait for next_run_at
      await asyncio.sleep(0.01)
      continue
    await process_claimed_job(db, job)

  final_doc = await db.jobs.find_one({"_id": job_doc["_id"]}, {"_id": 0})
  assert final_doc is not None
  assert final_doc["status"] == "dead"
  assert final_doc["attempts"] == 2
