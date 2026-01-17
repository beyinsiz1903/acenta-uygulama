from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.auth import create_access_token
from app.db import get_db
from app.utils import now_utc


@pytest.mark.anyio
async def test_admin_statements_feature_disabled(async_client, test_db, anyio_backend):  # type: ignore[override]
    db = test_db
    org_id = "org_no_b2b_pro_statements"
    await db.organizations.insert_one({"_id": org_id, "name": "No B2B PRO", "features": {"b2b_pro": False}})

    email = "admin_statements_nopro@test.local"
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
        "/api/admin/statements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_admin_statements_json_and_csv_happy_path(async_client, test_db, anyio_backend):  # type: ignore[override]
    db = test_db

    # Org with b2b_pro enabled
    org_id = "org_b2b_pro_statements"
    await db.organizations.insert_one({"_id": org_id, "name": "Org B2B PRO", "features": {"b2b_pro": True}})

    # Admin user
    email = "admin_statements@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Admin Statements",
        "roles": ["admin"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)
    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])

    # Seed one booking and one payment transaction
    now = now_utc()
    booking_doc = {
        "organization_id": org_id,
        "status": "CONFIRMED",
        "source": "public",
        "guest": {"full_name": "Test Guest"},
        "currency": "EUR",
        "booking_code": "STMT-001",
        "created_at": now,
    }
    ins_booking = await db.bookings.insert_one(booking_doc)

    tx_doc = {
        "organization_id": org_id,
        "booking_id": ins_booking.inserted_id,
        "amount": 11000,
        "currency": "EUR",
        "provider": "stripe",
        "occurred_at": now,
        "created_at": now,
    }
    await db.booking_payment_transactions.insert_one(tx_doc)

    # JSON request
    resp_json = await async_client.get(
        "/api/admin/statements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_json.status_code == 200
    data = resp_json.json()
    assert data["ok"] is True
    assert data["total"] >= 1
    assert data["returned_count"] >= 1
    assert data["skipped_missing_booking_count"] >= 0
    assert isinstance(data["items"], list)
    assert any(item["booking_code"] == "STMT-001" for item in data["items"])

    # CSV request - same filters, single query contract
    resp_csv = await async_client.get(
        "/api/admin/statements?format=csv",
        headers={"Authorization": f"Bearer {token}", "Accept": "text/csv"},
    )
    assert resp_csv.status_code == 200
    assert resp_csv.headers["content-type"].startswith("text/csv")
    assert "filename=\"statements.csv\"" in resp_csv.headers.get("content-disposition", "")

    body = resp_csv.text
    # Header + at least one data row
    lines = [line for line in body.split("\n") if line.strip()]
    assert len(lines) >= 2
    header = lines[0].split(",")
    assert "booking_code" in header


@pytest.mark.anyio
async def test_admin_statements_agency_admin_forces_own_agency(async_client, test_db, anyio_backend):  # type: ignore[override]
    db = test_db

    org_id = "org_b2b_pro_statements_agency"
    await db.organizations.insert_one({"_id": org_id, "name": "Org B2B PRO", "features": {"b2b_pro": True}})

    # Two agencies
    await db.agencies.insert_one({"_id": "agency_a", "organization_id": org_id, "name": "Agency A"})
    await db.agencies.insert_one({"_id": "agency_b", "organization_id": org_id, "name": "Agency B"})

    # Agency admin user linked to agency_a
    email = "agency_admin@test.local"
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
            "agency_id": "agency_a",
            "status": "CONFIRMED",
            "source": "public",
            "guest": {"full_name": "Guest A"},
            "currency": "EUR",
            "booking_code": "AG-A-001",
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
            "agency_id": "agency_b",
            "status": "CONFIRMED",
            "source": "public",
            "guest": {"full_name": "Guest B"},
            "currency": "EUR",
            "booking_code": "AG-B-001",
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

    # Agency admin tries to query with explicit agency_id=agency_b, but must be forced to agency_a
    resp = await async_client.get(
        "/api/admin/statements?agency_id=agency_b",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert all(item.get("agency_id") == "agency_a" for item in data["items"])
