from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.auth import create_access_token
from app.db import get_db
from app.utils import now_utc


@pytest.mark.anyio
async def test_admin_settlements_feature_disabled(async_client, test_db, anyio_backend):  # type: ignore[override]
    db = test_db

    org_id = "org_no_b2b_pro_settlements"
    await db.organizations.insert_one({"_id": org_id, "name": "No B2B PRO", "features": {"b2b_pro": False}})

    email = "admin_settlements_nopro@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Admin No PRO",
        "roles": ["admin"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    resp = await async_client.get(
        "/api/admin/settlements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_admin_settlements_admin_json_and_csv(async_client, test_db, anyio_backend):  # type: ignore[override]
    db = test_db

    # Org with b2b_pro enabled
    org_id = "org_b2b_pro_settlements"
    await db.organizations.insert_one(
        {
            "_id": org_id,
            "name": "Org B2B PRO",
            "features": {"b2b_pro": True},
        }
    )

    # Agency with commission/discount
    await db.agencies.insert_one(
        {
            "_id": "agency_s1",
            "organization_id": org_id,
            "name": "Settlement Agency",
            "commission_percent": 20.0,
            "discount_percent": 10.0,
        }
    )

    # Admin user
    email = "admin_settlements@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Admin Settlements",
        "roles": ["admin"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)
    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    # Seed booking + tx
    now = now_utc()
    booking_doc = {
        "organization_id": org_id,
        "status": "CONFIRMED",
        "source": "public",
        "booking_code": "SET-001",
        "agency_id": "agency_s1",
        "currency": "EUR",
        "created_at": now,
    }
    ins_booking = await db.bookings.insert_one(booking_doc)

    tx_amount = 10000  # 100 EUR gross
    await db.booking_payment_transactions.insert_one(
        {
            "organization_id": org_id,
            "booking_id": ins_booking.inserted_id,
            "agency_id": "agency_s1",
            "amount": tx_amount,
            "currency": "EUR",
            "provider": "stripe",
            "occurred_at": now,
            "created_at": now,
        }
    )

    # JSON request
    resp_json = await async_client.get(
        "/api/admin/settlements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_json.status_code == 200
    data = resp_json.json()
    assert data["ok"] is True
    assert data["total"] >= 1
    assert data["returned_count"] >= 1
    assert data["skipped_missing_booking_count"] >= 0
    items = data["items"]
    assert isinstance(items, list) and items

    row = next(i for i in items if i["booking_code"] == "SET-001")
    assert row["gross_cents"] == tx_amount

    # Settlement math: discount 10% => net_gross=9000; commission 20% => agency_cut=1800, platform_cut=7200
    assert row["agency_cut_cents"] == 1800
    assert row["platform_cut_cents"] == 7200

    # CSV request
    resp_csv = await async_client.get(
        "/api/admin/settlements?format=csv",
        headers={"Authorization": f"Bearer {token}", "Accept": "text/csv"},
    )
    assert resp_csv.status_code == 200
    assert resp_csv.headers["content-type"].startswith("text/csv")
    assert "filename=\"settlements.csv\"" in resp_csv.headers.get("content-disposition", "")

    body = resp_csv.text
    lines = [line for line in body.split("\n") if line.strip()]
    assert len(lines) >= 2
    header = lines[0].split(",")
    assert "booking_code" in header


@pytest.mark.anyio
async def test_admin_settlements_agency_admin_enforcement(async_client, test_db, anyio_backend):  # type: ignore[override]
    db = test_db

    org_id = "org_b2b_pro_settlements_agency"
    await db.organizations.insert_one(
        {
            "_id": org_id,
            "name": "Org B2B PRO",
            "features": {"b2b_pro": True},
        }
    )

    # Two agencies A and B
    await db.agencies.insert_one(
        {"_id": "agency_a", "organization_id": org_id, "name": "Agency A", "commission_percent": 10.0}
    )
    await db.agencies.insert_one(
        {"_id": "agency_b", "organization_id": org_id, "name": "Agency B", "commission_percent": 10.0}
    )

    # Agency admin for agency_a
    email = "agency_admin_settlements@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Agency Admin",
        "roles": ["agency_admin"],
        "agency_id": "agency_a",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)
    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    now = now_utc()

    # Booking + tx for agency_a
    booking_a = await db.bookings.insert_one(
        {
            "organization_id": org_id,
            "status": "CONFIRMED",
            "source": "public",
            "booking_code": "SET-A-001",
            "agency_id": "agency_a",
            "currency": "EUR",
            "created_at": now,
        }
    )
    await db.booking_payment_transactions.insert_one(
        {
            "organization_id": org_id,
            "booking_id": booking_a.inserted_id,
            "agency_id": "agency_a",
            "amount": 5000,
            "currency": "EUR",
            "provider": "stripe",
            "occurred_at": now,
            "created_at": now,
        }
    )

    # Booking + tx for agency_b
    booking_b = await db.bookings.insert_one(
        {
            "organization_id": org_id,
            "status": "CONFIRMED",
            "source": "public",
            "booking_code": "SET-B-001",
            "agency_id": "agency_b",
            "currency": "EUR",
            "created_at": now,
        }
    )
    await db.booking_payment_transactions.insert_one(
        {
            "organization_id": org_id,
            "booking_id": booking_b.inserted_id,
            "agency_id": "agency_b",
            "amount": 7000,
            "currency": "EUR",
            "provider": "stripe",
            "occurred_at": now,
            "created_at": now,
        }
    )

    # Agency admin queries with explicit agency_id=agency_b but must be forced to agency_a
    resp = await async_client.get(
        "/api/admin/settlements?agency_id=agency_b",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    items = data["items"]
    # All rows must belong to agency_a
    assert all(item.get("agency_id") == "agency_a" for item in items)


@pytest.mark.anyio
async def test_admin_settlements_pagination_validation(async_client, test_db, anyio_backend):  # type: ignore[override]
    db = test_db

    org_id = "org_b2b_pro_settlements_pagination"
    await db.organizations.insert_one(
        {
            "_id": org_id,
            "name": "Org B2B PRO",
            "features": {"b2b_pro": True},
        }
    )

    email = "admin_settlements_pagination@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Admin Settlements",
        "roles": ["admin"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)
    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    # Invalid page
    resp_page = await async_client.get(
        "/api/admin/settlements?page=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_page.status_code == 422

    # Invalid limit
    resp_limit = await async_client.get(
        "/api/admin/settlements?limit=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_limit.status_code == 422
