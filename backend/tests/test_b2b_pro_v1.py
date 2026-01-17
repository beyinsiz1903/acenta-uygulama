from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app.auth import create_access_token
from app.db import get_db

# HTTP client comes from tests/conftest.py as `async_client` fixture


@pytest.fixture
async def admin_token(anyio_backend):  # type: ignore[override]
    db = await get_db()

    org_id = "org_b2b_pro_test"
    await db.organizations.insert_one({"_id": org_id, "name": "B2B PRO Test Org", "features": {"b2b_pro": True}})

    email = "admin_b2b_pro@test.local"
    user_doc = {
        "organization_id": org_id,
        "email": email,
        "name": "Admin B2B PRO",
        "roles": ["admin", "super_admin"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(subject=email, organization_id=org_id, roles=user_doc["roles"])
    return token


@pytest.mark.anyio
async def test_admin_agencies_feature_disabled_returns_404(async_client, test_db, anyio_backend):  # type: ignore[override]
    db = test_db
    org_id = "org_no_b2b_pro"
    await db.organizations.insert_one({"_id": org_id, "name": "No B2B PRO", "features": {"b2b_pro": False}})

    email = "admin_nopro@test.local"
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

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        resp = await client.get("/api/admin/agencies/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_admin_agencies_create_and_cycle_guards(async_client, test_db, anyio_backend, admin_token):  # type: ignore[override]
    db = test_db

    # Create base agency (no parent)
    resp = await async_client.post(
        "/api/admin/agencies/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Root Agency"},
    )
        assert resp.status_code == 200
        root = resp.json()
        root_id = root["id"]

        # Create child agency with valid parent
        resp2 = await client.post(
            "/api/admin/agencies/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Child Agency", "parent_agency_id": root_id},
        )
        assert resp2.status_code == 200
        child = resp2.json()
        child_id = child["id"]

        # Self-parent on update -> 422
        resp_self = await client.put(
            f"/api/admin/agencies/{child_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"parent_agency_id": child_id},
        )
        assert resp_self.status_code == 422
        assert resp_self.json()["detail"] == "SELF_PARENT_NOT_ALLOWED"

        # Create third agency C with parent B, then try to set A's parent to C to form A<-B<-C<-A
        resp_c = await client.post(
            "/api/admin/agencies/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Third Agency", "parent_agency_id": child_id},
        )
        assert resp_c.status_code == 200
        third = resp_c.json()
        third_id = third["id"]

        # Now attempt to set root's parent to third -> cycle
        resp_cycle = await client.put(
            f"/api/admin/agencies/{root_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"parent_agency_id": third_id},
        )
        assert resp_cycle.status_code == 422
        assert resp_cycle.json()["detail"] == "PARENT_CYCLE_DETECTED"


@pytest.mark.anyio
async def test_admin_agencies_org_isolation(anyio_backend):  # type: ignore[override]
    db = await get_db()

    # Org A with b2b_pro
    org_a = "org_a_b2b"
    await db.organizations.insert_one({"_id": org_a, "name": "Org A", "features": {"b2b_pro": True}})
    email_a = "admin_a@test.local"
    user_a = {
        "organization_id": org_a,
        "email": email_a,
        "name": "Admin A",
        "roles": ["admin"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_a)
    token_a = create_access_token(subject=email_a, organization_id=org_a, roles=user_a["roles"])

    # Org B with b2b_pro
    org_b = "org_b_b2b"
    await db.organizations.insert_one({"_id": org_b, "name": "Org B", "features": {"b2b_pro": True}})
    email_b = "admin_b@test.local"
    user_b = {
        "organization_id": org_b,
        "email": email_b,
        "name": "Admin B",
        "roles": ["admin"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_b)
    token_b = create_access_token(subject=email_b, organization_id=org_b, roles=user_b["roles"])

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        # Create agency in org A
        resp_a = await client.post(
            "/api/admin/agencies/",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "Org A Agency"},
        )
        assert resp_a.status_code == 200
        agency_a = resp_a.json()
        agency_a_id = agency_a["id"]

        # Org B listing should not see Org A agency
        resp_list_b = await client.get(
            "/api/admin/agencies/",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_list_b.status_code == 200
        items_b = resp_list_b.json()
        # list_agencies returns a plain list
        assert isinstance(items_b, list)
        assert all(item["id"] != agency_a_id for item in items_b)

        # Org B trying to update Org A agency_id should get 404
        resp_update_b = await client.put(
            f"/api/admin/agencies/{agency_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"name": "Hacked"},
        )
        assert resp_update_b.status_code == 404
