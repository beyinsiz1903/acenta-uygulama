"""
Finance OS Phase 2C.1–2C.2 Test
FXService: fx_rates lookup + booking snapshot idempotency
"""

from datetime import datetime, timezone, timedelta

import anyio
import pymongo

from app.services.fx import FXService, ORG_FUNCTIONAL_CCY
from app.utils import now_utc
from app.errors import AppError

MONGO_URL = "mongodb://localhost:27017/"
DB_NAME = "test_database"


async def _setup_db():
  client = pymongo.MongoClient(MONGO_URL)
  db = client[DB_NAME]
  # Use raw motor-like interface via db attribute names in tests
  return db


async def _seed_rate(db, org_id: str, quote: str, rate: float, as_of: datetime):
  await db.fx_rates.insert_one(
    {
      "organization_id": org_id,
      "base": ORG_FUNCTIONAL_CCY,
      "quote": quote,
      "rate": rate,
      "provider": "manual",
      "as_of": as_of,
      "created_at": now_utc(),
      "created_by_email": "test@fx.local",
    }
  )


async def test_fxservice_get_rate_success():
  db = await _setup_db()
  org_id = "org_fx_test_1"
  quote = "TRY"
  as_of1 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
  as_of2 = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)

  # clean
  await db.fx_rates.delete_many({"organization_id": org_id})
  await db.fx_rate_snapshots.delete_many({"organization_id": org_id})

  # older rate
  await _seed_rate(db, org_id, quote, 34.0, as_of1)
  # newer rate
  await _seed_rate(db, org_id, quote, 35.0, as_of2)

  svc = FXService(db)

  # explicit as_of before newer rate -> should pick 34.0
  r1 = await svc.get_rate(org_id, quote, as_of1)
  assert r1.rate == 34.0

  # explicit as_of after newer rate -> should pick 35.0
  r2 = await svc.get_rate(org_id, quote, datetime(2026, 1, 3, 0, 0, tzinfo=timezone.utc))
  assert r2.rate == 35.0


async def test_fxservice_get_rate_not_found():
  db = await _setup_db()
  org_id = "org_fx_test_2"

  await db.fx_rates.delete_many({"organization_id": org_id})

  svc = FXService(db)

  try:
    await svc.get_rate(org_id, "TRY")
    assert False, "expected fx_rate_not_found"
  except AppError as e:
    assert e.code == "fx_rate_not_found"


async def test_fxservice_snapshot_idempotent_booking():
  db = await _setup_db()
  org_id = "org_fx_test_3"
  quote = "TRY"
  booking_id = "book_fx_test_1"

  await db.fx_rates.delete_many({"organization_id": org_id})
  await db.fx_rate_snapshots.delete_many({"organization_id": org_id})

  as_of = datetime(2026, 1, 4, 12, 0, tzinfo=timezone.utc)
  await _seed_rate(db, org_id, quote, 36.5, as_of)

  svc = FXService(db)

  snap1 = await svc.snapshot_for_booking(org_id, booking_id, quote, as_of)
  snap2 = await svc.snapshot_for_booking(org_id, booking_id, quote, as_of)

  assert snap1["snapshot_id"] == snap2["snapshot_id"]
  assert snap1["rate"] == snap2["rate"] == 36.5

  # ensure only one snapshot doc exists
  count = await db.fx_rate_snapshots.count_documents({"organization_id": org_id})
  assert count == 1


async def test_fxservice_base_equals_quote_short_circuit():
  db = await _setup_db()
  org_id = "org_fx_test_4"

  svc = FXService(db)
  r = await svc.get_rate(org_id, ORG_FUNCTIONAL_CCY, as_of=None)
  assert r.rate == 1.0
  assert r.base == ORG_FUNCTIONAL_CCY
  assert r.quote == ORG_FUNCTIONAL_CCY

  snap = await svc.snapshot_for_booking(org_id, "book_fx_eur", ORG_FUNCTIONAL_CCY, as_of=None)
  assert snap["rate"] == 1.0
  assert snap["snapshot_id"] is None


def test_phase_2c_1_fx_service():
  anyio.run(test_fxservice_get_rate_success)
  anyio.run(test_fxservice_get_rate_not_found)
  anyio.run(test_fxservice_snapshot_idempotent_booking)
  anyio.run(test_fxservice_base_equals_quote_short_circuit)
