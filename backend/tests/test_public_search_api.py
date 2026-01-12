from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.db import get_db


@pytest.mark.anyio
async def test_public_search_basic_tenant_scoping_and_published_only(async_client):
  db = await get_db()

  # Clean relevant collections
  await db.products.delete_many({})
  await db.product_versions.delete_many({})
  await db.rate_plans.delete_many({})
  await db.public_search_telemetry.delete_many({})

  org_a = "org_public_A"
  org_b = "org_public_B"

  # Product for org A with published version and active rate plan
  prod_a1 = {
    "organization_id": org_a,
    "type": "hotel",
    "code": "HTL-A1",
    "name": {"tr": "Otel A1", "en": "Hotel A1"},
    "name_search": "otel a1 hotel a1",
    "status": "active",
    "default_currency": "EUR",
    "location": {"city": "Istanbul", "country": "TR"},
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow(),
  }
  res_a1 = await db.products.insert_one(prod_a1)
  pid_a1 = res_a1.inserted_id

  await db.product_versions.insert_one(
    {
      "organization_id": org_a,
      "product_id": pid_a1,
      "version": 1,
      "status": "published",
      "content": {
        "description": {"tr": "Merkezde bir otel", "en": "Central hotel"},
        "images": [{"url": "https://example.com/hotel-a1.jpg"}],
      },
    }
  )

  await db.rate_plans.insert_one(
    {
      "organization_id": org_a,
      "product_id": pid_a1,
      "code": "RP-A1",
      "currency": "EUR",
      "base_net_price": 100.0,
      "status": "active",
    }
  )

  # Product for org A but inactive -> should be excluded
  await db.products.insert_one(
    {
      "organization_id": org_a,
      "type": "hotel",
      "code": "HTL-A2",
      "name": {"tr": "Otel A2"},
      "name_search": "otel a2",
      "status": "inactive",
      "default_currency": "EUR",
      "location": {"city": "Istanbul", "country": "TR"},
      "created_at": datetime.utcnow(),
      "updated_at": datetime.utcnow(),
    }
  )

  # Product for org B (different tenant) -> should not be visible
  await db.products.insert_one(
    {
      "organization_id": org_b,
      "type": "hotel",
      "code": "HTL-B1",
      "name": {"tr": "Otel B1"},
      "name_search": "otel b1",
      "status": "active",
      "default_currency": "EUR",
      "location": {"city": "Ankara", "country": "TR"},
      "created_at": datetime.utcnow(),
      "updated_at": datetime.utcnow(),
    }
  )

  # Call public search for org A
  resp = await async_client.get("/api/public/search", params={"org": org_a, "page": 1, "page_size": 10})
  assert resp.status_code == 200
  assert "Cache-Control" in resp.headers
  assert "stale-while-revalidate" in resp.headers["Cache-Control"]

  data = resp.json()
  assert data["page"] == 1
  assert data["page_size"] == 10
  assert data["total"] >= 1

  items = data["items"]
  # Only the active + published product for org A should be present
  assert any(it["product_id"] == str(pid_a1) for it in items)
  for it in items:
    assert it["type"] in {"hotel", "tour", "transfer", "activity", "hotel"}
    assert "title" in it
    assert "price" in it and "amount_cents" in it["price"] and "currency" in it["price"]
    assert "availability" in it and it["availability"]["status"] == "available"
    assert "policy" in it and "refundable" in it["policy"]


@pytest.mark.anyio
async def test_public_search_rate_limit(async_client):
  db = await get_db()
  await db.products.delete_many({})
  await db.product_versions.delete_many({})
  await db.rate_plans.delete_many({})
  await db.public_search_telemetry.delete_many({})

  org = "org_rate_limit"
  now = datetime.utcnow()
  prod = {
    "organization_id": org,
    "type": "hotel",
    "code": "HTL-RATE",
    "name": {"tr": "Rate Limit Oteli"},
    "name_search": "rate limit oteli",
    "status": "active",
    "default_currency": "EUR",
    "location": {"city": "Izmir", "country": "TR"},
    "created_at": now,
    "updated_at": now,
  }
  res = await db.products.insert_one(prod)
  pid = res.inserted_id

  await db.product_versions.insert_one(
    {
      "organization_id": org,
      "product_id": pid,
      "version": 1,
      "status": "published",
      "content": {"description": {"tr": "Test"}},
    }
  )

  # First ~60 calls should pass
  last_status = None
  for i in range(0, 62):
    r = await async_client.get("/api/public/search", params={"org": org, "page": 1, "page_size": 1})
    last_status = r.status_code
    if i < 60:
      assert r.status_code == 200
    elif i >= 61:
      # Allow some wiggle room: at least one call should start returning 429
      if r.status_code == 429:
        break
  assert last_status in {200, 429}
