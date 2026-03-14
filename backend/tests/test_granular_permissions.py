"""
Granular User Permissions Feature Tests

Tests the screen-level permissions feature for agency users:
- GET /api/admin/permissions/screens - list available screens
- GET /api/admin/all-users/{user_id}/permissions - get user's allowed_screens
- PUT /api/admin/all-users/{user_id}/permissions - update allowed_screens
- Login response includes allowed_screens field
- GET /api/auth/me includes allowed_screens field
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.auth import create_access_token
from app.db import get_db

EXPECTED_SCREENS = [
    "dashboard", "rezervasyonlar", "oteller", "musaitlik",
    "sheet_baglantilari", "mutabakat", "raporlar", "turlar",
    "musteriler", "ayarlar",
]


async def _seed_admin_and_agent(db):
    """Seed a super_admin and an agency_agent user for permission tests."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    admin_email = "perm_admin@test.local"
    agent_email = "perm_agent@test.local"
    org_id = "org_perm_test"

    await db.organizations.update_one(
        {"_id": org_id},
        {"$set": {"_id": org_id, "name": "Perm Test Org", "status": "active", "created_at": now}},
        upsert=True,
    )

    admin_doc = {
        "_id": "user_perm_admin",
        "email": admin_email,
        "name": "Perm Admin",
        "organization_id": org_id,
        "roles": ["super_admin"],
        "status": "active",
        "allowed_screens": [],
        "created_at": now,
    }
    await db.users.update_one({"_id": admin_doc["_id"]}, {"$set": admin_doc}, upsert=True)

    agent_doc = {
        "_id": "user_perm_agent",
        "email": agent_email,
        "name": "Perm Agent",
        "organization_id": org_id,
        "roles": ["agency_agent"],
        "status": "active",
        "allowed_screens": [],
        "created_at": now,
    }
    await db.users.update_one({"_id": agent_doc["_id"]}, {"$set": agent_doc}, upsert=True)

    admin_token = create_access_token(
        subject=admin_email, organization_id=org_id, roles=["super_admin"],
    )
    return {
        "admin_token": admin_token,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "agent_id": agent_doc["_id"],
        "org_id": org_id,
    }


# ---------------------------------------------------------------------------
# Screens endpoint
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_list_screens_unauthenticated(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/admin/permissions/screens")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_list_screens_authenticated(async_client: AsyncClient, test_db) -> None:
    db = await get_db()
    ctx = await _seed_admin_and_agent(db)

    resp = await async_client.get("/api/admin/permissions/screens", headers=ctx["admin_headers"])
    assert resp.status_code == 200, f"Failed: {resp.text[:200]}"
    screens = resp.json()

    assert isinstance(screens, list)
    assert len(screens) >= 10
    screen_keys = [s["key"] for s in screens]
    for expected in EXPECTED_SCREENS:
        assert expected in screen_keys, f"Missing screen: {expected}"
    for s in screens:
        assert "key" in s
        assert "label" in s
        assert "description" in s


# ---------------------------------------------------------------------------
# Get / Update user permissions
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_user_permissions(async_client: AsyncClient, test_db) -> None:
    db = await get_db()
    ctx = await _seed_admin_and_agent(db)

    resp = await async_client.get(
        f"/api/admin/all-users/{ctx['agent_id']}/permissions",
        headers=ctx["admin_headers"],
    )
    assert resp.status_code == 200, f"Failed: {resp.text[:200]}"
    data = resp.json()
    assert data["user_id"] == ctx["agent_id"]
    assert isinstance(data["allowed_screens"], list)


@pytest.mark.anyio
async def test_get_permissions_invalid_user(async_client: AsyncClient, test_db) -> None:
    db = await get_db()
    ctx = await _seed_admin_and_agent(db)

    resp = await async_client.get(
        "/api/admin/all-users/000000000000000000000000/permissions",
        headers=ctx["admin_headers"],
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_permissions_unauthenticated(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/admin/all-users/some_id/permissions")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_update_permissions_valid(async_client: AsyncClient, test_db) -> None:
    db = await get_db()
    ctx = await _seed_admin_and_agent(db)

    new_screens = ["dashboard", "rezervasyonlar", "oteller"]
    resp = await async_client.put(
        f"/api/admin/all-users/{ctx['agent_id']}/permissions",
        headers=ctx["admin_headers"],
        json={"allowed_screens": new_screens},
    )
    assert resp.status_code == 200, f"Failed: {resp.text[:200]}"
    assert set(resp.json()["allowed_screens"]) == set(new_screens)

    # Persistence check
    get_resp = await async_client.get(
        f"/api/admin/all-users/{ctx['agent_id']}/permissions",
        headers=ctx["admin_headers"],
    )
    assert get_resp.status_code == 200
    assert set(get_resp.json()["allowed_screens"]) == set(new_screens)


@pytest.mark.anyio
async def test_update_permissions_all_screens(async_client: AsyncClient, test_db) -> None:
    db = await get_db()
    ctx = await _seed_admin_and_agent(db)

    resp = await async_client.put(
        f"/api/admin/all-users/{ctx['agent_id']}/permissions",
        headers=ctx["admin_headers"],
        json={"allowed_screens": EXPECTED_SCREENS},
    )
    assert resp.status_code == 200
    assert set(resp.json()["allowed_screens"]) == set(EXPECTED_SCREENS)


@pytest.mark.anyio
async def test_update_permissions_empty(async_client: AsyncClient, test_db) -> None:
    db = await get_db()
    ctx = await _seed_admin_and_agent(db)

    resp = await async_client.put(
        f"/api/admin/all-users/{ctx['agent_id']}/permissions",
        headers=ctx["admin_headers"],
        json={"allowed_screens": []},
    )
    assert resp.status_code == 200
    assert resp.json()["allowed_screens"] == []


@pytest.mark.anyio
async def test_update_permissions_filters_invalid(async_client: AsyncClient, test_db) -> None:
    db = await get_db()
    ctx = await _seed_admin_and_agent(db)

    resp = await async_client.put(
        f"/api/admin/all-users/{ctx['agent_id']}/permissions",
        headers=ctx["admin_headers"],
        json={"allowed_screens": ["dashboard", "invalid_xyz", "rezervasyonlar", "fake"]},
    )
    assert resp.status_code == 200
    assert set(resp.json()["allowed_screens"]) == {"dashboard", "rezervasyonlar"}


@pytest.mark.anyio
async def test_update_permissions_invalid_user(async_client: AsyncClient, test_db) -> None:
    db = await get_db()
    ctx = await _seed_admin_and_agent(db)

    resp = await async_client.put(
        "/api/admin/all-users/000000000000000000000000/permissions",
        headers=ctx["admin_headers"],
        json={"allowed_screens": ["dashboard"]},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_permissions_unauthenticated(async_client: AsyncClient) -> None:
    resp = await async_client.put(
        "/api/admin/all-users/some_id/permissions",
        json={"allowed_screens": ["dashboard"]},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Login & /auth/me include allowed_screens
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_auth_me_includes_allowed_screens(async_client: AsyncClient, test_db) -> None:
    db = await get_db()
    ctx = await _seed_admin_and_agent(db)

    resp = await async_client.get("/api/auth/me", headers=ctx["admin_headers"])
    assert resp.status_code == 200, f"Failed: {resp.text[:200]}"
    data = resp.json()
    assert "allowed_screens" in data
    assert isinstance(data["allowed_screens"], list)


# ---------------------------------------------------------------------------
# E2E flow
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_full_permissions_workflow(async_client: AsyncClient, test_db) -> None:
    db = await get_db()
    ctx = await _seed_admin_and_agent(db)
    h = ctx["admin_headers"]
    uid = ctx["agent_id"]

    # 1 - List screens
    screens_resp = await async_client.get("/api/admin/permissions/screens", headers=h)
    assert screens_resp.status_code == 200
    assert len(screens_resp.json()) >= 10

    # 2 - Get initial permissions
    get_resp = await async_client.get(f"/api/admin/all-users/{uid}/permissions", headers=h)
    assert get_resp.status_code == 200

    # 3 - Restrict
    restricted = ["dashboard", "rezervasyonlar", "oteller"]
    upd = await async_client.put(
        f"/api/admin/all-users/{uid}/permissions",
        headers=h, json={"allowed_screens": restricted},
    )
    assert upd.status_code == 200
    assert set(upd.json()["allowed_screens"]) == set(restricted)

    # 4 - Clear
    clear = await async_client.put(
        f"/api/admin/all-users/{uid}/permissions",
        headers=h, json={"allowed_screens": []},
    )
    assert clear.status_code == 200
    assert clear.json()["allowed_screens"] == []
