"""MEGA PROMPT #34 - Multi Accounting Provider Architecture Tests (iteration 98).

Tests for:
  - Provider catalog endpoints (list all, list active, get specific)
  - Provider config CRUD (configure, get, delete)
  - Connection test endpoint
  - Credential rotation
  - Health monitoring
  - RBAC: agency_admin vs super_admin permissions
  - Redis health check
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestProviderCatalog:
    """Provider catalog endpoints - list providers and capability matrix."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as super_admin for catalog tests."""
        self.session = requests.Session()
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def test_list_all_providers_returns_4_providers(self):
        """GET /api/accounting/providers/catalog - returns luca, logo, parasut, mikro."""
        resp = self.session.get(f"{BASE_URL}/api/accounting/providers/catalog")
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
        print(f"SUCCESS: Found {len(providers)} providers: {codes}")

    def test_capability_matrix_structure(self):
        """Verify each provider has capability matrix."""
        resp = self.session.get(f"{BASE_URL}/api/accounting/providers/catalog")
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
        print("SUCCESS: All providers have complete capability matrix")

    def test_list_active_providers_returns_only_luca(self):
        """GET /api/accounting/providers/catalog/active - only Luca is active."""
        resp = self.session.get(f"{BASE_URL}/api/accounting/providers/catalog/active")
        assert resp.status_code == 200, f"Active catalog failed: {resp.text}"
        providers = resp.json()["providers"]
        assert len(providers) == 1, f"Expected 1 active provider, got {len(providers)}"
        assert providers[0]["code"] == "luca", f"Expected luca, got {providers[0]['code']}"
        assert providers[0]["is_active"] is True
        print("SUCCESS: Only Luca is active provider")

    def test_get_specific_provider_luca(self):
        """GET /api/accounting/providers/catalog/luca - returns Luca details."""
        resp = self.session.get(f"{BASE_URL}/api/accounting/providers/catalog/luca")
        assert resp.status_code == 200, f"Get luca failed: {resp.text}"
        p = resp.json()
        assert p["code"] == "luca"
        assert p["name"] == "Luca"
        assert p["is_active"] is True
        assert p["capabilities"]["customer_management"] is True
        assert p["capabilities"]["invoice_creation"] is True
        assert len(p["credential_fields"]) >= 3
        print(f"SUCCESS: Luca details - {p['name']}, rate_limit={p['rate_limit_rpm']}")

    def test_get_specific_provider_logo(self):
        """GET /api/accounting/providers/catalog/logo - Logo is inactive."""
        resp = self.session.get(f"{BASE_URL}/api/accounting/providers/catalog/logo")
        assert resp.status_code == 200
        p = resp.json()
        assert p["code"] == "logo"
        assert p["is_active"] is False
        print(f"SUCCESS: Logo is inactive stub - {p['description'][:50]}...")

    def test_get_specific_provider_parasut(self):
        """GET /api/accounting/providers/catalog/parasut - Parasut is inactive."""
        resp = self.session.get(f"{BASE_URL}/api/accounting/providers/catalog/parasut")
        assert resp.status_code == 200
        p = resp.json()
        assert p["code"] == "parasut"
        assert p["is_active"] is False
        print("SUCCESS: Parasut is inactive stub")

    def test_get_specific_provider_mikro(self):
        """GET /api/accounting/providers/catalog/mikro - Mikro is inactive."""
        resp = self.session.get(f"{BASE_URL}/api/accounting/providers/catalog/mikro")
        assert resp.status_code == 200
        p = resp.json()
        assert p["code"] == "mikro"
        assert p["is_active"] is False
        print("SUCCESS: Mikro is inactive stub")

    def test_get_nonexistent_provider_404(self):
        """GET /api/accounting/providers/catalog/unknown - returns 404."""
        resp = self.session.get(f"{BASE_URL}/api/accounting/providers/catalog/unknown")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("SUCCESS: Unknown provider returns 404")


class TestProviderConfig:
    """Provider configuration CRUD tests."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as super_admin."""
        self.session = requests.Session()
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def test_configure_luca_provider(self):
        """POST /api/accounting/providers/config - configure Luca."""
        payload = {
            "provider_code": "luca",
            "credentials": {
                "username": "TEST_luca_user",
                "password": "TEST_luca_pass",
                "company_id": "TEST_FIRMA001",
            },
        }
        resp = self.session.post(f"{BASE_URL}/api/accounting/providers/config", json=payload)
        assert resp.status_code == 200, f"Config failed: {resp.text}"
        data = resp.json()
        assert data.get("provider_code") == "luca"
        assert data.get("status") == "configured"
        assert "config_id" in data
        assert "encrypted_credentials" not in data, "Credentials should not be exposed"
        print(f"SUCCESS: Luca configured, config_id={data.get('config_id')}")

    def test_configure_inactive_provider_returns_400(self):
        """POST /api/accounting/providers/config with logo - should fail."""
        payload = {
            "provider_code": "logo",
            "credentials": {"api_key": "test", "api_secret": "test", "company_code": "test"},
        }
        resp = self.session.post(f"{BASE_URL}/api/accounting/providers/config", json=payload)
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        error = resp.json()
        assert "aktif degil" in error.get("detail", "").lower() or "active" in str(error).lower()
        print(f"SUCCESS: Inactive provider correctly rejected: {error}")

    def test_configure_unknown_provider_returns_400(self):
        """POST /api/accounting/providers/config with unknown provider."""
        payload = {
            "provider_code": "unknown_provider",
            "credentials": {"key": "value"},
        }
        resp = self.session.post(f"{BASE_URL}/api/accounting/providers/config", json=payload)
        assert resp.status_code == 400
        print("SUCCESS: Unknown provider rejected with 400")

    def test_get_current_config(self):
        """GET /api/accounting/providers/config - returns configured provider."""
        # First configure
        self.session.post(
            f"{BASE_URL}/api/accounting/providers/config",
            json={
                "provider_code": "luca",
                "credentials": {"username": "TEST_user2", "password": "TEST_pass2", "company_id": "TEST_C2"},
            },
        )
        # Get config
        resp = self.session.get(f"{BASE_URL}/api/accounting/providers/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("configured") is True
        provider = data.get("provider")
        assert provider is not None
        assert provider.get("provider_code") == "luca"
        assert "masked_credentials" in provider
        # Verify credentials are masked
        masked = provider.get("masked_credentials", {})
        if masked:
            for key, val in masked.items():
                assert "***" in str(val) or len(str(val)) <= 4, f"Credential {key} not masked: {val}"
        print(f"SUCCESS: Got config with masked credentials: {list(masked.keys())}")


class TestConnectionTest:
    """Connection test endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def test_test_connection_simulated_mode(self):
        """POST /api/accounting/providers/test-connection - simulated mode."""
        # Ensure Luca is configured
        self.session.post(
            f"{BASE_URL}/api/accounting/providers/config",
            json={
                "provider_code": "luca",
                "credentials": {"username": "TEST_conn", "password": "TEST_conn", "company_id": "TEST_CONN"},
            },
        )
        resp = self.session.post(f"{BASE_URL}/api/accounting/providers/test-connection")
        assert resp.status_code == 200, f"Test connection failed: {resp.text}"
        data = resp.json()
        assert data.get("success") is True, f"Test connection not successful: {data}"
        assert data.get("status") in ["connected", "simulated"], f"Unexpected status: {data}"
        print(f"SUCCESS: Connection test - status={data.get('status')}")


class TestCredentialRotation:
    """Credential rotation tests."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def test_rotate_credentials(self):
        """POST /api/accounting/providers/rotate-credentials."""
        # Configure first
        self.session.post(
            f"{BASE_URL}/api/accounting/providers/config",
            json={
                "provider_code": "luca",
                "credentials": {"username": "TEST_old", "password": "TEST_old", "company_id": "TEST_OLD"},
            },
        )
        # Rotate
        resp = self.session.post(
            f"{BASE_URL}/api/accounting/providers/rotate-credentials",
            json={"credentials": {"username": "TEST_rotated", "password": "TEST_rotated_pass", "company_id": "TEST_ROT"}},
        )
        assert resp.status_code == 200, f"Rotate failed: {resp.text}"
        data = resp.json()
        assert "encrypted_credentials" not in data
        assert data.get("status") == "configured"
        print("SUCCESS: Credentials rotated")


class TestDeleteConfig:
    """Delete provider config tests."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def test_delete_config(self):
        """DELETE /api/accounting/providers/config."""
        # Configure first
        self.session.post(
            f"{BASE_URL}/api/accounting/providers/config",
            json={
                "provider_code": "luca",
                "credentials": {"username": "TEST_del", "password": "TEST_del", "company_id": "TEST_DEL"},
            },
        )
        # Delete
        resp = self.session.delete(f"{BASE_URL}/api/accounting/providers/config")
        assert resp.status_code == 200, f"Delete failed: {resp.text}"
        assert resp.json().get("deleted") is True
        # Verify deleted
        get_resp = self.session.get(f"{BASE_URL}/api/accounting/providers/config")
        assert get_resp.status_code == 200
        assert get_resp.json().get("configured") is False
        print("SUCCESS: Config deleted and verified")


class TestHealthDashboard:
    """Health monitoring endpoint tests."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def test_health_dashboard(self):
        """GET /api/accounting/providers/health - health dashboard."""
        resp = self.session.get(f"{BASE_URL}/api/accounting/providers/health")
        assert resp.status_code == 200, f"Health failed: {resp.text}"
        data = resp.json()
        assert "tenant_providers" in data, "Missing tenant_providers"
        assert "metrics_24h" in data, "Missing metrics_24h"
        assert "metrics_1h" in data, "Missing metrics_1h"
        assert "available_providers" in data, "Missing available_providers"
        print(f"SUCCESS: Health dashboard - providers={data.get('available_providers')}")


class TestRBACAgencyAdmin:
    """RBAC tests - agency_admin can view catalog but cannot configure."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agency1@demo.test", "password": "agency123"},
        )
        if login_resp.status_code != 200:
            pytest.skip(f"Agency login failed: {login_resp.text}")
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def test_agency_admin_can_view_catalog(self):
        """Agency admin CAN access GET /api/accounting/providers/catalog."""
        resp = self.session.get(f"{BASE_URL}/api/accounting/providers/catalog")
        # agency_admin should be in ALLOWED_ROLES
        assert resp.status_code == 200, f"Agency should access catalog: {resp.status_code} - {resp.text}"
        providers = resp.json().get("providers", [])
        assert len(providers) == 4
        print("SUCCESS: Agency admin CAN view catalog")

    def test_agency_admin_cannot_configure_provider(self):
        """Agency admin CANNOT access POST /api/accounting/providers/config."""
        resp = self.session.post(
            f"{BASE_URL}/api/accounting/providers/config",
            json={
                "provider_code": "luca",
                "credentials": {"username": "TEST_agency", "password": "TEST_agency", "company_id": "TEST_AG"},
            },
        )
        # POST /config requires super_admin, admin, finance_admin (not agency_admin)
        assert resp.status_code in [401, 403], f"Agency should NOT configure: {resp.status_code}"
        print(f"SUCCESS: Agency admin correctly blocked from config (status={resp.status_code})")

    def test_agency_admin_cannot_test_connection(self):
        """Agency admin CANNOT access POST /api/accounting/providers/test-connection."""
        resp = self.session.post(f"{BASE_URL}/api/accounting/providers/test-connection")
        assert resp.status_code in [401, 403, 404], f"Agency should NOT test connection: {resp.status_code}"
        print(f"SUCCESS: Agency admin blocked from test-connection (status={resp.status_code})")


class TestRedisHealth:
    """Redis health check."""

    def test_redis_ping(self):
        """Verify Redis is running."""
        import subprocess
        result = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True)
        assert result.returncode == 0, f"Redis not running: {result.stderr}"
        assert "PONG" in result.stdout, f"Unexpected redis response: {result.stdout}"
        print("SUCCESS: Redis PONG")


class TestCleanup:
    """Cleanup test data and re-configure Luca for frontend tests."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def test_reconfigure_luca_for_frontend(self):
        """Re-configure Luca provider for frontend tests."""
        payload = {
            "provider_code": "luca",
            "credentials": {
                "username": "demo_user",
                "password": "demo_pass",
                "company_id": "FIRMA001",
            },
        }
        resp = self.session.post(f"{BASE_URL}/api/accounting/providers/config", json=payload)
        assert resp.status_code == 200
        print("SUCCESS: Luca re-configured for frontend tests")
