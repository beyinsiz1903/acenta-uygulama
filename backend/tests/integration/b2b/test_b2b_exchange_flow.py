from __future__ import annotations

from typing import Any, Dict

import pytest
from httpx import AsyncClient

from app.db import get_db

LISTINGS_PATH = "/api/b2b/listings"
AVAILABLE_PATH = "/api/b2b/listings/available"
MATCH_REQUEST_PATH = "/api/b2b/match-request"


async def clear_tenant_features(test_db, tenant_id: str) -> None:
  """Helper to clear tenant_features for a given tenant_id.
  
  This removes any existing tenant_features document for the tenant,
  effectively disabling all features for that tenant.
  """
  await test_db.tenant_features.delete_many({"tenant_id": tenant_id})


@pytest.mark.anyio
async def test_b2b_tenant_isolation_cannot_request_own_listing(
  seller_client: AsyncClient,
  test_db,
  seller_tenant,
  enable_b2b_features,
) -> None:
  """Seller cannot create match request on its own listing.

  - Seller creates a listing under its own tenant (acts as provider)
  - Listing should not appear in /listings/available for the same tenant
  - Direct /match-request must return cannot_request_own_listing
  """

  # 1) Seller creates listing for its own tenant
  create_resp = await seller_client.post(
    LISTINGS_PATH,
    json={
      "title": "Own Listing",
      "base_price": 900.0,
      "provider_commission_rate": 12.0,
    },
  )
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()

  # Sağlayıcı tenant id'si seller_tenant ile aynı olmalı
  assert listing["provider_tenant_id"] == str(seller_tenant["_id"])

  # 2) Same-tenant available listesinde bu listing görünmemeli (partner ilişkisi yok)
  available_resp = await seller_client.get(AVAILABLE_PATH)
  assert available_resp.status_code == 200, available_resp.text
  available = available_resp.json()
  assert all(item["id"] != listing["id"] for item in available)

  # 3) Same-tenant doğrudan match-request denemesi yasak
  match_resp = await seller_client.post(
    MATCH_REQUEST_PATH,
    json={"listing_id": listing["id"], "requested_price": 1000.0},
  )
  assert match_resp.status_code in (400, 403, 422), match_resp.text
  body = match_resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "cannot_request_own_listing", body


@pytest.mark.anyio
async def test_b2b_happy_path_flow(
  provider_client: AsyncClient,
  seller_client: AsyncClient,
  partner_relationship_active: Dict[str, Any],
  test_db,
  enable_b2b_features,
) -> None:
  """Provider creates a listing, seller requests it, provider approves and completes.

  Validates:
  - Listing created with lst_* id and TRY currency
  - Seller sees listing in /listings/available thanks to active partner relationship
  - Match request created with mreq_* id and pending status
  - Provider can approve then complete
  - platform_fee_amount is computed as requested_price * platform_fee_rate
  - status_history tracks pending -> approved -> completed
  """

  # 1) Provider creates listing
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
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()
  assert listing["id"].startswith("lst_"), listing
  assert listing["currency"] == "TRY"

  # 2) Seller sees listing in available listings
  available_resp = await seller_client.get(AVAILABLE_PATH)
  assert available_resp.status_code == 200, available_resp.text
  available = available_resp.json()
  ids = {item["id"] for item in available}
  assert listing["id"] in ids

  # 3) Seller creates match request
  match_resp = await seller_client.post(
    MATCH_REQUEST_PATH,
    json={
      "listing_id": listing["id"],
      "requested_price": 1200.0,
    },
  )
  assert match_resp.status_code == 200, match_resp.text
  match = match_resp.json()
  assert match["id"].startswith("mreq_"), match
  assert match["listing_id"] == listing["id"]
  assert match["status"] == "pending"
  assert match["platform_fee_rate"] == pytest.approx(0.01)
  assert match["platform_fee_amount"] == pytest.approx(0.0)

  # 4) Provider sees incoming request
  incoming_resp = await provider_client.get(f"{MATCH_REQUEST_PATH}/incoming")
  assert incoming_resp.status_code == 200, incoming_resp.text
  incoming = incoming_resp.json()
  assert any(m["id"] == match["id"] for m in incoming)

  # 5) Provider approves then completes
  approve_resp = await provider_client.patch(f"{MATCH_REQUEST_PATH}/{match['id']}/approve")
  assert approve_resp.status_code == 200, approve_resp.text
  approved = approve_resp.json()
  assert approved["status"] == "approved"

  complete_resp = await provider_client.patch(f"{MATCH_REQUEST_PATH}/{match['id']}/complete")
  assert complete_resp.status_code == 200, complete_resp.text
  completed = complete_resp.json()
  assert completed["status"] == "completed"

  # 6) DB-level verification: platform_fee_amount and status_history
  db = await get_db()
  db_match = await db.b2b_match_requests.find_one({"id": match["id"]})
  assert db_match is not None
  assert db_match["platform_fee_rate"] == pytest.approx(0.01)
  assert db_match["platform_fee_amount"] == pytest.approx(1200.0 * 0.01)

  history_statuses = [e["status"] for e in db_match.get("status_history", [])]
  assert "pending" in history_statuses
  assert "approved" in history_statuses
  assert "completed" in history_statuses


@pytest.mark.anyio
async def test_b2b_not_active_partner_cannot_see_or_request(
  provider_client: AsyncClient,
  seller_client: AsyncClient,
  test_db,
  provider_tenant,
  seller_tenant,
  enable_b2b_features,
) -> None:
  """Non-active partner relationship should block visibility and match requests.

  - With status != active, seller should not see provider's listing in /available
  - Direct /match-request should return not_active_partner error code
  """

  # 1) Insert non-active partner relationship (invited)
  await test_db.partner_relationships.insert_one(
    {
      "seller_tenant_id": str(provider_tenant["_id"]),
      "buyer_tenant_id": str(seller_tenant["_id"]),
      "status": "invited",
    }
  )

  # 2) Provider creates listing
  create_resp = await provider_client.post(
    LISTINGS_PATH,
    json={
      "title": "Listing without active partner",
      "base_price": 1000.0,
      "provider_commission_rate": 10.0,
    },
  )
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()

  # 3) Seller should not see this listing in /available
  available_resp = await seller_client.get(AVAILABLE_PATH)
  assert available_resp.status_code == 200, available_resp.text
  available = available_resp.json()
  assert all(item["id"] != listing["id"] for item in available)

  # 4) Seller trying to create match-request should get not_active_partner
  match_resp = await seller_client.post(
    MATCH_REQUEST_PATH,
    json={"listing_id": listing["id"], "requested_price": 1100.0},
  )
  assert match_resp.status_code in (400, 403, 422), match_resp.text
  body = match_resp.json()
  # AppError format: {"error": {"code": ..., "message": ..., "details": {...}}}
  error = body.get("error") or {}
  assert error.get("code") == "not_active_partner", body


@pytest.mark.anyio
async def test_b2b_cross_org_cannot_see_or_request(
  provider_client: AsyncClient,
  other_client: AsyncClient,
  enable_b2b_features_all,
) -> None:
  """Cross-org tenant cannot see or request another org's listing.

  - Provider in org A creates listing
  - Tenant in org B calls /listings/available -> listing not visible
  - Tenant in org B calls /match-request -> not_active_partner
  """

  # Provider (org A) creates listing
  create_resp = await provider_client.post(
    LISTINGS_PATH,
    json={
      "title": "Cross-org Listing",
      "base_price": 800.0,
      "provider_commission_rate": 10.0,
    },
  )
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()

  # Cross-org tenant should not see listing in /available
  available_resp = await other_client.get(AVAILABLE_PATH)
  assert available_resp.status_code == 200, available_resp.text
  available = available_resp.json()
  assert all(item["id"] != listing["id"] for item in available)

  # Cross-org tenant trying to create match-request should get not_active_partner
  match_resp = await other_client.post(
    MATCH_REQUEST_PATH,
    json={"listing_id": listing["id"], "requested_price": 950.0},
  )
  assert match_resp.status_code in (400, 403, 422), match_resp.text
  body = match_resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "not_active_partner", body


@pytest.mark.anyio
async def test_b2b_third_tenant_cannot_approve_match(
  provider_client: AsyncClient,
  seller_client: AsyncClient,
  third_client: AsyncClient,
  partner_relationship_active: Dict[str, Any],
  enable_b2b_features_all,
) -> None:
  """Third tenant (no provider role on match) cannot approve another tenant's match.

  - Provider A creates listing
  - Seller B creates match request
  - Third tenant C attempts to approve -> 403 forbidden
  """

  # 1) Provider creates listing
  create_resp = await provider_client.post(
    LISTINGS_PATH,
    json={
      "title": "Approval Isolation Listing",
      "base_price": 700.0,
      "provider_commission_rate": 10.0,
    },
  )
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()

  # 2) Seller creates match request
  match_resp = await seller_client.post(
    MATCH_REQUEST_PATH,
    json={"listing_id": listing["id"], "requested_price": 750.0},
  )
  assert match_resp.status_code == 200, match_resp.text
  match = match_resp.json()

  # 3) Third tenant tries to approve -> should be forbidden
  approve_resp = await third_client.patch(f"{MATCH_REQUEST_PATH}/{match['id']}/approve")
  assert approve_resp.status_code == 403, approve_resp.text
  body = approve_resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "forbidden", body




@pytest.mark.anyio
async def test_b2b_invalid_status_pending_cannot_complete(
  provider_client: AsyncClient,
  seller_client: AsyncClient,
  partner_relationship_active: Dict[str, Any],
) -> None:
  """pending durumundaki talep doğrudan complete edilemez.

  Beklenen:
  - /match-request/{id}/complete çağrısı 400 + error.code="invalid_status_transition" döner.
  """

  # 1) Provider listing + pending match oluştur
  create_resp = await provider_client.post(
    LISTINGS_PATH,
    json={
      "title": "Invalid Transition Pending -> Complete",
      "base_price": 500.0,
      "provider_commission_rate": 10.0,
    },
  )
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()

  match_resp = await seller_client.post(
    MATCH_REQUEST_PATH,
    json={"listing_id": listing["id"], "requested_price": 550.0},
  )
  assert match_resp.status_code == 200, match_resp.text
  match = match_resp.json()
  assert match["status"] == "pending"

  # 2) Doğrudan complete etmeye çalış
  complete_resp = await provider_client.patch(f"{MATCH_REQUEST_PATH}/{match['id']}/complete")
  assert complete_resp.status_code == 400, complete_resp.text
  body = complete_resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "invalid_status_transition", body


@pytest.mark.anyio
async def test_b2b_invalid_status_rejected_cannot_approve(
  provider_client: AsyncClient,
  seller_client: AsyncClient,
  partner_relationship_active: Dict[str, Any],
) -> None:
  """rejected durumundaki talep tekrar approve edilemez."""

  # 1) Pending match oluştur
  create_resp = await provider_client.post(
    LISTINGS_PATH,
    json={
      "title": "Invalid Transition Rejected -> Approve",
      "base_price": 600.0,
      "provider_commission_rate": 10.0,
    },
  )
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()

  match_resp = await seller_client.post(
    MATCH_REQUEST_PATH,
    json={"listing_id": listing["id"], "requested_price": 650.0},
  )
  assert match_resp.status_code == 200, match_resp.text
  match = match_resp.json()

  # 2) Önce reject et (geçerli)
  reject_resp = await provider_client.patch(f"{MATCH_REQUEST_PATH}/{match['id']}/reject")
  assert reject_resp.status_code == 200, reject_resp.text
  rejected = reject_resp.json()
  assert rejected["status"] == "rejected"

  # 3) Sonra tekrar approve etmeye çalış
  approve_resp = await provider_client.patch(f"{MATCH_REQUEST_PATH}/{match['id']}/approve")
  assert approve_resp.status_code == 400, approve_resp.text
  body = approve_resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "invalid_status_transition", body


@pytest.mark.anyio
async def test_b2b_invalid_status_approved_cannot_reapprove(
  provider_client: AsyncClient,
  seller_client: AsyncClient,
  partner_relationship_active: Dict[str, Any],
) -> None:
  """approved durumundaki talep tekrar approve edilemez."""

  # 1) Pending match oluştur
  create_resp = await provider_client.post(
    LISTINGS_PATH,
    json={
      "title": "Invalid Transition Approved -> Approve",
      "base_price": 700.0,
      "provider_commission_rate": 10.0,
    },
  )
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()

  match_resp = await seller_client.post(
    MATCH_REQUEST_PATH,
    json={"listing_id": listing["id"], "requested_price": 750.0},
  )
  assert match_resp.status_code == 200, match_resp.text
  match = match_resp.json()

  # 2) Geçerli approve
  approve_resp_1 = await provider_client.patch(f"{MATCH_REQUEST_PATH}/{match['id']}/approve")
  assert approve_resp_1.status_code == 200, approve_resp_1.text
  approved = approve_resp_1.json()
  assert approved["status"] == "approved"

  # 3) Tekrar approve etmeye çalış
  approve_resp_2 = await provider_client.patch(f"{MATCH_REQUEST_PATH}/{match['id']}/approve")
  assert approve_resp_2.status_code == 400, approve_resp_2.text
  body = approve_resp_2.json()
  error = body.get("error") or {}
  assert error.get("code") == "invalid_status_transition", body


@pytest.mark.anyio
async def test_b2b_invalid_status_completed_cannot_change(
  provider_client: AsyncClient,
  seller_client: AsyncClient,
  partner_relationship_active: Dict[str, Any],
) -> None:
  """completed durumundaki talep tekrar approve/reject/complete edilemez."""

  # 1) Pending match oluştur
  create_resp = await provider_client.post(
    LISTINGS_PATH,
    json={
      "title": "Invalid Transition Completed -> Any",
      "base_price": 800.0,
      "provider_commission_rate": 10.0,
    },
  )
  assert create_resp.status_code == 200, create_resp.text
  listing = create_resp.json()

  match_resp = await seller_client.post(
    MATCH_REQUEST_PATH,
    json={"listing_id": listing["id"], "requested_price": 850.0},
  )
  assert match_resp.status_code == 200, match_resp.text
  match = match_resp.json()

  # 2) Geçerli approve + complete
  approve_resp = await provider_client.patch(f"{MATCH_REQUEST_PATH}/{match['id']}/approve")
  assert approve_resp.status_code == 200, approve_resp.text
  complete_resp = await provider_client.patch(f"{MATCH_REQUEST_PATH}/{match['id']}/complete")
  assert complete_resp.status_code == 200, complete_resp.text
  completed = complete_resp.json()
  assert completed["status"] == "completed"

  # 3) Tekrar approve / reject / complete çağrıları invalid olmalı
  for path in [
    f"{MATCH_REQUEST_PATH}/{match['id']}/approve",
    f"{MATCH_REQUEST_PATH}/{match['id']}/reject",
    f"{MATCH_REQUEST_PATH}/{match['id']}/complete",
  ]:
    resp = await provider_client.patch(path)
    assert resp.status_code == 400, resp.text
    body = resp.json()
    error = body.get("error") or {}
    assert error.get("code") == "invalid_status_transition", body


@pytest.mark.anyio
async def test_b2b_feature_flag_enforcement(
  seller_client: AsyncClient,
  test_db,
  seller_tenant,
) -> None:
  """When tenant_features for the current tenant DO NOT include 'b2b', 
  all /api/b2b/* endpoints return 403 with error.code == 'feature_not_enabled'.
  
  This test verifies that the @require_tenant_feature("b2b") decorator
  properly blocks access when the tenant doesn't have the b2b feature enabled.
  """
  
  # 1) Clear tenant_features for seller_tenant to ensure no "b2b" feature
  await clear_tenant_features(test_db, str(seller_tenant["_id"]))
  
  # 2) Try to call GET /api/b2b/listings/available - should return 403
  available_resp = await seller_client.get(AVAILABLE_PATH)
  assert available_resp.status_code == 403, available_resp.text
  body = available_resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "feature_not_enabled", body
  
  # 3) Try to call POST /api/b2b/listings - should return 403
  create_listing_resp = await seller_client.post(
    LISTINGS_PATH,
    json={
      "title": "Test Listing",
      "base_price": 1000.0,
      "provider_commission_rate": 15.0,
    },
  )
  assert create_listing_resp.status_code == 403, create_listing_resp.text
  body = create_listing_resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "feature_not_enabled", body
  
  # 4) Try to call GET /api/b2b/listings/my - should return 403
  my_listings_resp = await seller_client.get(f"{LISTINGS_PATH}/my")
  assert my_listings_resp.status_code == 403, my_listings_resp.text
  body = my_listings_resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "feature_not_enabled", body
  
  # 5) Try to call POST /api/b2b/match-request - should return 403
  match_request_resp = await seller_client.post(
    MATCH_REQUEST_PATH,
    json={"listing_id": "lst_dummy", "requested_price": 1200.0},
  )
  assert match_request_resp.status_code == 403, match_request_resp.text
  body = match_request_resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "feature_not_enabled", body
  
  # 6) Try to call GET /api/b2b/match-request/my - should return 403
  my_matches_resp = await seller_client.get(f"{MATCH_REQUEST_PATH}/my")
  assert my_matches_resp.status_code == 403, my_matches_resp.text
  body = my_matches_resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "feature_not_enabled", body
  
  # 7) Try to call GET /api/b2b/match-request/incoming - should return 403
  incoming_matches_resp = await seller_client.get(f"{MATCH_REQUEST_PATH}/incoming")
  assert incoming_matches_resp.status_code == 403, incoming_matches_resp.text
  body = incoming_matches_resp.json()
  error = body.get("error") or {}
  assert error.get("code") == "feature_not_enabled", body

