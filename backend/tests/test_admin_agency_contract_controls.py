from __future__ import annotations

from datetime import timedelta

import pytest

from app.auth import create_access_token, hash_password
from app.utils import now_utc


@pytest.mark.anyio
async def test_admin_agencies_return_contract_summary_and_enforce_user_limit(async_client, test_db, admin_headers):
    now = now_utc()
    admin_user = await test_db.users.find_one({"email": "admin@acenta.test"})
    assert admin_user, "Admin seed user should exist"

    org_id = admin_user["organization_id"]
    agency_id = "agency_contract_limit_case"

    await test_db.agencies.insert_one(
        {
            "_id": agency_id,
            "organization_id": org_id,
            "name": "Limit Test Agency",
            "status": "active",
            "contract_start_date": (now.date() - timedelta(days=335)).isoformat(),
            "contract_end_date": (now.date() + timedelta(days=20)).isoformat(),
            "payment_status": "paid",
            "package_type": "Yıllık Pro",
            "user_limit": 1,
            "created_at": now,
            "updated_at": now,
        }
    )

    await test_db.users.insert_one(
        {
            "_id": "limit_case_existing_user",
            "organization_id": org_id,
            "tenant_id": "tenant_default",
            "agency_id": agency_id,
            "email": "limit.existing@test.local",
            "name": "Limit Existing",
            "password_hash": hash_password("secret123"),
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    agencies_resp = await async_client.get("/api/admin/agencies/", headers=admin_headers)
    assert agencies_resp.status_code == 200, agencies_resp.text
    agencies = agencies_resp.json()

    target = next((item for item in agencies if item.get("id") == agency_id), None)
    assert target is not None, agencies
    assert target["contract_summary"]["contract_status"] == "expiring_soon"
    assert target["contract_summary"]["payment_status"] == "paid"
    assert target["active_user_count"] == 1
    assert target["remaining_user_slots"] == 0

    create_resp = await async_client.post(
        "/api/admin/all-users",
        headers=admin_headers,
        json={
            "name": "New Seat",
            "email": "limit.new@test.local",
            "password": "secret123",
            "agency_id": agency_id,
            "role": "agency_agent",
        },
    )
    assert create_resp.status_code == 409, create_resp.text
    payload = create_resp.json()
    assert payload["error"]["code"] == "agency_user_limit_reached"


@pytest.mark.anyio
async def test_agency_profile_reports_expired_contract(async_client, test_db):
    now = now_utc()
    org_id = "org_contract_gate"
    tenant_id = "tenant_contract_gate"
    agency_id = "agency_contract_gate"

    await test_db.organizations.insert_one(
        {
            "_id": org_id,
            "name": "Contract Gate Org",
            "slug": "contract-gate-org",
            "features": {"b2b_pro": True},
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.tenants.insert_one(
        {
            "_id": tenant_id,
            "organization_id": org_id,
            "name": "Contract Tenant",
            "slug": "contract-tenant",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.agencies.insert_one(
        {
            "_id": agency_id,
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "name": "Expired Agency",
            "status": "active",
            "contract_start_date": (now.date() - timedelta(days=400)).isoformat(),
            "contract_end_date": (now.date() - timedelta(days=1)).isoformat(),
            "payment_status": "overdue",
            "package_type": "Yıllık Kurumsal",
            "user_limit": 5,
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.users.insert_one(
        {
            "_id": "agency_contract_gate_user",
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "agency_id": agency_id,
            "email": "agency.contract.gate@test.local",
            "name": "Agency Contract Gate",
            "password_hash": hash_password("secret123"),
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.memberships.insert_one(
        {
            "_id": "agency_contract_gate_membership",
            "user_id": "agency_contract_gate_user",
            "tenant_id": tenant_id,
            "role": "agency_admin",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )

    token = create_access_token(
        subject="agency.contract.gate@test.local",
        organization_id=org_id,
        roles=["agency_admin"],
    )
    resp = await async_client.get(
        "/api/agency/profile",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    contract = data.get("contract") or {}
    assert contract.get("contract_status") == "expired"
    assert contract.get("access_blocked") is True
    assert contract.get("lock_message")
