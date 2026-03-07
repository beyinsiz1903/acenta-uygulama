from __future__ import annotations

import json
import os
import uuid
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


def _login(*, web: bool = False) -> requests.Response:
    headers = WEB_HEADERS if web else {"Content-Type": "application/json"}
    return requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers=headers,
        timeout=30,
    )


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestSettingsRolloutParity:
    def test_legacy_and_v1_settings_list_match(self):
        login_resp = _login()
        assert login_resp.status_code == 200, login_resp.text
        token = login_resp.json()["access_token"]

        legacy_resp = requests.get(f"{BASE_URL}/api/settings/users", headers=_bearer(token), timeout=30)
        v1_resp = requests.get(f"{BASE_URL}/api/v1/settings/users", headers=_bearer(token), timeout=30)

        assert legacy_resp.status_code == 200, legacy_resp.text
        assert legacy_resp.headers.get("deprecation") == "true"
        assert "</api/v1/settings/users>; rel=\"successor-version\"" in legacy_resp.headers.get("link", "")
        assert v1_resp.status_code == 200, v1_resp.text
        assert [user["email"] for user in legacy_resp.json()] == [user["email"] for user in v1_resp.json()]

    def test_v1_settings_create_user_preserves_legacy_behavior(self):
        login_resp = _login()
        assert login_resp.status_code == 200, login_resp.text
        token = login_resp.json()["access_token"]

        unique_email = f"settings-v1-{uuid.uuid4().hex[:8]}@acenta.test"
        create_resp = requests.post(
            f"{BASE_URL}/api/v1/settings/users",
            headers=_bearer(token),
            json={
                "email": unique_email,
                "name": "Settings Alias User",
                "password": "AliasPass123!",
                "roles": ["agency_agent"],
            },
            timeout=30,
        )
        assert create_resp.status_code == 200, create_resp.text
        assert create_resp.json()["email"] == unique_email

        legacy_list = requests.get(f"{BASE_URL}/api/settings/users", headers=_bearer(token), timeout=30)
        assert legacy_list.status_code == 200, legacy_list.text
        assert any(user["email"] == unique_email for user in legacy_list.json())

    def test_v1_settings_list_works_with_cookie_auth(self):
        session = requests.Session()
        login_resp = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers=WEB_HEADERS,
            timeout=30,
        )
        assert login_resp.status_code == 200, login_resp.text
        assert login_resp.json()["auth_transport"] == "cookie_compat"
        access_token = login_resp.json()["access_token"]

        v1_resp = session.get(f"{BASE_URL}/api/v1/settings/users", headers=WEB_HEADERS, timeout=30)
        mobile_resp = requests.get(f"{BASE_URL}/api/v1/mobile/auth/me", headers=_bearer(access_token), timeout=30)

        assert v1_resp.status_code == 200, v1_resp.text
        assert isinstance(v1_resp.json(), list)
        assert mobile_resp.status_code == 200, mobile_resp.text


class TestSettingsRouteInventoryArtifacts:
    def test_pr_v1_2c_inventory_diff_and_summary_updated(self):
        inventory = json.loads(Path("/app/backend/app/bootstrap/route_inventory.json").read_text())
        summary = json.loads(Path("/app/backend/app/bootstrap/route_inventory_summary.json").read_text())
        diff_report = json.loads(Path("/app/backend/app/bootstrap/route_inventory_diff.json").read_text())

        inventory_set = {(entry["method"], entry["path"]) for entry in inventory}
        assert ("GET", "/api/v1/settings/users") in inventory_set
        assert ("POST", "/api/v1/settings/users") in inventory_set
        assert diff_report["summary"]["new_v1_route_count"] == 2
        assert {item["path"] for item in diff_report["added_paths"]} == {"/api/v1/settings/users"}
        assert summary["v1_count"] >= 25
        assert summary["domain_v1_progress"]["system"]["migrated_v1_route_count"] >= 6
        assert set(summary["migration_velocity"].keys()) == {"routes_migrated_this_pr", "routes_remaining", "estimated_prs_remaining"}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])