from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_login_creates_listable_session(async_client):
    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    sessions_resp = await async_client.get(
        "/api/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sessions_resp.status_code == 200
    sessions = sessions_resp.json()
    assert isinstance(sessions, list)
    assert sessions
    assert "id" in sessions[0]


@pytest.mark.anyio
async def test_revoke_specific_session_removes_access(async_client):
    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sessions_resp = await async_client.get("/api/auth/sessions", headers=headers)
    session_id = sessions_resp.json()[0]["id"]

    revoke_resp = await async_client.post(f"/api/auth/sessions/{session_id}/revoke", headers=headers)
    assert revoke_resp.status_code == 200

    me_resp = await async_client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 401


@pytest.mark.anyio
async def test_v1_sessions_alias_lists_active_sessions(async_client):
    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    sessions_resp = await async_client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sessions_resp.status_code == 200
    sessions = sessions_resp.json()
    assert isinstance(sessions, list)
    assert sessions
    assert "id" in sessions[0]


@pytest.mark.anyio
async def test_v1_revoke_all_sessions_alias_revokes_current_access(async_client):
    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    revoke_resp = await async_client.post("/api/v1/auth/revoke-all-sessions", headers=headers)
    assert revoke_resp.status_code == 200

    me_resp = await async_client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 401
