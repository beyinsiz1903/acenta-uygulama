from __future__ import annotations

from bson import ObjectId
import pytest

from app.constants.usage_metrics import UsageMetric
from app.repositories.usage_daily_repository import usage_daily_repo
from app.repositories.usage_ledger_repository import usage_ledger_repo
from app.services.feature_service import feature_service
from app.utils import now_utc


async def _seed_reservation_prereqs(test_db) -> tuple[str, str, ObjectId, ObjectId, str]:
  admin = await test_db.users.find_one({"email": "admin@acenta.test"})
  assert admin is not None

  org_id = str(admin["organization_id"])
  tenant_id = str(admin["tenant_id"])
  travel_date = "2026-04-10"
  product_id = ObjectId()
  customer_id = ObjectId()

  await test_db.products.insert_one(
    {
      "_id": product_id,
      "organization_id": org_id,
      "type": "activity",
      "title": "Metered Reservation Product",
      "description": "Usage metering integration test product",
      "created_at": now_utc(),
      "updated_at": now_utc(),
    }
  )
  await test_db.customers.insert_one(
    {
      "_id": customer_id,
      "organization_id": org_id,
      "name": "Metered Customer",
      "email": "metered.customer@example.test",
      "phone": "+90 555 000 0000",
      "created_at": now_utc(),
      "updated_at": now_utc(),
    }
  )
  await test_db.inventory.insert_one(
    {
      "organization_id": org_id,
      "product_id": product_id,
      "date": travel_date,
      "capacity_total": 10,
      "capacity_available": 10,
      "price": 1500.0,
      "restrictions": {"closed": False, "cta": False, "ctd": False},
      "created_at": now_utc(),
      "updated_at": now_utc(),
    }
  )

  return org_id, tenant_id, product_id, customer_id, travel_date


async def _seed_tour(test_db, org_id: str) -> ObjectId:
  tour_id = ObjectId()
  await test_db.tours.insert_one(
    {
      "_id": tour_id,
      "organization_id": org_id,
      "type": "tour",
      "name": "Metered Kapadokya Turu",
      "name_search": "metered kapadokya turu",
      "description": "Tour reservation metering test",
      "destination": "Kapadokya",
      "departure_city": "İstanbul",
      "category": "Kültür",
      "base_price": 4200.0,
      "currency": "TRY",
      "status": "active",
      "duration_days": 1,
      "max_participants": 20,
      "created_at": now_utc(),
      "updated_at": now_utc(),
    }
  )
  return tour_id


@pytest.mark.anyio
async def test_reservation_created_tracks_usage_on_new_create(async_client, admin_headers, test_db) -> None:
  org_id, tenant_id, product_id, customer_id, travel_date = await _seed_reservation_prereqs(test_db)
  await test_db.usage_ledger.delete_many({"tenant_id": tenant_id})
  await test_db.usage_daily.delete_many({"tenant_id": tenant_id})
  await feature_service.set_plan(tenant_id, "starter")
  await usage_ledger_repo.ensure_indexes()
  await usage_daily_repo.ensure_indexes()

  payload = {
    "idempotency_key": "reservation-created-metric-001",
    "product_id": str(product_id),
    "customer_id": str(customer_id),
    "start_date": travel_date,
    "pax": 2,
    "channel": "direct",
  }
  resp = await async_client.post("/api/reservations/reserve", json=payload, headers=admin_headers)
  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert body["organization_id"] == org_id

  ledger_doc = await test_db.usage_ledger.find_one(
    {"tenant_id": tenant_id, "metric": UsageMetric.RESERVATION_CREATED},
    {"_id": 0},
  )
  assert ledger_doc is not None
  assert ledger_doc["source_event_id"] == payload["idempotency_key"]
  assert ledger_doc["metadata"]["reservation_id"] == body["id"]

  summary_resp = await async_client.get(f"/api/admin/billing/tenants/{tenant_id}/usage", headers=admin_headers)
  assert summary_resp.status_code == 200, summary_resp.text
  summary = summary_resp.json()
  assert summary["metrics"][UsageMetric.RESERVATION_CREATED]["used"] == 1
  assert summary["metrics"][UsageMetric.RESERVATION_CREATED]["quota"] == 100


@pytest.mark.anyio
async def test_reservation_created_does_not_double_count_idempotent_retry(async_client, admin_headers, test_db) -> None:
  _, tenant_id, product_id, customer_id, travel_date = await _seed_reservation_prereqs(test_db)
  await test_db.usage_ledger.delete_many({"tenant_id": tenant_id})
  await test_db.usage_daily.delete_many({"tenant_id": tenant_id})
  await feature_service.set_plan(tenant_id, "starter")
  await usage_ledger_repo.ensure_indexes()
  await usage_daily_repo.ensure_indexes()

  payload = {
    "idempotency_key": "reservation-created-metric-duplicate",
    "product_id": str(product_id),
    "customer_id": str(customer_id),
    "start_date": travel_date,
    "pax": 1,
    "channel": "direct",
  }
  first = await async_client.post("/api/reservations/reserve", json=payload, headers=admin_headers)
  second = await async_client.post("/api/reservations/reserve", json=payload, headers=admin_headers)

  assert first.status_code == 200, first.text
  assert second.status_code == 200, second.text
  assert first.json()["id"] == second.json()["id"]

  ledger_count = await test_db.usage_ledger.count_documents(
    {"tenant_id": tenant_id, "metric": UsageMetric.RESERVATION_CREATED}
  )
  daily_doc = await test_db.usage_daily.find_one(
    {"tenant_id": tenant_id, "metric": UsageMetric.RESERVATION_CREATED},
    {"_id": 0},
  )
  assert ledger_count == 1
  assert daily_doc is not None
  assert daily_doc["count"] == 1


@pytest.mark.anyio
async def test_reservation_created_is_not_incremented_on_status_change(async_client, admin_headers, test_db) -> None:
  _, tenant_id, product_id, customer_id, travel_date = await _seed_reservation_prereqs(test_db)
  await test_db.usage_ledger.delete_many({"tenant_id": tenant_id})
  await test_db.usage_daily.delete_many({"tenant_id": tenant_id})
  await feature_service.set_plan(tenant_id, "starter")
  await usage_ledger_repo.ensure_indexes()
  await usage_daily_repo.ensure_indexes()

  create_resp = await async_client.post(
    "/api/reservations/reserve",
    json={
      "idempotency_key": "reservation-created-metric-status-change",
      "product_id": str(product_id),
      "customer_id": str(customer_id),
      "start_date": travel_date,
      "pax": 2,
      "channel": "direct",
    },
    headers=admin_headers,
  )
  assert create_resp.status_code == 200, create_resp.text
  reservation_id = create_resp.json()["id"]

  confirm_resp = await async_client.post(f"/api/reservations/{reservation_id}/confirm", headers=admin_headers)
  cancel_resp = await async_client.post(f"/api/reservations/{reservation_id}/cancel", headers=admin_headers)
  assert confirm_resp.status_code == 200, confirm_resp.text
  assert cancel_resp.status_code == 200, cancel_resp.text

  summary = await async_client.get(f"/api/admin/billing/tenants/{tenant_id}/usage", headers=admin_headers)
  assert summary.status_code == 200, summary.text
  body = summary.json()
  assert body["metrics"][UsageMetric.RESERVATION_CREATED]["used"] == 1


@pytest.mark.anyio
async def test_tour_reservation_create_tracks_usage(async_client, admin_headers, test_db) -> None:
  org_id, tenant_id, _, _, _ = await _seed_reservation_prereqs(test_db)
  await test_db.usage_ledger.delete_many({"tenant_id": tenant_id})
  await test_db.usage_daily.delete_many({"tenant_id": tenant_id})
  await feature_service.set_plan(tenant_id, "starter")
  await usage_ledger_repo.ensure_indexes()
  await usage_daily_repo.ensure_indexes()

  tour_id = await _seed_tour(test_db, org_id)

  resp = await async_client.post(
    f"/api/tours/{tour_id}/reserve",
    json={
      "travel_date": "2026-04-20",
      "adults": 2,
      "children": 1,
      "guest_name": "Tour Guest",
      "guest_email": "tour.guest@example.test",
      "guest_phone": "+90 555 111 2233",
      "notes": "Tour usage metering test",
    },
    headers=admin_headers,
  )
  assert resp.status_code == 201, resp.text

  summary = await async_client.get(f"/api/admin/billing/tenants/{tenant_id}/usage", headers=admin_headers)
  assert summary.status_code == 200, summary.text
  body = summary.json()
  assert body["metrics"][UsageMetric.RESERVATION_CREATED]["used"] == 1

  ledger_doc = await test_db.usage_ledger.find_one(
    {"tenant_id": tenant_id, "metric": UsageMetric.RESERVATION_CREATED},
    {"_id": 0, "source": 1, "source_event_id": 1},
  )
  assert ledger_doc is not None
  assert ledger_doc["source"] == "tours.reserve"
  assert ledger_doc["source_event_id"]
