from __future__ import annotations

from app.auth import hash_password
from app.utils import now_utc


async def _get_demo_agency_and_tenant(test_db):
    agency = await test_db.agencies.find_one({"name": "Demo Agency"})
    tenant = await test_db.tenants.find_one({"_id": "tenant_default"})
    assert agency is not None
    assert tenant is not None
    return agency, tenant


async def test_create_user_auto_creates_membership(async_client, admin_headers, test_db):
    agency, tenant = await _get_demo_agency_and_tenant(test_db)

    response = await async_client.post(
        "/api/admin/all-users",
        headers=admin_headers,
        json={
            "email": "membership.create@test.local",
            "name": "Membership Create",
            "password": "Secret123!",
            "agency_id": str(agency["_id"]),
            "role": "agency_admin",
        },
    )
    assert response.status_code == 200, response.text
    created = response.json()

    membership = await test_db.memberships.find_one(
        {
            "user_id": created["id"],
            "tenant_id": str(tenant["_id"]),
            "status": "active",
        }
    )
    assert membership is not None
    assert membership["role"] == "agency_admin"

    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "membership.create@test.local",
            "password": "Secret123!",
        },
    )
    assert login_response.status_code == 200, login_response.text
    assert login_response.json().get("tenant_id") == str(tenant["_id"])


async def test_repair_endpoint_fixes_existing_broken_user(async_client, admin_headers, test_db):
    agency, tenant = await _get_demo_agency_and_tenant(test_db)
    now = now_utc()

    await test_db.users.insert_one(
        {
            "_id": "broken_membership_user",
            "organization_id": str(tenant["organization_id"]),
            "agency_id": agency["_id"],
            "email": "broken.membership@test.local",
            "name": "Broken Membership",
            "password_hash": hash_password("Secret123!"),
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    repair_response = await async_client.post(
        "/api/admin/all-users/repair-memberships",
        headers=admin_headers,
    )
    assert repair_response.status_code == 200, repair_response.text
    payload = repair_response.json()
    assert payload["repaired"] >= 1

    membership = await test_db.memberships.find_one(
        {
            "user_id": "broken_membership_user",
            "tenant_id": str(tenant["_id"]),
            "status": "active",
        }
    )
    assert membership is not None
    assert membership["role"] == "agency_agent"

    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "broken.membership@test.local",
            "password": "Secret123!",
        },
    )
    assert login_response.status_code == 200, login_response.text
    assert login_response.json().get("tenant_id") == str(tenant["_id"])
