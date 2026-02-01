from __future__ import annotations

from typing import Any

import jwt
import pytest
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.exit_canonical_schema_enforced
@pytest.mark.anyio
async def test_canonical_offers_schema_and_no_raw_leakage(test_db: Any, async_client: AsyncClient) -> None:
    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "CANON Org", "slug": "canon_org", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "canon-tenant",
            "organization_id": org_id,
            "brand_name": "Canon Tenant",
            "primary_domain": "canon-tenant.example.com",
            "subdomain": "canon-tenant",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "canon@example.com"
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
        "X-Tenant-Key": "canon-tenant",
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

    assert "session_id" in data
    assert "expires_at" in data
    offers = data.get("offers") or []
    assert offers, "Expected at least one canonical offer from mock supplier"

    # Schema checks & raw leakage guard
    for o in offers:
        assert set(o.keys()) == {
            "offer_token",
            "supplier_code",
            "supplier_offer_id",
            "product_type",
            "hotel",
            "stay",
            "room",
            "cancellation_policy",
            "price",
            "availability_token",
            "raw_fingerprint",
        }
        assert o["supplier_code"] == "mock"
        # No supplier-specific raw payload
        assert "raw" not in o
        assert "xml" not in o
        assert "paximum" not in str(o).lower()


@pytest.mark.exit_supplier_response_no_leak
@pytest.mark.anyio
async def test_canonical_offers_no_supplier_raw_leakage(test_db: Any, async_client: AsyncClient) -> None:
    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "CANON Org2", "slug": "canon_org2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "canon-tenant-2",
            "organization_id": org_id,
            "brand_name": "Canon Tenant 2",
            "primary_domain": "canon-tenant-2.example.com",
            "subdomain": "canon-tenant-2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "canon2@example.com"
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
        "X-Tenant-Key": "canon-tenant-2",
    }

    payload = {
        "destination": "IST",
        "check_in": "2025-06-01",
        "check_out": "2025-06-05",
        "adults": 2,
        "children": 0,
        # We include only mock here to avoid dependency on live Paximum upstream
        "supplier_codes": ["mock"],
    }

    resp = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.text
    # No obvious supplier raw markers (rough signature scan)
    forbidden_signatures = [
        "<xml",  # XML payloads
        "offerId",  # upstream Paximum field
        "rateKey",  # typical supplier rate identifier
        "HotelSearch",
        "Paximum",
    ]
    for sig in forbidden_signatures:
        assert sig not in body, f"Unexpected raw supplier signature found: {sig}"


@pytest.mark.exit_search_cache_ttl
@pytest.mark.anyio
async def test_search_session_ttl_and_indexes(test_db: Any, async_client: AsyncClient) -> None:
    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "CANON Org3", "slug": "canon_org3", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "canon-tenant-3",
            "organization_id": org_id,
            "brand_name": "Canon Tenant 3",
            "primary_domain": "canon-tenant-3.example.com",
            "subdomain": "canon-tenant-3",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "canon3@example.com"
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
        "X-Tenant-Key": "canon-tenant-3",
    }

    payload = {
        "destination": "IST",
        "check_in": "2025-06-01",
        "check_out": "2025-06-02",
        "adults": 1,
        "children": 0,
        "supplier_codes": ["mock"],
    }

    resp = await client.post("/api/offers/search", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    session_id = data["session_id"]

    # Check session document exists in DB
    from bson import ObjectId

    session_doc = await test_db.search_sessions.find_one({"_id": ObjectId(session_id)})
    assert session_doc is not None
    assert "expires_at" in session_doc

    # Check offer_index and offers are consistent
    offers = session_doc.get("offers") or []
    offer_index = session_doc.get("offer_index") or {}
    tokens = set()
    for o in offers:
        token = o.get("offer_token")
        assert token is not None
        tokens.add(token)
        idx = offer_index.get(token)
        assert idx is not None
        assert idx.get("supplier_offer_id") == o.get("supplier_offer_id")
        assert idx.get("supplier_code") == o.get("supplier_code")
    assert len(tokens) == len(offers)

    # Check TTL index exists on search_sessions.expires_at
    indexes = await test_db.search_sessions.index_information()
    ttl_index = None
    for name, spec in indexes.items():
        keys = spec.get("key") or []
        if keys and keys[0][0] == "expires_at":
            ttl_index = spec
            break
    assert ttl_index is not None
    assert ttl_index.get("expireAfterSeconds") == 0


@pytest.mark.exit_offer_token_booking_draft
@pytest.mark.anyio
async def test_booking_from_canonical_offer_creates_draft_booking(test_db: Any, async_client: AsyncClient) -> None:
    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "CANON Org4", "slug": "canon_org4", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "canon-tenant-4",
            "organization_id": org_id,
            "brand_name": "Canon Tenant 4",
            "primary_domain": "canon-tenant-4.example.com",
            "subdomain": "canon-tenant-4",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_key = "canon-tenant-4"

    email = "canon4@example.com"
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
        "X-Tenant-Key": tenant_key,
    }

    # 1) Search canonical offers
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
    assert offers
    offer = offers[0]

    # 2) Create booking from canonical offer
    create_payload = {
        "session_id": session_id,
        "offer_token": offer["offer_token"],
        "buyer_tenant_id": tenant_key,
        "customer": {
            "full_name": "Canonical Test Customer",
            "email": "canon4@example.com",
        },
    }

    resp_booking = await client.post("/api/bookings/from-canonical-offer", json=create_payload, headers=headers)
    assert resp_booking.status_code == status.HTTP_201_CREATED, resp_booking.text
    booking = resp_booking.json()
    assert booking.get("state") in {"draft", "created"}
    offer_ref = booking.get("offer_ref") or {}
    assert offer_ref.get("supplier") == "mock"
    assert offer_ref.get("supplier_offer_id") == offer["supplier_offer_id"]
    assert offer_ref.get("search_session_id") == session_id
    assert offer_ref.get("offer_token") == offer["offer_token"]
