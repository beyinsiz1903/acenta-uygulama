from __future__ import annotations

import re
from typing import Any, Dict, List

import pytest
from httpx import AsyncClient

from app.db import get_db

LISTINGS_PATH = "/api/b2b/listings"
MY_LISTINGS_PATH = "/api/b2b/listings/my"
AVAILABLE_PATH = "/api/b2b/listings/available"
MATCH_REQUEST_PATH = "/api/b2b/match-request"
MY_MATCHES_PATH = "/api/b2b/match-request/my"
INCOMING_MATCHES_PATH = "/api/b2b/match-request/incoming"

LISTING_ID_RE = re.compile(r"^lst_[0-9a-f]{32}$")
MATCH_ID_RE = re.compile(r"^mreq_[0-9a-f]{32}$")


def _assert_no_internal_fields(item: Dict[str, Any], extra_forbidden: List[str] | None = None) -> None:
  forbidden = {"_id"}
  if extra_forbidden:
    forbidden.update(extra_forbidden)
  for key in forbidden:
    assert key not in item, f"Internal field '{key}' leaked in response: {item}"


@pytest.mark.anyio
async def test_listing_id_prefix_and_no_mongo_id_leak(provider_client: AsyncClient, enable_b2b_features) -> None:
  """Listing public id'leri lst_* formatında olmalı ve _id leak etmemeli."""

  create_resp = await provider_client.post(
    LISTINGS_PATH,
    json={
      "title": "ID Contract Listing",
      "description": "ID contract test",
      "category": "tour",
      "base_price": 1000.0,
      "provider_commission_rate": 10.0,
    },
  )
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()

  # Tekil response
  assert LISTING_ID_RE.match(listing["id"]), listing
  _assert_no_internal_fields(listing)

  # /listings/my endpoint'i de aynı kontratı korumalı
  my_resp = await provider_client.get(MY_LISTINGS_PATH)
  assert my_resp.status_code == 200, my_resp.text
  items = my_resp.json()
  assert any(it["id"] == listing["id"] for it in items)
  for it in items:
    assert LISTING_ID_RE.match(it["id"]), it
    _assert_no_internal_fields(it)


@pytest.mark.anyio
async def test_match_id_prefix_and_no_internal_fields_leak(
  provider_client: AsyncClient,
  seller_client: AsyncClient,
  partner_relationship_active: Dict[str, Any],
  enable_b2b_features,
) -> None:
  """Match id'leri mreq_* formatında olmalı ve internal alanlar sızmamalı.

  Özellikle:
  - match.id -> ^mreq_[0-9a-f]{32}$
  - match.listing_id -> lst_* (public id)
  - _id ve listing_mongo_id response'ta olmamalı
  """

  # 1) Provider listing oluşturur
  create_resp = await provider_client.post(
    LISTINGS_PATH,
    json={
      "title": "ID Contract Match Listing",
      "base_price": 900.0,
      "provider_commission_rate": 12.0,
    },
  )
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()
  assert LISTING_ID_RE.match(listing["id"]), listing

  # 2) Seller match-request oluşturur
  match_resp = await seller_client.post(
    MATCH_REQUEST_PATH,
    json={"listing_id": listing["id"], "requested_price": 950.0},
  )
  assert match_resp.status_code == 200, match_resp.text
  match = match_resp.json()

  assert MATCH_ID_RE.match(match["id"]), match
  assert LISTING_ID_RE.match(match["listing_id"]), match
  _assert_no_internal_fields(match, extra_forbidden=["listing_mongo_id"])

  # 3) DB'de listing_mongo_id tutuluyor ama response'ta yok olmalı
  db = await get_db()
  db_match = await db.b2b_match_requests.find_one({"id": match["id"]})
  assert db_match is not None
  assert "listing_mongo_id" in db_match  # internal olarak DB'de var


@pytest.mark.anyio
async def test_list_endpoints_do_not_leak_internal_fields(
  provider_client: AsyncClient,
  seller_client: AsyncClient,
  partner_relationship_active: Dict[str, Any],
  enable_b2b_features,
) -> None:
  """Tüm liste endpoint'lerinde internal alanlar (_id, listing_mongo_id) sızmamalı."""

  # 1) Provider listing + match seed'i
  create_resp = await provider_client.post(
    LISTINGS_PATH,
    json={
      "title": "ID Contract List Listing",
      "base_price": 1100.0,
      "provider_commission_rate": 15.0,
    },
  )
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()

  match_resp = await seller_client.post(
    MATCH_REQUEST_PATH,
    json={"listing_id": listing["id"], "requested_price": 1200.0},
  )
  assert match_resp.status_code == 200, match_resp.text

  # 2) /listings/my
  my_listings = (await provider_client.get(MY_LISTINGS_PATH)).json()
  for it in my_listings:
    _assert_no_internal_fields(it)

  # 3) /listings/available
  available = (await seller_client.get(AVAILABLE_PATH)).json()
  for it in available:
    _assert_no_internal_fields(it)

  # 4) /match-request/my
  my_matches = (await seller_client.get(MY_MATCHES_PATH)).json()
  for it in my_matches:
    _assert_no_internal_fields(it, extra_forbidden=["listing_mongo_id"])

  # 5) /match-request/incoming
  incoming = (await provider_client.get(INCOMING_MATCHES_PATH)).json()
  for it in incoming:
    _assert_no_internal_fields(it, extra_forbidden=["listing_mongo_id"])
