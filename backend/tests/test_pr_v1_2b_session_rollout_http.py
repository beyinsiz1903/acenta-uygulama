from __future__ import annotations

import os
from pathlib import Path

import pytest
import requests



def _resolve_base_url() -> str:
    env_url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")

    frontend_env = Path("/app/frontend/.env")
    if frontend_env.exists():
        for line in frontend_env.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")

    return ""


BASE_URL = _resolve_base_url()
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
WEB_HEADERS = {"X-Client-Platform": "web", "Content-Type": "application/json"}


def _login(*, v1: bool = False, web: bool = False) -> requests.Response:
    path = "/api/v1/auth/login" if v1 else "/api/auth/login"
    headers = WEB_HEADERS if web else {"Content-Type": "application/json"}
    return requests.post(
        f"{BASE_URL}{path}",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers=headers,
        timeout=30,
    )


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestAuthSessionRolloutParity:
    def test_legacy_and_v1_sessions_lists_match(self):
        login_a = _login()
        assert login_a.status_code == 200, login_a.text
        token_a = login_a.json()["access_token"]

        login_b = _login(v1=True)
        assert login_b.status_code == 200, login_b.text

        legacy_resp = requests.get(f"{BASE_URL}/api/auth/sessions", headers=_bearer(token_a), timeout=30)
        v1_resp = requests.get(f"{BASE_URL}/api/v1/auth/sessions", headers=_bearer(token_a), timeout=30)

        assert legacy_resp.status_code == 200, legacy_resp.text
        assert legacy_resp.headers.get("deprecation") == "true"
        assert v1_resp.status_code == 200, v1_resp.text
        assert {item["id"] for item in legacy_resp.json()} == {item["id"] for item in v1_resp.json()}

    def test_v1_revoke_specific_session_preserves_current_session_behavior(self):
        keeper_login = _login(v1=True)
        target_login = _login(v1=True)
        assert keeper_login.status_code == 200, keeper_login.text
        assert target_login.status_code == 200, target_login.text

        keeper_token = keeper_login.json()["access_token"]
        target_token = target_login.json()["access_token"]
        target_session_id = target_login.json()["session_id"]

        revoke_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/sessions/{target_session_id}/revoke",
            headers=_bearer(keeper_token),
            timeout=30,
        )
        assert revoke_resp.status_code == 200, revoke_resp.text

        target_me = requests.get(f"{BASE_URL}/api/auth/me", headers=_bearer(target_token), timeout=30)
        keeper_me = requests.get(f"{BASE_URL}/api/auth/me", headers=_bearer(keeper_token), timeout=30)
        assert target_me.status_code == 401, target_me.text
        assert keeper_me.status_code == 200, keeper_me.text

    def test_v1_revoke_all_sessions_works_for_cookie_auth(self):
        session = requests.Session()
        login_resp = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers=WEB_HEADERS,
            timeout=30,
        )
        assert login_resp.status_code == 200, login_resp.text
        assert login_resp.json().get("auth_transport") == "cookie_compat"

        sessions_resp = session.get(f"{BASE_URL}/api/v1/auth/sessions", headers=WEB_HEADERS, timeout=30)
        assert sessions_resp.status_code == 200, sessions_resp.text
        assert sessions_resp.json(), sessions_resp.text

        revoke_all_resp = session.post(
            f"{BASE_URL}/api/v1/auth/revoke-all-sessions",
            json={},
            headers=WEB_HEADERS,
            timeout=30,
        )
        assert revoke_all_resp.status_code == 200, revoke_all_resp.text

        me_after = session.get(f"{BASE_URL}/api/v1/auth/me", headers=WEB_HEADERS, timeout=30)
        assert me_after.status_code == 401, me_after.text


class TestRouteInventoryArtifacts:
    def test_pr_v1_2b_inventory_and_summary_updated(self):
        import json

        inventory = json.loads(open("/app/backend/app/bootstrap/route_inventory.json").read())
        summary = json.loads(open("/app/backend/app/bootstrap/route_inventory_summary.json").read())

        inventory_set = {(entry["method"], entry["path"]) for entry in inventory}
        assert ("GET", "/api/v1/auth/sessions") in inventory_set
        assert ("POST", "/api/v1/auth/sessions/{session_id}/revoke") in inventory_set
        assert ("POST", "/api/v1/auth/revoke-all-sessions") in inventory_set
        assert summary["v1_count"] >= 23
        assert summary["domain_v1_progress"]["auth"]["migrated_v1_route_count"] >= 6


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])