from __future__ import annotations

from typing import Any, Dict

import pytest
from httpx import AsyncClient

from app.db import get_db

LISTINGS_PATH = "/api/b2b/listings"
AVAILABLE_PATH = "/api/b2b/listings/available"
MATCH_REQUEST_PATH = "/api/b2b/match-request"


@pytest.mark.anyio
async def test_b2b_debug_happy_path_flow(
  provider_client: AsyncClient,
  seller_client: AsyncClient,
  partner_relationship_active: Dict[str, Any],
  test_db,
  provider_tenant,
  seller_tenant,
  provider_user,
  seller_user,
) -> None:
  """Debug version of the happy path test."""

  print(f"\n=== DEBUG INFO ===")
  print(f"Provider tenant: {provider_tenant['_id']}")
  print(f"Seller tenant: {seller_tenant['_id']}")
  print(f"Provider user: {provider_user['_id']} - {provider_user['email']}")
  print(f"Seller user: {seller_user['_id']} - {seller_user['email']}")
  print(f"Partner relationship: {partner_relationship_active}")
  
  # Check auth headers
  print(f"Provider client headers: {dict(provider_client.headers)}")
  print(f"Seller client headers: {dict(seller_client.headers)}")

  # 1) Provider creates listing
  print(f"\n=== STEP 1: Provider creates listing ===")
  create_resp = await provider_client.post(
    LISTINGS_PATH,
    json={
      "title": "B2B Test Listing",
      "description": "Integration happy path",
      "category": "tour",
      "base_price": 1000.0,
      "provider_commission_rate": 15.0,
    },
  )
  print(f"Create response status: {create_resp.status_code}")
  print(f"Create response body: {create_resp.text}")
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()
  print(f"Created listing: {listing}")
  assert listing["id"].startswith("lst_"), listing
  assert listing["currency"] == "TRY"

  # 2) Seller sees listing in available listings
  print(f"\n=== STEP 2: Seller checks available listings ===")
  available_resp = await seller_client.get(AVAILABLE_PATH)
  print(f"Available response status: {available_resp.status_code}")
  print(f"Available response body: {available_resp.text}")
  assert available_resp.status_code == 200, available_resp.text
  available = available_resp.json()
  print(f"Available listings: {available}")
  ids = {item["id"] for item in available}
  print(f"Available listing IDs: {ids}")
  print(f"Looking for listing ID: {listing['id']}")
  
  # Debug: Check partner relationships in DB
  db = await get_db()
  all_rels = await db.partner_relationships.find({}).to_list(length=10)
  print(f"All partner relationships in DB: {all_rels}")
  
  # Debug: Check listings in DB
  all_listings = await db.b2b_listings.find({}).to_list(length=10)
  print(f"All listings in DB: {all_listings}")
  
  assert listing["id"] in ids, f"Listing {listing['id']} not found in available listings {ids}"