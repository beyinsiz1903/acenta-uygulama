from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.auth import create_access_token


def _auth_headers(token: str, tenant_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id
    return headers


@pytest.mark.anyio
async def test_mobile_bff_requires_auth(async_client):
    for path in (
        "/api/v1/mobile/auth/me",
        "/api/v1/mobile/dashboard/summary",
        "/api/v1/mobile/bookings",
        "/api/v1/mobile/reports/summary",
    ):
        response = await async_client.get(path)
        assert response.status_code == 401, (path, response.text)


@pytest.mark.anyio
async def test_mobile_auth_me_returns_sanitized_user(async_client, admin_token):
    response = await async_client.get(
        "/api/v1/mobile/auth/me",
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["email"] == "admin@acenta.test"
    assert "password_hash" not in payload
    assert "_id" not in payload
    assert "tenant_id" in payload


@pytest.mark.anyio
async def test_mobile_bookings_are_tenant_isolated(async_client, test_db):
    now = datetime.now(timezone.utc)
    org_id = "org_mobile_iso"
    tenant_a = "tenant_mobile_a"
    tenant_b = "tenant_mobile_b"

    await test_db.organizations.insert_one({"_id": org_id, "name": "Mobile Org", "slug": "mobile-org", "created_at": now, "updated_at": now})
    await test_db.tenants.insert_many(
        [
            {"_id": tenant_a, "organization_id": org_id, "slug": "mobile-a", "name": "Mobile A", "created_at": now, "updated_at": now},
            {"_id": tenant_b, "organization_id": org_id, "slug": "mobile-b", "name": "Mobile B", "created_at": now, "updated_at": now},
        ]
    )
    await test_db.users.insert_one(
        {
            "_id": "mobile_user_a",
            "organization_id": org_id,
            "email": "mobile-a@test.local",
            "name": "Mobile User A",
            "roles": ["agency_admin"],
            "agency_id": "agency_a",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.memberships.insert_one(
        {
            "_id": "mobile_membership_a",
            "user_id": "mobile_user_a",
            "tenant_id": tenant_a,
            "role": "agency_admin",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )

    booking_a_id = ObjectId()
    booking_b_id = ObjectId()
    await test_db.bookings.insert_many(
        [
            {
                "_id": booking_a_id,
                "organization_id": org_id,
                "tenant_id": tenant_a,
                "agency_id": "agency_a",
                "guest_name": "Alice",
                "hotel_name": "Hotel A",
                "state": "draft",
                "amount": 1200,
                "currency": "TRY",
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": booking_b_id,
                "organization_id": org_id,
                "tenant_id": tenant_b,
                "agency_id": "agency_b",
                "guest_name": "Bob",
                "hotel_name": "Hotel B",
                "state": "draft",
                "amount": 2200,
                "currency": "TRY",
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

    token = create_access_token(subject="mobile-a@test.local", organization_id=org_id, roles=["agency_admin"])
    headers = _auth_headers(token, tenant_a)

    list_response = await async_client.get("/api/v1/mobile/bookings", headers=headers)
    assert list_response.status_code == 200, list_response.text
    body = list_response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["hotel_name"] == "Hotel A"
    assert "_id" not in str(body)

    detail_allowed = await async_client.get(f"/api/v1/mobile/bookings/{booking_a_id}", headers=headers)
    assert detail_allowed.status_code == 200, detail_allowed.text
    assert detail_allowed.json()["hotel_name"] == "Hotel A"

    detail_denied = await async_client.get(f"/api/v1/mobile/bookings/{booking_b_id}", headers=headers)
    assert detail_denied.status_code == 404, detail_denied.text


@pytest.mark.anyio
async def test_mobile_booking_create_sets_tenant_and_returns_mobile_dto(async_client, test_db):
    now = datetime.now(timezone.utc)
    org_id = "org_mobile_create"
    tenant_id = "tenant_mobile_create"

    await test_db.organizations.insert_one({"_id": org_id, "name": "Create Org", "slug": "create-org", "created_at": now, "updated_at": now})
    await test_db.tenants.insert_one({"_id": tenant_id, "organization_id": org_id, "slug": "create-tenant", "name": "Create Tenant", "created_at": now, "updated_at": now})
    await test_db.users.insert_one(
        {
            "_id": "mobile_creator",
            "organization_id": org_id,
            "email": "mobile-create@test.local",
            "name": "Mobile Creator",
            "roles": ["agency_admin"],
            "agency_id": "agency_create",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.memberships.insert_one(
        {
            "_id": "mobile_creator_membership",
            "user_id": "mobile_creator",
            "tenant_id": tenant_id,
            "role": "agency_admin",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )

    token = create_access_token(subject="mobile-create@test.local", organization_id=org_id, roles=["agency_admin"])
    response = await async_client.post(
        "/api/v1/mobile/bookings",
        headers=_auth_headers(token, tenant_id),
        json={
            "amount": 3499.5,
            "currency": "TRY",
            "customer_name": "Jane Doe",
            "hotel_name": "Mobile Hotel",
            "booking_ref": "MB-1001",
            "check_in": "2026-03-10",
            "check_out": "2026-03-12",
            "notes": "Late arrival",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["customer_name"] == "Jane Doe"
    assert payload["hotel_name"] == "Mobile Hotel"
    assert payload["status"] == "draft"
    assert "_id" not in payload

    saved = await test_db.bookings.find_one({"booking_ref": "MB-1001"})
    assert saved is not None
    assert saved["tenant_id"] == tenant_id
    assert saved["agency_id"] == "agency_create"
    assert saved["source"] == "mobile"


@pytest.mark.anyio
async def test_mobile_dashboard_and_reports_summary_contracts(async_client, test_db):
    now = datetime.now(timezone.utc)
    org_id = "org_mobile_summary"
    tenant_id = "tenant_mobile_summary"

    await test_db.organizations.insert_one({"_id": org_id, "name": "Summary Org", "slug": "summary-org", "created_at": now, "updated_at": now})
    await test_db.tenants.insert_one({"_id": tenant_id, "organization_id": org_id, "slug": "summary-tenant", "name": "Summary Tenant", "created_at": now, "updated_at": now})
    await test_db.users.insert_one(
        {
            "_id": "mobile_summary_user",
            "organization_id": org_id,
            "email": "mobile-summary@test.local",
            "name": "Mobile Summary",
            "roles": ["agency_admin"],
            "agency_id": "agency_summary",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.memberships.insert_one(
        {
            "_id": "mobile_summary_membership",
            "user_id": "mobile_summary_user",
            "tenant_id": tenant_id,
            "role": "agency_admin",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.bookings.insert_many(
        [
            {
                "_id": ObjectId(),
                "organization_id": org_id,
                "tenant_id": tenant_id,
                "agency_id": "agency_summary",
                "guest_name": "Guest 1",
                "hotel_name": "Hotel 1",
                "state": "booked",
                "amount": 1500,
                "currency": "TRY",
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "organization_id": org_id,
                "tenant_id": tenant_id,
                "agency_id": "agency_summary",
                "guest_name": "Guest 2",
                "hotel_name": "Hotel 2",
                "state": "draft",
                "amount": 800,
                "currency": "TRY",
                "created_at": now - timedelta(days=1),
                "updated_at": now - timedelta(days=1),
            },
        ]
    )

    token = create_access_token(subject="mobile-summary@test.local", organization_id=org_id, roles=["agency_admin"])
    headers = _auth_headers(token, tenant_id)

    dashboard_response = await async_client.get("/api/v1/mobile/dashboard/summary", headers=headers)
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard_payload = dashboard_response.json()
    assert dashboard_payload["bookings_month"] == 2
    assert dashboard_payload["revenue_month"] == pytest.approx(2300.0)
    assert dashboard_payload["currency"] == "TRY"

    reports_response = await async_client.get("/api/v1/mobile/reports/summary", headers=headers)
    assert reports_response.status_code == 200, reports_response.text
    reports_payload = reports_response.json()
    assert reports_payload["total_bookings"] == 2
    assert reports_payload["total_revenue"] == pytest.approx(2300.0)
    assert {item["status"] for item in reports_payload["status_breakdown"]} == {"booked", "draft"}
    assert "_id" not in str(reports_payload)
