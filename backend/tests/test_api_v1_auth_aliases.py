from __future__ import annotations

import pytest

from app.bootstrap.route_inventory import build_route_inventory
from app.config import AUTH_REFRESH_COOKIE_NAME, WEB_AUTH_PLATFORM_HEADER, WEB_AUTH_PLATFORM_VALUE
from server import app

WEB_HEADERS = {WEB_AUTH_PLATFORM_HEADER: WEB_AUTH_PLATFORM_VALUE}


def _inventory_map() -> dict[tuple[str, str], dict]:
    inventory = build_route_inventory(app)
    return {(entry["method"], entry["path"]): entry for entry in inventory}


def test_auth_v1_aliases_are_present_in_route_inventory() -> None:
    inventory = _inventory_map()

    expected = {
        ("POST", "/api/auth/login"): "legacy",
        ("GET", "/api/auth/me"): "legacy",
        ("POST", "/api/auth/refresh"): "legacy",
        ("POST", "/api/v1/auth/login"): "v1",
        ("GET", "/api/v1/auth/me"): "v1",
        ("POST", "/api/v1/auth/refresh"): "v1",
    }

    for key, version_status in expected.items():
        entry = inventory.get(key)
        assert entry is not None, f"missing auth route inventory entry for {key}"
        assert entry["legacy_or_v1"] == version_status
        assert entry["target_namespace"] == "/api/v1/auth"


@pytest.mark.anyio
async def test_legacy_auth_endpoints_publish_successor_headers(async_client) -> None:
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert login_response.status_code == 200, login_response.text
    assert login_response.headers.get("deprecation") == "true"
    assert "</api/v1/auth/login>; rel=\"successor-version\"" in login_response.headers.get("link", "")

    me_response = await async_client.get("/api/auth/me", headers=WEB_HEADERS)
    assert me_response.status_code == 200, me_response.text
    assert me_response.headers.get("deprecation") == "true"
    assert "</api/v1/auth/me>; rel=\"successor-version\"" in me_response.headers.get("link", "")

    refresh_response = await async_client.post("/api/auth/refresh", json={}, headers=WEB_HEADERS)
    assert refresh_response.status_code == 200, refresh_response.text
    assert refresh_response.headers.get("deprecation") == "true"
    assert "</api/v1/auth/refresh>; rel=\"successor-version\"" in refresh_response.headers.get("link", "")


@pytest.mark.anyio
async def test_v1_auth_cookie_bootstrap_flow(async_client) -> None:
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert login_response.status_code == 200, login_response.text
    assert login_response.json()["auth_transport"] == "cookie_compat"

    me_response = await async_client.get("/api/v1/auth/me", headers=WEB_HEADERS)
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["email"] == "admin@acenta.test"




@pytest.mark.anyio
async def test_v1_auth_refresh_rotates_cookie_transport(async_client) -> None:
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert login_response.status_code == 200, login_response.text
    first_refresh_cookie = login_response.cookies.get(AUTH_REFRESH_COOKIE_NAME)

    refresh_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={},
        headers=WEB_HEADERS,
    )
    assert refresh_response.status_code == 200, refresh_response.text
    assert refresh_response.json()["auth_transport"] == "cookie_compat"
    assert refresh_response.cookies.get(AUTH_REFRESH_COOKIE_NAME)
    assert refresh_response.cookies.get(AUTH_REFRESH_COOKIE_NAME) != first_refresh_cookie


@pytest.mark.anyio
async def test_v1_auth_bearer_flow_matches_legacy_transport(async_client) -> None:
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert login_response.status_code == 200, login_response.text
    payload = login_response.json()
    assert payload["auth_transport"] == "bearer"

    me_response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["email"] == "admin@acenta.test"
