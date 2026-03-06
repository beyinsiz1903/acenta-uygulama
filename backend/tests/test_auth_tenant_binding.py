from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.auth import hash_password


@pytest.mark.anyio
async def test_login_requires_tenant_context_when_same_email_exists_in_multiple_tenants(async_client, test_db):
    now = datetime.now(timezone.utc)
    shared_email = "shared-login@test.local"
    password_hash = hash_password("Password123!")

    await test_db.organizations.insert_many(
        [
            {"_id": "org_login_a", "name": "Org A", "slug": "org-login-a", "created_at": now, "updated_at": now},
            {"_id": "org_login_b", "name": "Org B", "slug": "org-login-b", "created_at": now, "updated_at": now},
        ]
    )
    await test_db.tenants.insert_many(
        [
            {"_id": "tenant_login_a", "organization_id": "org_login_a", "slug": "tenant-a", "name": "Tenant A", "created_at": now, "updated_at": now},
            {"_id": "tenant_login_b", "organization_id": "org_login_b", "slug": "tenant-b", "name": "Tenant B", "created_at": now, "updated_at": now},
        ]
    )
    await test_db.users.insert_many(
        [
            {"_id": "user_login_a", "organization_id": "org_login_a", "email": shared_email, "name": "User A", "password_hash": password_hash, "roles": ["agency_admin"], "is_active": True, "created_at": now, "updated_at": now},
            {"_id": "user_login_b", "organization_id": "org_login_b", "email": shared_email, "name": "User B", "password_hash": password_hash, "roles": ["agency_admin"], "is_active": True, "created_at": now, "updated_at": now},
        ]
    )
    await test_db.memberships.insert_many(
        [
            {"_id": "membership_login_a", "user_id": "user_login_a", "tenant_id": "tenant_login_a", "role": "agency_admin", "status": "active", "created_at": now, "updated_at": now},
            {"_id": "membership_login_b", "user_id": "user_login_b", "tenant_id": "tenant_login_b", "role": "agency_admin", "status": "active", "created_at": now, "updated_at": now},
        ]
    )

    ambiguous = await async_client.post(
        "/api/auth/login",
        json={"email": shared_email, "password": "Password123!"},
    )
    assert ambiguous.status_code == 409

    scoped = await async_client.post(
        "/api/auth/login",
        json={"email": shared_email, "password": "Password123!", "tenant_id": "tenant_login_a"},
    )
    assert scoped.status_code == 200, scoped.text
    body = scoped.json()
    assert body["tenant_id"] == "tenant_login_a"
    assert body["user"]["organization_id"] == "org_login_a"


@pytest.mark.anyio
async def test_login_without_membership_is_rejected_for_non_admin(async_client, test_db):
    now = datetime.now(timezone.utc)
    await test_db.organizations.insert_one({"_id": "org_nomem", "name": "No Membership Org", "slug": "org-nomem", "created_at": now, "updated_at": now})
    await test_db.tenants.insert_one({"_id": "tenant_nomem", "organization_id": "org_nomem", "slug": "tenant-nomem", "name": "Tenant NoMem", "created_at": now, "updated_at": now})
    await test_db.users.insert_one(
        {
            "_id": "user_nomem",
            "organization_id": "org_nomem",
            "email": "nomembership@test.local",
            "name": "No Membership",
            "password_hash": hash_password("Password123!"),
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    resp = await async_client.post(
        "/api/auth/login",
        json={"email": "nomembership@test.local", "password": "Password123!", "tenant_id": "tenant_nomem"},
    )
    assert resp.status_code == 403