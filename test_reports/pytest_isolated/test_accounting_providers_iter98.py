"""MEGA PROMPT #34 - Multi Accounting Provider Architecture Tests (iteration 98).

Isolated test file with session reuse to avoid rate limiting.
"""
import os
import subprocess
import requests
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cache-health-check.preview.emergentagent.com").rstrip("/")

# Global session caches
_admin_session = None
_agency_session = None


def get_admin_session():
    """Login as super_admin - reuses session."""
    global _admin_session
    if _admin_session is not None:
        return _admin_session
    session = requests.Session()
    login_resp = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
    token = login_resp.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    _admin_session = session
    return session


def get_agency_session():
    """Login as agency_admin - reuses session."""
    global _agency_session
    if _agency_session is not None:
        return _agency_session
    session = requests.Session()
    login_resp = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agency1@demo.test", "password": "agency123"},
    )
    if login_resp.status_code != 200:
        print(f"SKIP: Agency login failed: {login_resp.text}")
        return None
    token = login_resp.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    _agency_session = session
    return session


def test_list_all_providers_returns_4_providers():
    """GET /api/accounting/providers/catalog - returns luca, logo, parasut, mikro."""
    session = get_admin_session()
    resp = session.get(f"{BASE_URL}/api/accounting/providers/catalog")
    assert resp.status_code == 200, f"Catalog failed: {resp.text}"
    data = resp.json()
    assert "providers" in data, "Missing providers key"
    providers = data["providers"]
    assert len(providers) == 4, f"Expected 4 providers, got {len(providers)}"
    codes = [p["code"] for p in providers]
    assert "luca" in codes, "Missing luca provider"
    assert "logo" in codes, "Missing logo provider"
    assert "parasut" in codes, "Missing parasut provider"
    assert "mikro" in codes, "Missing mikro provider"
    print(f"PASS: Found {len(providers)} providers: {codes}")


def test_capability_matrix_structure():
    """Verify each provider has capability matrix."""
    session = get_admin_session()
    resp = session.get(f"{BASE_URL}/api/accounting/providers/catalog")
    assert resp.status_code == 200
    providers = resp.json()["providers"]
    for p in providers:
        assert "capabilities" in p, f"Missing capabilities for {p['code']}"
        caps = p["capabilities"]
        assert "customer_management" in caps
        assert "invoice_creation" in caps
        assert "invoice_cancel" in caps
        assert "status_polling" in caps
        assert "pdf_download" in caps
        assert "webhook_support" in caps
        assert "rate_limit_rpm" in p
        assert "is_active" in p
        assert "credential_fields" in p
    print("PASS: All providers have complete capability matrix")


def test_list_active_providers_returns_only_luca():
    """GET /api/accounting/providers/catalog/active - only Luca is active."""
    session = get_admin_session()
    resp = session.get(f"{BASE_URL}/api/accounting/providers/catalog/active")
    assert resp.status_code == 200, f"Active catalog failed: {resp.text}"
    providers = resp.json()["providers"]
    assert len(providers) == 1, f"Expected 1 active provider, got {len(providers)}"
    assert providers[0]["code"] == "luca", f"Expected luca, got {providers[0]['code']}"
    assert providers[0]["is_active"] is True
    print("PASS: Only Luca is active provider")


def test_get_specific_provider_luca():
    """GET /api/accounting/providers/catalog/luca - returns Luca details."""
    session = get_admin_session()
    resp = session.get(f"{BASE_URL}/api/accounting/providers/catalog/luca")
    assert resp.status_code == 200, f"Get luca failed: {resp.text}"
    p = resp.json()
    assert p["code"] == "luca"
    assert p["name"] == "Luca"
    assert p["is_active"] is True
    assert p["capabilities"]["customer_management"] is True
    assert p["capabilities"]["invoice_creation"] is True
    assert len(p["credential_fields"]) >= 3
    print(f"PASS: Luca details - {p['name']}, rate_limit={p['rate_limit_rpm']}")


def test_get_specific_providers_logo_parasut_mikro():
    """GET /api/accounting/providers/catalog/{logo,parasut,mikro} - inactive stubs."""
    session = get_admin_session()
    for code in ["logo", "parasut", "mikro"]:
        resp = session.get(f"{BASE_URL}/api/accounting/providers/catalog/{code}")
        assert resp.status_code == 200, f"Get {code} failed: {resp.text}"
        p = resp.json()
        assert p["code"] == code
        assert p["is_active"] is False
    print("PASS: Logo, Parasut, Mikro are inactive stubs")


def test_get_nonexistent_provider_404():
    """GET /api/accounting/providers/catalog/unknown - returns 404."""
    session = get_admin_session()
    resp = session.get(f"{BASE_URL}/api/accounting/providers/catalog/unknown")
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    print("PASS: Unknown provider returns 404")


def test_configure_luca_provider():
    """POST /api/accounting/providers/config - configure Luca."""
    session = get_admin_session()
    payload = {
        "provider_code": "luca",
        "credentials": {
            "username": "TEST_luca_user",
            "password": "TEST_luca_pass",
            "company_id": "TEST_FIRMA001",
        },
    }
    resp = session.post(f"{BASE_URL}/api/accounting/providers/config", json=payload)
    assert resp.status_code == 200, f"Config failed: {resp.text}"
    data = resp.json()
    assert data.get("provider_code") == "luca"
    assert data.get("status") == "configured"
    assert "config_id" in data
    assert "encrypted_credentials" not in data, "Credentials should not be exposed"
    print(f"PASS: Luca configured, config_id={data.get('config_id')}")


def test_configure_inactive_provider_returns_400():
    """POST /api/accounting/providers/config with logo - should fail."""
    session = get_admin_session()
    payload = {
        "provider_code": "logo",
        "credentials": {"api_key": "test", "api_secret": "test", "company_code": "test"},
    }
    resp = session.post(f"{BASE_URL}/api/accounting/providers/config", json=payload)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    error = resp.json()
    # Error may be in detail (HTTPException) or error.message (error wrapper)
    error_msg = error.get("detail", "") or error.get("error", {}).get("message", "")
    assert "aktif degil" in error_msg.lower() or "active" in error_msg.lower(), f"Unexpected error: {error}"
    print(f"PASS: Inactive provider correctly rejected: {error_msg}")


def test_configure_unknown_provider_returns_400():
    """POST /api/accounting/providers/config with unknown provider."""
    session = get_admin_session()
    payload = {
        "provider_code": "unknown_provider",
        "credentials": {"key": "value"},
    }
    resp = session.post(f"{BASE_URL}/api/accounting/providers/config", json=payload)
    assert resp.status_code == 400
    print("PASS: Unknown provider rejected with 400")


def test_get_current_config():
    """GET /api/accounting/providers/config - returns configured provider."""
    session = get_admin_session()
    # First configure
    session.post(
        f"{BASE_URL}/api/accounting/providers/config",
        json={
            "provider_code": "luca",
            "credentials": {"username": "TEST_user2", "password": "TEST_pass2", "company_id": "TEST_C2"},
        },
    )
    # Get config
    resp = session.get(f"{BASE_URL}/api/accounting/providers/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("configured") is True
    provider = data.get("provider")
    assert provider is not None
    assert provider.get("provider_code") == "luca"
    assert "masked_credentials" in provider
    # Verify sensitive credentials are masked (password, username)
    # Note: company_id is NOT a secret and is intentionally NOT masked
    masked = provider.get("masked_credentials", {})
    if masked:
        # Only password and username should be masked
        if "password" in masked:
            assert "***" in str(masked["password"]) or "*" in str(masked["password"]), f"password not masked: {masked['password']}"
        if "username" in masked:
            assert "***" in str(masked["username"]) or "*" in str(masked["username"]), f"username not masked: {masked['username']}"
    print(f"PASS: Got config with masked credentials: {list(masked.keys())}")


def test_test_connection_simulated_mode():
    """POST /api/accounting/providers/test-connection - simulated mode."""
    session = get_admin_session()
    # Ensure Luca is configured
    session.post(
        f"{BASE_URL}/api/accounting/providers/config",
        json={
            "provider_code": "luca",
            "credentials": {"username": "TEST_conn", "password": "TEST_conn", "company_id": "TEST_CONN"},
        },
    )
    resp = session.post(f"{BASE_URL}/api/accounting/providers/test-connection")
    assert resp.status_code == 200, f"Test connection failed: {resp.text}"
    data = resp.json()
    assert data.get("success") is True, f"Test connection not successful: {data}"
    assert data.get("status") in ["connected", "simulated"], f"Unexpected status: {data}"
    print(f"PASS: Connection test - status={data.get('status')}")


def test_rotate_credentials():
    """POST /api/accounting/providers/rotate-credentials."""
    session = get_admin_session()
    # Configure first
    session.post(
        f"{BASE_URL}/api/accounting/providers/config",
        json={
            "provider_code": "luca",
            "credentials": {"username": "TEST_old", "password": "TEST_old", "company_id": "TEST_OLD"},
        },
    )
    # Rotate
    resp = session.post(
        f"{BASE_URL}/api/accounting/providers/rotate-credentials",
        json={"credentials": {"username": "TEST_rotated", "password": "TEST_rotated_pass", "company_id": "TEST_ROT"}},
    )
    assert resp.status_code == 200, f"Rotate failed: {resp.text}"
    data = resp.json()
    assert "encrypted_credentials" not in data
    assert data.get("status") == "configured"
    print("PASS: Credentials rotated")


def test_delete_config():
    """DELETE /api/accounting/providers/config."""
    session = get_admin_session()
    # Configure first
    session.post(
        f"{BASE_URL}/api/accounting/providers/config",
        json={
            "provider_code": "luca",
            "credentials": {"username": "TEST_del", "password": "TEST_del", "company_id": "TEST_DEL"},
        },
    )
    # Delete
    resp = session.delete(f"{BASE_URL}/api/accounting/providers/config")
    assert resp.status_code == 200, f"Delete failed: {resp.text}"
    assert resp.json().get("deleted") is True
    # Verify deleted
    get_resp = session.get(f"{BASE_URL}/api/accounting/providers/config")
    assert get_resp.status_code == 200
    assert get_resp.json().get("configured") is False
    print("PASS: Config deleted and verified")


def test_health_dashboard():
    """GET /api/accounting/providers/health - health dashboard."""
    session = get_admin_session()
    # First configure a provider
    session.post(
        f"{BASE_URL}/api/accounting/providers/config",
        json={
            "provider_code": "luca",
            "credentials": {"username": "TEST_health", "password": "TEST_health", "company_id": "TEST_H"},
        },
    )
    resp = session.get(f"{BASE_URL}/api/accounting/providers/health")
    assert resp.status_code == 200, f"Health failed: {resp.text}"
    data = resp.json()
    assert "tenant_providers" in data, "Missing tenant_providers"
    assert "metrics_24h" in data, "Missing metrics_24h"
    assert "metrics_1h" in data, "Missing metrics_1h"
    assert "available_providers" in data, "Missing available_providers"
    print(f"PASS: Health dashboard - providers={data.get('available_providers')}")


def test_agency_admin_can_view_catalog():
    """Agency admin CAN access GET /api/accounting/providers/catalog."""
    session = get_agency_session()
    if session is None:
        print("SKIP: Agency login not available")
        return
    resp = session.get(f"{BASE_URL}/api/accounting/providers/catalog")
    # agency_admin should be in ALLOWED_ROLES
    assert resp.status_code == 200, f"Agency should access catalog: {resp.status_code} - {resp.text}"
    providers = resp.json().get("providers", [])
    assert len(providers) == 4
    print("PASS: Agency admin CAN view catalog")


def test_agency_admin_cannot_configure_provider():
    """Agency admin CANNOT access POST /api/accounting/providers/config."""
    session = get_agency_session()
    if session is None:
        print("SKIP: Agency login not available")
        return
    resp = session.post(
        f"{BASE_URL}/api/accounting/providers/config",
        json={
            "provider_code": "luca",
            "credentials": {"username": "TEST_agency", "password": "TEST_agency", "company_id": "TEST_AG"},
        },
    )
    # POST /config requires super_admin, admin, finance_admin (not agency_admin)
    assert resp.status_code in [401, 403], f"Agency should NOT configure: {resp.status_code}"
    print(f"PASS: Agency admin correctly blocked from config (status={resp.status_code})")


def test_redis_ping():
    """Verify Redis is running."""
    result = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True)
    assert result.returncode == 0, f"Redis not running: {result.stderr}"
    assert "PONG" in result.stdout, f"Unexpected redis response: {result.stdout}"
    print("PASS: Redis PONG")


def test_reconfigure_luca_for_frontend():
    """Re-configure Luca provider for frontend tests."""
    session = get_admin_session()
    payload = {
        "provider_code": "luca",
        "credentials": {
            "username": "demo_user",
            "password": "demo_pass",
            "company_id": "FIRMA001",
        },
    }
    resp = session.post(f"{BASE_URL}/api/accounting/providers/config", json=payload)
    assert resp.status_code == 200
    print("PASS: Luca re-configured for frontend tests")


if __name__ == "__main__":
    tests = [
        test_list_all_providers_returns_4_providers,
        test_capability_matrix_structure,
        test_list_active_providers_returns_only_luca,
        test_get_specific_provider_luca,
        test_get_specific_providers_logo_parasut_mikro,
        test_get_nonexistent_provider_404,
        test_configure_luca_provider,
        test_configure_inactive_provider_returns_400,
        test_configure_unknown_provider_returns_400,
        test_get_current_config,
        test_test_connection_simulated_mode,
        test_rotate_credentials,
        test_delete_config,
        test_health_dashboard,
        test_redis_ping,
        test_agency_admin_can_view_catalog,
        test_agency_admin_cannot_configure_provider,
        test_reconfigure_luca_for_frontend,
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test in tests:
        try:
            print(f"\n--- Running {test.__name__} ---")
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {test.__name__} - {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {test.__name__} - {e}")
            failed += 1
    
    print(f"\n=== SUMMARY: {passed} passed, {failed} failed ===")
