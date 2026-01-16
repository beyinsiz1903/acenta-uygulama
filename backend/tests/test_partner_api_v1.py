from __future__ import annotations

import uuid

import pytest

from app.db import get_db


@pytest.mark.anyio
async def test_partner_key_cannot_access_other_org(async_client):
  db = await get_db()

  await db.api_keys.delete_many({})

  org_a = "org_a"
  org_b = "org_b"

  # Seed orgs
  await db.organizations.insert_many([
    {"_id": org_a, "slug": "a", "name": "Org A"},
    {"_id": org_b, "slug": "b", "name": "Org B"},
  ])

  # Seed one product per org
  await db.products.insert_many([
    {
      "_id": "prod_a",
      "organization_id": org_a,
      "type": "hotel",
      "status": "active",
      "name": {"tr": "Hotel A"},
    },
    {
      "_id": "prod_b",
      "organization_id": org_b,
      "type": "hotel",
      "status": "active",
      "name": {"tr": "Hotel B"},
    },
  ])

  # Create API key for org_a via admin endpoint
  login_res = await async_client.post(
    "/api/auth/login",
    json={"email": "admin@acenta.test", "password": "admin123"},
  )
  assert login_res.status_code == 200
  token = login_res.json()["access_token"]

  res = await async_client.post(
    "/api/admin/api-keys",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "partner-a", "scopes": ["products:read"]},
  )
  assert res.status_code == 200
  api_key = res.json()["api_key"]

  # Partner search should only see org_a products
  res_search = await async_client.get(
    "/api/partner/products/search",
    headers={"X-API-Key": api_key},
  )
  assert res_search.status_code == 200
  items = res_search.json()["items"]
  assert any("Hotel A" in (i["title"] or "") for i in items)
  assert all("Hotel B" not in (i["title"] or "") for i in items)


@pytest.mark.anyio
async def test_partner_rate_limit_returns_429(async_client):
  db = await get_db()
  await db.api_keys.delete_many({})
  await db.rate_limit_buckets.delete_many({})

  org = "org_rate_limit"
  await db.organizations.insert_one({"_id": org, "slug": "rl", "name": "RL Org"})

  # Single product for org
  await db.products.insert_one(
    {
      "_id": "prod_rl",
      "organization_id": org,
      "type": "hotel",
      "status": "active",
      "name": {"tr": "Hotel RL"},
    }
  )

  login_res = await async_client.post(
    "/api/auth/login",
    json={"email": "admin@acenta.test", "password": "admin123"},
  )
  assert login_res.status_code == 200
  token = login_res.json()["access_token"]

  res = await async_client.post(
    "/api/admin/api-keys",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "partner-rl", "scopes": ["products:read"]},
  )
  api_key = res.json()["api_key"]

  # Hit the endpoint many times to trigger limit
  last_status = None
  for _ in range(70):
    r = await async_client.get(
      "/api/partner/products/search",
      headers={"X-API-Key": api_key},
    )
    last_status = r.status_code
    if last_status == 429:
      break
  assert last_status == 429


@pytest.mark.anyio
async def test_partner_happy_path_search_quote_booking_docs(async_client):
  db = await get_db()
  await db.api_keys.delete_many({})

  org = "org_partner_flow"
  await db.organizations.insert_one({"_id": org, "slug": "pf", "name": "Partner Flow Org"})

  # Minimal product + rate_plan for search/quote/booking path
  from datetime import date, timedelta
  from app.utils import now_utc

  hotel_id = "hotel_pf"
  await db.products.insert_one(
    {
      "_id": hotel_id,
      "organization_id": org,
      "type": "hotel",
      "status": "active",
      "name": {"tr": "Hotel PF"},
      "location": {"city": "Istanbul", "country": "TR"},
      "default_currency": "EUR",
      "created_at": now_utc(),
    }
  )

  await db.rate_plans.insert_one(
    {
      "_id": "rp_pf",
      "organization_id": org,
      "product_id": hotel_id,
      "status": "active",
      "currency": "EUR",
      "board": "BB",
      "base_net_price": 100.0,
    }
  )

  # Login & create api key
  login_res = await async_client.post(
    "/api/auth/login",
    json={"email": "admin@acenta.test", "password": "admin123"},
  )
  token = login_res.json()["access_token"]

  res_key = await async_client.post(
    "/api/admin/api-keys",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "partner-flow", "scopes": ["products:read", "quotes:write", "bookings:write", "documents:read"]},
  )
  api_key = res_key.json()["api_key"]

  # search
  res_search = await async_client.get(
    "/api/partner/products/search",
    headers={"X-API-Key": api_key},
  )
  assert res_search.status_code == 200
  items = res_search.json()["items"]
  assert any("Hotel PF" in (i["title"] or "") for i in items)

  # quote
  today = date.today()
  tomorrow = today + timedelta(days=1)

  res_quote = await async_client.post(
    "/api/partner/quotes",
    headers={"X-API-Key": api_key},
    json={
      "product_id": hotel_id,
      "date_from": today.isoformat(),
      "date_to": tomorrow.isoformat(),
      "adults": 2,
      "children": 0,
      "rooms": 1,
      "currency": "EUR",
    },
  )
  assert res_quote.status_code == 200
  quote_body = res_quote.json()
  quote_id = quote_body["quote_id"]

  # booking
  idem = uuid.uuid4().hex
  res_booking = await async_client.post(
    "/api/partner/bookings",
    headers={"X-API-Key": api_key},
    json={
      "quote_id": quote_id,
      "guest": {
        "full_name": "Partner Guest",
        "email": "guest@example.com",
        "phone": "+905551112233",
      },
      "payment": {"method": "stripe", "return_url": "https://example.com/thanks"},
      "idempotency_key": idem,
    },
  )
  assert res_booking.status_code in (200, 503)
  body_booking = res_booking.json()

  # Even if provider_unavailable (Stripe test env), we must get deterministic response shape
  assert "ok" in body_booking

  # documents
  booking_id = body_booking.get("booking_id") or "dummy"
  res_docs = await async_client.get(
    f"/api/partner/bookings/{booking_id}/documents",
    headers={"X-API-Key": api_key},
  )
  assert res_docs.status_code == 200
  assert "voucher_url" in res_docs.json()
