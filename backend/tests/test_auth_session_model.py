from __future__ import annotations

import pytest




def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data


@pytest.mark.anyio
async def test_login_creates_listable_session(async_client):
    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = _unwrap(login_resp)["access_token"]

    sessions_resp = await async_client.get(
        "/api/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sessions_resp.status_code == 200
    sessions = _unwrap(sessions_resp)
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
    token = _unwrap(login_resp)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sessions_resp = await async_client.get("/api/auth/sessions", headers=headers)
    session_id = _unwrap(sessions_resp)[0]["id"]

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
    token = _unwrap(login_resp)["access_token"]

    sessions_resp = await async_client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sessions_resp.status_code == 200
    sessions = _unwrap(sessions_resp)
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
    token = _unwrap(login_resp)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    revoke_resp = await async_client.post("/api/v1/auth/revoke-all-sessions", headers=headers)
    assert revoke_resp.status_code == 200

    me_resp = await async_client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 401
