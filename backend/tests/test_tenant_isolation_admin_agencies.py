from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.auth import create_access_token


@pytest.mark.anyio
async def test_admin_agencies_isolated_by_tenant_header_and_membership(async_client, test_db):
    now = datetime.now(timezone.utc)
    org_id = "org_tenant_isolation"
    tenant_a = "tenant_iso_a"
    tenant_b = "tenant_iso_b"

    await test_db.organizations.insert_one({"_id": org_id, "name": "Tenant Isolation Org", "slug": "tenant-isolation-org", "features": {"b2b_pro": True}, "created_at": now, "updated_at": now})
    await test_db.tenants.insert_many(
        [
            {"_id": tenant_a, "organization_id": org_id, "slug": "tenant-iso-a", "name": "Tenant Iso A", "created_at": now, "updated_at": now},
            {"_id": tenant_b, "organization_id": org_id, "slug": "tenant-iso-b", "name": "Tenant Iso B", "created_at": now, "updated_at": now},
        ]
    )
    await test_db.users.insert_many(
        [
            {"_id": "admin_iso_a", "organization_id": org_id, "email": "admin-iso-a@test.local", "name": "Admin A", "roles": ["admin"], "is_active": True, "created_at": now, "updated_at": now},
            {"_id": "admin_iso_b", "organization_id": org_id, "email": "admin-iso-b@test.local", "name": "Admin B", "roles": ["admin"], "is_active": True, "created_at": now, "updated_at": now},
        ]
    )
    await test_db.memberships.insert_many(
        [
            {"_id": "membership_iso_a", "user_id": "admin_iso_a", "tenant_id": tenant_a, "role": "admin", "status": "active", "created_at": now, "updated_at": now},
            {"_id": "membership_iso_b", "user_id": "admin_iso_b", "tenant_id": tenant_b, "role": "admin", "status": "active", "created_at": now, "updated_at": now},
        ]
    )
    await test_db.agencies.insert_many(
        [
            {"_id": "agency_iso_a", "organization_id": org_id, "tenant_id": tenant_a, "name": "Agency A", "status": "active", "created_at": now, "updated_at": now},
            {"_id": "agency_iso_b", "organization_id": org_id, "tenant_id": tenant_b, "name": "Agency B", "status": "active", "created_at": now, "updated_at": now},
        ]
    )

    token_a = create_access_token(subject="admin-iso-a@test.local", organization_id=org_id, roles=["admin"])

    allowed_resp = await async_client.get(
        "/api/admin/agencies/",
        headers={"Authorization": f"Bearer {token_a}", "X-Tenant-Id": tenant_a},
    )
    assert allowed_resp.status_code == 200, allowed_resp.text
    names = [item["name"] for item in allowed_resp.json()]
    assert names == ["Agency A"]

    denied_resp = await async_client.get(
        "/api/admin/agencies/",
        headers={"Authorization": f"Bearer {token_a}", "X-Tenant-Id": tenant_b},
    )
    assert denied_resp.status_code == 403