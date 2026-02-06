"""Test that B2B exchange operations write events to b2b_events collection."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.integration.b2b.conftest import enable_b2b_feature_for_tenant


@pytest.mark.anyio
async def test_b2b_events_written_on_happy_path(
  provider_client: AsyncClient,
  seller_client: AsyncClient,
  test_db,
  provider_tenant,
  seller_tenant,
  partner_relationship_active,
  enable_b2b_features,
) -> None:
  """Happy path: listing create, match request, approve, complete should write events."""
  provider_tid = str(provider_tenant["_id"])
  seller_tid = str(seller_tenant["_id"])

  # Clear events
  await test_db.b2b_events.delete_many({})

  # 1) Create listing
  resp = await provider_client.post("/api/b2b/listings", json={
    "title": "Event Test Hotel",
    "base_price": 1000,
    "description": "test",
    "category": "hotel",
    "provider_commission_rate": 10,
  })
  assert resp.status_code == 200, resp.text
  listing_id = resp.json()["id"]

  # 2) Create match request
  resp2 = await seller_client.post("/api/b2b/match-request", json={
    "listing_id": listing_id,
    "requested_price": 1200,
  })
  assert resp2.status_code == 200, resp2.text
  mreq_id = resp2.json()["id"]

  # 3) Approve
  resp3 = await provider_client.patch(f"/api/b2b/match-request/{mreq_id}/approve")
  assert resp3.status_code == 200, resp3.text

  # 4) Complete
  resp4 = await provider_client.patch(f"/api/b2b/match-request/{mreq_id}/complete")
  assert resp4.status_code == 200, resp4.text

  # Verify events
  events = await test_db.b2b_events.find({}, {"_id": 0}).sort("created_at", 1).to_list(100)

  event_types = [e["event_type"] for e in events]
  assert "listing.created" in event_types, f"Missing listing.created: {event_types}"
  assert "match_request.created" in event_types, f"Missing match_request.created: {event_types}"

  # Status changes: pending->approved, approved->completed
  status_changes = [e for e in events if e["event_type"] == "match_request.status_changed"]
  assert len(status_changes) >= 2, f"Expected >=2 status changes, got {len(status_changes)}"

  approve_evt = next((e for e in status_changes if e["payload"]["to"] == "approved"), None)
  assert approve_evt is not None, "Missing approved status change event"
  assert approve_evt["payload"]["from"] == "pending"

  complete_evt = next((e for e in status_changes if e["payload"]["to"] == "completed"), None)
  assert complete_evt is not None, "Missing completed status change event"
  assert complete_evt["payload"]["from"] == "approved"
  assert complete_evt["payload"]["platform_fee_amount"] > 0


@pytest.mark.anyio
async def test_b2b_event_has_tenant_ids(
  provider_client: AsyncClient,
  seller_client: AsyncClient,
  test_db,
  provider_tenant,
  seller_tenant,
  partner_relationship_active,
  enable_b2b_features,
) -> None:
  """Events should contain correct tenant IDs for isolation."""
  await test_db.b2b_events.delete_many({})

  # Create listing
  resp = await provider_client.post("/api/b2b/listings", json={
    "title": "Tenant ID Test",
    "base_price": 500,
    "description": "test",
    "category": "hotel",
    "provider_commission_rate": 5,
  })
  listing_id = resp.json()["id"]

  evt = await test_db.b2b_events.find_one(
    {"event_type": "listing.created", "entity_id": listing_id},
    {"_id": 0},
  )
  assert evt is not None
  assert evt["provider_tenant_id"] == str(provider_tenant["_id"])
  assert evt["id"].startswith("evt_")
