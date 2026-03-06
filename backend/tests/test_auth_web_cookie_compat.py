from __future__ import annotations

import pytest

from app.config import AUTH_ACCESS_COOKIE_NAME, AUTH_REFRESH_COOKIE_NAME, WEB_AUTH_PLATFORM_HEADER, WEB_AUTH_PLATFORM_VALUE


WEB_HEADERS = {WEB_AUTH_PLATFORM_HEADER: WEB_AUTH_PLATFORM_VALUE}


@pytest.mark.anyio
async def test_web_login_sets_auth_cookies_and_cookie_transport(async_client):
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )

    assert response.status_code == 200, response.text
    assert response.json()["auth_transport"] == "cookie_compat"
    assert response.cookies.get(AUTH_ACCESS_COOKIE_NAME)
    assert response.cookies.get(AUTH_REFRESH_COOKIE_NAME)


@pytest.mark.anyio
async def test_web_cookie_session_bootstraps_without_authorization_header(async_client):
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert login_response.status_code == 200, login_response.text

    me_response = await async_client.get("/api/auth/me", headers=WEB_HEADERS)

    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["email"] == "admin@acenta.test"
    assert "password_hash" not in me_response.json()


@pytest.mark.anyio
async def test_web_refresh_uses_cookie_when_refresh_body_is_empty(async_client):
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert login_response.status_code == 200, login_response.text
    first_refresh_cookie = login_response.cookies.get(AUTH_REFRESH_COOKIE_NAME)

    refresh_response = await async_client.post(
        "/api/auth/refresh",
        json={},
        headers=WEB_HEADERS,
    )

    assert refresh_response.status_code == 200, refresh_response.text
    assert refresh_response.json()["auth_transport"] == "cookie_compat"
    assert refresh_response.cookies.get(AUTH_REFRESH_COOKIE_NAME)
    assert refresh_response.cookies.get(AUTH_REFRESH_COOKIE_NAME) != first_refresh_cookie


@pytest.mark.anyio
async def test_web_logout_clears_cookie_session_without_bearer_header(async_client):
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert login_response.status_code == 200, login_response.text

    logout_response = await async_client.post("/api/auth/logout", headers=WEB_HEADERS)

    assert logout_response.status_code == 200, logout_response.text

    me_response = await async_client.get("/api/auth/me", headers=WEB_HEADERS)
    assert me_response.status_code == 401