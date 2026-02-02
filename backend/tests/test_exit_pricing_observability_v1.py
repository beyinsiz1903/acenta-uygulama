from __future__ import annotations

from typing import Any

import jwt
import pytest
from bson import ObjectId
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.exit_pricing_overlay_audit_written
@pytest.mark.anyio
async def test_pricing_overlay_applied_audit_written(test_db: Any, async_client: AsyncClient) -> None:
    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "OBS Org1", "slug": "obs_org1", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "obs-tenant-1",
            "organization_id": org_id,
            "brand_name": "Obs Tenant 1",
            "primary_domain": "obs-tenant-1.example.com",
            "subdomain": "obs-tenant-1",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "obs1@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "obs-tenant-1",
    }

    payload = {
        "destination": "IST",
        "check_in": "2025-06-01",
        "check_out": "2025-06-05",
        "adults": 2,
        "children": 0,
        "supplier_codes": ["mock"],
    }

    resp = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    offers = data.get("offers") or []
    assert offers, (
        f"expected offers but got 0; payload={payload}; headers={{'X-Tenant-Key': headers.get('X-Tenant-Key')}}; resp={data}"
    )

    offer = offers[0]
    offer_token = offer["offer_token"]

    # Audit log should contain PRICING_OVERLAY_APPLIED for this offer
    audit = await test_db.audit_logs.find_one(
        {"organization_id": org_id, "action": "PRICING_OVERLAY_APPLIED", "target.id": offer_token}
    )
    assert audit is not None
    meta = audit.get("meta") or {}
    assert meta.get("event_source") == "offers_search"
    # buyer_tenant_id is stored as the internal tenant ObjectId string, not the public tenant_key
    assert meta.get("buyer_tenant_id") == str(tenant.inserted_id)
    assert meta.get("offer_token") == offer_token
    assert "session_id" in meta
    assert isinstance(meta.get("base_amount"), (int, float))
    assert isinstance(meta.get("final_amount"), (int, float))


@pytest.mark.exit_booking_repriced_audit_written
@pytest.mark.anyio
async def test_booking_repriced_audit_written(test_db: Any, async_client: AsyncClient) -> None:
    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "OBS Org2", "slug": "obs_org2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "obs-tenant-2",
            "organization_id": org_id,
            "brand_name": "Obs Tenant 2",
            "primary_domain": "obs-tenant-2.example.com",
            "subdomain": "obs-tenant-2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "obs2@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "obs-tenant-2",
    }

    # Search first to create session and offers
    payload = {
        "destination": "IST",
        "check_in": "2025-06-01",
        "check_out": "2025-06-02",
        "adults": 1,
        "children": 0,
        "supplier_codes": ["mock"],
    }

    resp_search = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp_search.status_code == status.HTTP_200_OK, resp_search.text
    search_data = resp_search.json()
    session_id = search_data["session_id"]
    offers = search_data.get("offers") or []
    assert offers, f"expected offers but got 0; response={search_data}"
    offer = offers[0]

    # Create booking from canonical offer
    create_payload = {
        "session_id": session_id,
        "offer_token": offer["offer_token"],
        "buyer_tenant_id": "obs-tenant-2",
        "customer": {
            "full_name": "Obs Customer 2",
            "email": "obs2@example.com",
        },
    }

    resp_booking = await client.post("/api/bookings/from-canonical-offer", json=create_payload, headers=headers)
    assert resp_booking.status_code == status.HTTP_201_CREATED, resp_booking.text
    booking = resp_booking.json()
    booking_id = booking.get("id") or booking.get("booking_id")
    assert booking_id

    audit = await test_db.audit_logs.find_one(
        {"organization_id": org_id, "action": "BOOKING_REPRICED", "target.id": booking_id}
    )
    assert audit is not None
    meta = audit.get("meta") or {}
    assert meta.get("event_source") == "booking_from_canonical_offer"
    assert meta.get("booking_id") == booking_id
    assert meta.get("session_id") == session_id
    assert isinstance(meta.get("final_amount"), (int, float))


@pytest.mark.exit_pricing_mismatch_audit_written
@pytest.mark.anyio
async def test_pricing_mismatch_audit_written(test_db: Any, async_client: AsyncClient) -> None:
    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "OBS Org3", "slug": "obs_org3", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    await test_db.tenants.insert_one(
        {
            "tenant_key": "obs-tenant-3",
            "organization_id": org_id,
            "brand_name": "Obs Tenant 3",
            "primary_domain": "obs-tenant-3.example.com",
            "subdomain": "obs-tenant-3",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "obs3@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "obs-tenant-3",
    }

    # Step 1: search with initial pricing rule (10%)
    await test_db.pricing_rules.insert_one(
        {
            "organization_id": org_id,
            "status": "active",
            "priority": 100,
            "scope": {"agency_id": "obs-tenant-3", "product_type": "hotel"},
            "validity": {},
            "action": {"type": "markup_percent", "value": 10.0},
            "updated_at": now,
        }
    )

    payload = {
        "destination": "IST",
        "check_in": "2025-06-01",
        "check_out": "2025-06-02",
        "adults": 1,
        "children": 0,
        "supplier_codes": ["mock"],
    }

    resp_search = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp_search.status_code == status.HTTP_200_OK, resp_search.text
    search_data = resp_search.json()
    session_id = search_data["session_id"]
    offers = search_data.get("offers") or []
    assert offers, f"expected offers but got 0; response={search_data}"
    offer = offers[0]

    # Step 2: change pricing rule for booking stage (e.g. 30%)
    await test_db.pricing_rules.delete_many({"organization_id": org_id})
    await test_db.pricing_rules.insert_one(
        {
            "organization_id": org_id,
            "status": "active",
            "priority": 100,
            "scope": {"agency_id": "obs-tenant-3", "product_type": "hotel"},
            "validity": {},
            "action": {"type": "markup_percent", "value": 30.0},
            "updated_at": now,
        }
    )

    # Step 3: create booking from canonical offer
    create_payload = {
        "session_id": session_id,
        "offer_token": offer["offer_token"],
        "buyer_tenant_id": "obs-tenant-3",
        "customer": {
            "full_name": "Obs Customer 3",
            "email": "obs3@example.com",
        },
    }

    resp_booking = await client.post("/api/bookings/from-canonical-offer", json=create_payload, headers=headers)
    assert resp_booking.status_code == status.HTTP_201_CREATED, resp_booking.text
    booking = resp_booking.json()
    booking_id = booking.get("id") or booking.get("booking_id")
    assert booking_id

    # PRICING_MISMATCH_DETECTED should be logged
    audit = await test_db.audit_logs.find_one(
        {"organization_id": org_id, "action": "PRICING_MISMATCH_DETECTED", "target.id": booking_id}
    )
    assert audit is not None
    meta = audit.get("meta") or {}
    assert meta.get("booking_id") == booking_id
    assert meta.get("session_id") == session_id
    assert isinstance(meta.get("search_final_amount"), (int, float))
    assert isinstance(meta.get("booking_final_amount"), (int, float))
    assert isinstance(meta.get("delta"), (int, float))
    assert isinstance(meta.get("tolerance"), (int, float))
    assert meta.get("delta") > meta.get("tolerance")
    # rule ids are informational; just ensure keys exist
    assert "search_pricing_rule_id" in meta
    assert "booking_pricing_rule_id" in meta
