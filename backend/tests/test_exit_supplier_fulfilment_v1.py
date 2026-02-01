from __future__ import annotations

from typing import Any

import jwt
import pytest
from bson import ObjectId
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.exit_supplier_fulfilment_v1
@pytest.mark.anyio
async def test_supplier_fulfilment_happy_path(test_db: Any, async_client: AsyncClient) -> None:
    """draft b2b_marketplace booking -> confirm -> CONFIRMED + audit event.

    - Uses marketplace listing with resolved supplier_mapping
    - Buyer creates draft booking via POST /api/b2b/bookings (source=marketplace)
    - Confirm endpoint calls mock supplier and transitions to CONFIRMED
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Org + tenants
    org = await test_db.organizations.insert_one(
        {"name": "SUP-FLOW Org", "slug": "sup_flow_org", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    seller_tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "seller-supflow",
            "organization_id": org_id,
            "brand_name": "Seller SupFlow",
            "primary_domain": "seller-supflow.example.com",
            "subdomain": "seller-supflow",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    seller_tenant_id = str(seller_tenant.inserted_id)

    buyer_tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "buyer-supflow",
            "organization_id": org_id,
            "brand_name": "Buyer SupFlow",
            "primary_domain": "buyer-supflow.example.com",
            "subdomain": "buyer-supflow",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    buyer_tenant_id = str(buyer_tenant.inserted_id)

    # Users
    seller_email = "seller_supflow@example.com"
    buyer_email = "buyer_supflow@example.com"

    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": seller_email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": buyer_email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    seller_token = jwt.encode({"sub": seller_email, "org": org_id}, _jwt_secret(), algorithm="HS256")
    buyer_token = jwt.encode({"sub": buyer_email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    seller_headers = {"Authorization": f"Bearer {seller_token}", "X-Tenant-Key": "seller-supflow"}

    # 1) Seller creates listing with supplier metadata
    payload = {
        "title": "Supplier Fulfilment Listing",
        "description": "Supplier fulfilment test product",
        "category": "hotel",
        "currency": "TRY",
        "base_price": "150.00",
        "tags": ["supplier", "hotel"],
        "supplier": {
            "name": "mock_supplier_v1",
            "external_ref": "MS-FLOW-1",
        },
    }

    resp_create = await client.post("/api/marketplace/listings", json=payload, headers=seller_headers)
    assert resp_create.status_code == status.HTTP_201_CREATED, resp_create.text
    listing = resp_create.json()
    listing_id = listing["id"]

    # 2) Seller publishes listing
    resp_publish = await client.post(f"/api/marketplace/listings/{listing_id}/publish", headers=seller_headers)
    assert resp_publish.status_code == status.HTTP_200_OK, resp_publish.text

    # 3) Admin grants access seller->buyer
    admin_headers = {"Authorization": f"Bearer {seller_token}"}
    grant_payload = {"seller_tenant_id": seller_tenant_id, "buyer_tenant_id": buyer_tenant_id}
    resp_grant = await client.post("/api/marketplace/access/grant", json=grant_payload, headers=admin_headers)
    assert resp_grant.status_code == status.HTTP_201_CREATED, resp_grant.text

    # 4) Resolve supplier mapping explicitly (so booking sees resolved mapping)
    resp_resolve = await client.post(
        f"/api/marketplace/listings/{listing_id}/resolve-supplier",
        headers=seller_headers,
    )
    assert resp_resolve.status_code == status.HTTP_200_OK, resp_resolve.text

    # 5) Buyer creates draft booking from marketplace
    buyer_headers = {
        "Authorization": f"Bearer {buyer_token}",
        "X-Tenant-Key": "buyer-supflow",
        "Idempotency-Key": "supflow-draft-1",
    }

    booking_payload = {
        "source": "marketplace",
        "listing_id": listing_id,
        "customer": {
            "full_name": "Supplier Flow Customer",
            "email": "supflow@example.com",
            "phone": "+900000000000",
        },
        "travellers": [
            {"first_name": "Test", "last_name": "User"},
        ],
    }

    resp_booking = await client.post("/api/b2b/bookings", json=booking_payload, headers=buyer_headers)
    assert resp_booking.status_code == status.HTTP_201_CREATED, resp_booking.text
    booking_data = resp_booking.json()
    booking_id = booking_data["booking_id"]
    assert booking_data["state"] == "draft"

    # 6) Confirm booking via new endpoint
    confirm_headers = {
        "Authorization": f"Bearer {buyer_token}",
        "X-Tenant-Key": "buyer-supflow",
    }

    resp_confirm = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=confirm_headers)
    assert resp_confirm.status_code == status.HTTP_200_OK, resp_confirm.text
    body = resp_confirm.json()
    assert body["booking_id"] == booking_id
    assert body["state"] == "confirmed"

    # 7) Check booking status projection + lifecycle event
    stored = await test_db.bookings.find_one({"_id": ObjectId(booking_id)})
    assert stored is not None
    assert stored.get("status") == "CONFIRMED"

    events = await test_db.booking_events.find({"organization_id": org_id, "booking_id": booking_id}).to_list(10)
    assert any(ev.get("event") == "BOOKING_CONFIRMED" for ev in events)

    # 8) Audit log for B2B_BOOKING_CONFIRMED with supplier meta
    audit_cursor = test_db.audit_logs.find(
        {
            "organization_id": org_id,
            "action": "B2B_BOOKING_CONFIRMED",
            "target.id": booking_id,
        }
    )
    audit_docs = await audit_cursor.to_list(length=5)
    assert len(audit_docs) == 1
    meta = audit_docs[0].get("meta") or {}
    assert meta.get("source") == "supplier_fulfilment"
    assert meta.get("supplier") == "mock_supplier_v1"
    assert meta.get("supplier_offer_id") is not None
    assert meta.get("attempt_id") is not None


@pytest.mark.exit_supplier_fulfilment_v1
@pytest.mark.anyio
async def test_supplier_fulfilment_missing_mapping(test_db: Any, async_client: AsyncClient) -> None:
    """Confirm should fail fast when supplier mapping is missing on draft booking."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "SUP-FLOW Org2", "slug": "sup_flow_org2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "tenant-supflow-2",
            "organization_id": org_id,
            "brand_name": "Tenant SupFlow 2",
            "primary_domain": "supflow2.example.com",
            "subdomain": "supflow2",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    email = "supflow2@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    # Insert a draft booking manually with missing supplier mapping
    booking_doc = {
        "organization_id": org_id,
        "state": "draft",
        "status": "PENDING",
        "source": "b2b_marketplace",
        "currency": "TRY",
        "amount": 100.0,
        "offer_ref": {
            "source": "marketplace",
            "listing_id": "dummy",
            "seller_tenant_id": tenant_id,
            "buyer_tenant_id": tenant_id,
            # supplier and supplier_offer_id intentionally missing
        },
        "created_at": now,
        "updated_at": now,
    }
    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "tenant-supflow-2",
    }

    resp_confirm = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp_confirm.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err = resp_confirm.json().get("error", {})
    assert err.get("code") == "INVALID_SUPPLIER_MAPPING"
    # reason should be one of the allowed values; we don't assert exact here to keep v1 flexible
    details = err.get("details") or {}
    assert details.get("reason") in {"missing_supplier", "missing_supplier_offer_id", "unsupported_supplier"}


@pytest.mark.exit_supplier_fulfilment_v1
@pytest.mark.anyio
async def test_supplier_fulfilment_tenant_mismatch(test_db: Any, async_client: AsyncClient) -> None:
    """Confirm should fail-fast with BOOKING_NOT_CONFIRMABLE when buyer tenant mismatch."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "SUP-FLOW Org3", "slug": "sup_flow_org3", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    buyer_tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "buyer-supflow-3",
            "organization_id": org_id,
            "brand_name": "Buyer SupFlow 3",
            "primary_domain": "buyer-supflow-3.example.com",
            "subdomain": "buyer-supflow-3",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    buyer_tenant_id = str(buyer_tenant.inserted_id)

    other_tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "other-supflow-3",
            "organization_id": org_id,
            "brand_name": "Other SupFlow 3",
            "primary_domain": "other-supflow-3.example.com",
            "subdomain": "other-supflow-3",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    email = "supflow3@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    # Booking with buyer_tenant_id=buyer_tenant_id in offer_ref, but we'll call confirm with different X-Tenant-Key
    booking_doc = {
        "organization_id": org_id,
        "state": "draft",
        "status": "PENDING",
        "source": "b2b_marketplace",
        "currency": "TRY",
        "amount": 100.0,
        "offer_ref": {
            "source": "marketplace",
            "listing_id": "dummy",
            "seller_tenant_id": buyer_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
            "supplier": "mock_supplier_v1",
            "supplier_offer_id": "MOCK-MS-FLOW-3",
        },
        "created_at": now,
        "updated_at": now,
    }
    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "other-supflow-3",  # mismatch
    }

    resp_confirm = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp_confirm.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err = resp_confirm.json().get("error", {})
    assert err.get("code") == "BOOKING_NOT_CONFIRMABLE"
    details = err.get("details") or {}
    assert details.get("reason") == "invalid_state"


@pytest.mark.exit_supplier_fulfilment_v1
@pytest.mark.anyio
async def test_supplier_fulfilment_idempotent_confirm(test_db: Any, async_client: AsyncClient) -> None:
    """Second confirm call on already confirmed booking should be idempotent (no-op)."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "SUP-FLOW Org4", "slug": "sup_flow_org4", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "tenant-supflow-4",
            "organization_id": org_id,
            "brand_name": "Tenant SupFlow 4",
            "primary_domain": "tenant-supflow-4.example.com",
            "subdomain": "tenant-supflow-4",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    email = "supflow4@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    # Booking already confirmed at projection level
    booking_doc = {
        "organization_id": org_id,
        "state": "draft",  # legacy field, kept as draft
        "status": "CONFIRMED",
        "source": "b2b_marketplace",
        "currency": "TRY",
        "amount": 100.0,
        "offer_ref": {
            "source": "marketplace",
            "listing_id": "dummy",
            "seller_tenant_id": tenant_id,
            "buyer_tenant_id": tenant_id,
            "supplier": "mock_supplier_v1",
            "supplier_offer_id": "MOCK-MS-FLOW-4",
        },
        "created_at": now,
        "updated_at": now,
    }
    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": "tenant-supflow-4",
    }

    # First confirm (should be treated as idempotent no-op since status is already CONFIRMED)
    resp_confirm_1 = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp_confirm_1.status_code == status.HTTP_200_OK
    data1 = resp_confirm_1.json()
    assert data1["state"] == "confirmed"

    # Second confirm
    resp_confirm_2 = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp_confirm_2.status_code == status.HTTP_200_OK
    data2 = resp_confirm_2.json()
    assert data2["state"] == "confirmed"

    # Only one BOOKING_CONFIRMED lifecycle event should exist
    events = await test_db.booking_events.find(
        {"organization_id": org_id, "booking_id": booking_id, "event": "BOOKING_CONFIRMED"}
    ).to_list(10)
    assert len(events) == 1

    # Only one B2B_BOOKING_CONFIRMED audit log should exist
    audit_docs = await test_db.audit_logs.find(
        {
            "organization_id": org_id,
            "action": "B2B_BOOKING_CONFIRMED",
            "target.id": booking_id,
        }
    ).to_list(10)
    assert len(audit_docs) == 1
