from __future__ import annotations

import json

import pytest
from bson import ObjectId

from app.auth import create_access_token
from app.utils import now_utc


@pytest.mark.anyio
async def test_admin_push_invoice_v1_happy_and_idempotent(async_client, test_db):
    db = test_db

    # Use seeded admin user from conftest
    admin = await db.users.find_one({"email": "admin@acenta.test"})
    assert admin is not None
    org_id = admin["organization_id"]

    booking_id = ObjectId()
    now = now_utc()

    await db.bookings.insert_one(
        {
            "_id": booking_id,
            "organization_id": org_id,
            "currency": "EUR",
            "amount_total_cents": 10000,
            "code": "BK-ADMIN-1",
            "status": "CONFIRMED",
            "created_at": now,
            "guest": {"full_name": "Admin Guest", "email": "admin-guest@example.com"},
        }
    )

    token = create_access_token(
        subject="admin@acenta.test",
        organization_id=org_id,
        roles=["super_admin"],
    )

    headers = {"Authorization": f"Bearer {token}"}

    # First push
    resp1 = await async_client.post(
        "/api/admin/finance/parasut/push-invoice-v1",
        headers=headers,
        json={"booking_id": str(booking_id)},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "success"
    assert data1["parasut_invoice_id"].startswith("mock_invoice_")

    # Second push -> skipped
    resp2 = await async_client.post(
        "/api/admin/finance/parasut/push-invoice-v1",
        headers=headers,
        json={"booking_id": str(booking_id)},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "skipped"
    assert data2["parasut_invoice_id"] == data1["parasut_invoice_id"]


@pytest.mark.anyio
async def test_admin_push_invoice_v1_404_for_other_org(async_client, test_db):
    db = test_db

    admin = await db.users.find_one({"email": "admin@acenta.test"})
    assert admin is not None
    org_id = admin["organization_id"]

    # Booking belongs to another org
    other_org_id = "org_other"
    booking_id = ObjectId()

    await db.bookings.insert_one(
        {
            "_id": booking_id,
            "organization_id": other_org_id,
            "currency": "EUR",
            "amount_total_cents": 5000,
            "code": "BK-OTHER-ORG",
            "status": "CONFIRMED",
            "created_at": now_utc(),
        }
    )

    token = create_access_token(
        subject="admin@acenta.test",
        organization_id=org_id,
        roles=["super_admin"],
    )

    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/admin/finance/parasut/push-invoice-v1?booking_id={booking_id}",
        headers=headers,
    )

    # Should not leak that booking exists in another org
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_admin_list_parasut_push_log_filtered_by_org_and_booking(async_client, test_db):
    db = test_db

    admin = await db.users.find_one({"email": "admin@acenta.test"})
    assert admin is not None
    org_id = admin["organization_id"]

    # Seed two log rows for same org, different bookings
    await db.parasut_push_log.insert_many(
        [
            {
                "organization_id": org_id,
                "booking_id": "bk1",
                "push_type": "invoice_v1",
                "dedupe_key": "invoice_v1:bk1",
                "status": "success",
                "parasut_contact_id": "cnt1",
                "parasut_invoice_id": "inv1",
                "attempt_count": 1,
                "last_error": None,
                "created_at": now_utc(),
                "updated_at": now_utc(),
            },
            {
                "organization_id": org_id,
                "booking_id": "bk2",
                "push_type": "invoice_v1",
                "dedupe_key": "invoice_v1:bk2",
                "status": "failed",
                "parasut_contact_id": None,
                "parasut_invoice_id": None,
                "attempt_count": 2,
                "last_error": "missing_amount",
                "created_at": now_utc(),
                "updated_at": now_utc(),
            },
            # Log row for another org should be invisible
            {
                "organization_id": "org_other",
                "booking_id": "bk3",
                "push_type": "invoice_v1",
                "dedupe_key": "invoice_v1:bk3",
                "status": "success",
                "parasut_contact_id": "cnt3",
                "parasut_invoice_id": "inv3",
                "attempt_count": 1,
                "last_error": None,
                "created_at": now_utc(),
                "updated_at": now_utc(),
            },
        ]
    )

    token = create_access_token(
        subject="admin@acenta.test",
        organization_id=org_id,
        roles=["super_admin"],
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Filter by booking_id=bk2
    resp = await async_client.get(
        "/api/admin/finance/parasut/pushes?booking_id=bk2", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    items = data["items"]

    # Only bk2 row should be visible
    assert len(items) == 1
    assert items[0]["booking_id"] == "bk2"
    assert items[0]["status"] == "failed"
    assert items[0]["last_error"] == "missing_amount"
