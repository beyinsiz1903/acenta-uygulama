"""Platform Maturation Program - Iteration 153 Tests

Tests for:
1. CI Quality Gates & Coverage
2. Physical Router Migration (1440 routes)
3. Event-Driven Core + Cache Strategy
4. Live Architecture Documentation
5. Dependency/Scope Audit

Multi-persona travel SaaS platform (Admin, Agency, Hotel, B2B)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ddd-router-hub.preview.emergentagent.com").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "Admin123!@#"
AGENCY_EMAIL = "agency1@demo.test"
AGENCY_PASSWORD = "Agency123!@#"


class TestHealthAndBasics:
    """Basic health and connectivity tests"""
    
    def test_health_endpoint(self):
        """GET /api/health returns ok"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print(f"Health check passed: {data}")
    
    def test_root_endpoint(self):
        """GET / returns app info"""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"Root endpoint: {data}")


class TestAuthentication:
    """Authentication flow tests"""
    
    def test_admin_login(self):
        """POST /api/auth/login with admin credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        assert "access_token" in data.get("data", {})
        assert data["data"]["user"]["email"] == ADMIN_EMAIL
        assert "super_admin" in data["data"]["user"]["roles"]
        print(f"Admin login successful: {data['data']['user']['email']}")
        return data["data"]["access_token"]
    
    def test_agency_login(self):
        """POST /api/auth/login with agency credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": AGENCY_EMAIL, "password": AGENCY_PASSWORD}
        )
        # Agency user may or may not exist in test DB
        if response.status_code == 200:
            data = response.json()
            assert data.get("ok") is True
            print(f"Agency login successful")
        else:
            print(f"Agency user not found (expected in some environments)")
            pytest.skip("Agency user not seeded")


class TestDashboardAPIs:
    """Dashboard API tests for all personas"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["data"]["access_token"]
    
    def test_admin_dashboard_today(self, admin_token):
        """GET /api/dashboard/admin-today returns valid data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/admin-today",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        
        # Verify expected keys
        dashboard_data = data.get("data", {})
        expected_keys = ["alerts", "operations", "finance", "pending_approvals", "system_health"]
        for key in expected_keys:
            assert key in dashboard_data, f"Missing key: {key}"
        print(f"Admin dashboard keys: {list(dashboard_data.keys())}")
    
    def test_agency_dashboard_today(self, admin_token):
        """GET /api/dashboard/agency-today returns valid data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/agency-today",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        
        dashboard_data = data.get("data", {})
        expected_keys = ["today_tasks", "counters", "today_kpi", "recent_activity"]
        for key in expected_keys:
            assert key in dashboard_data, f"Missing key: {key}"
        print(f"Agency dashboard keys: {list(dashboard_data.keys())}")
    
    def test_hotel_dashboard_today(self, admin_token):
        """GET /api/dashboard/hotel-today returns valid data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/hotel-today",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        
        dashboard_data = data.get("data", {})
        expected_keys = ["checkin_checkout", "occupancy", "alerts", "pending", "revenue", "upcoming_arrivals", "recent_activity"]
        for key in expected_keys:
            assert key in dashboard_data, f"Missing key: {key}"
        print(f"Hotel dashboard keys: {list(dashboard_data.keys())}")
    
    def test_b2b_dashboard_today(self, admin_token):
        """GET /api/dashboard/b2b-today returns valid data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/b2b-today",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        
        dashboard_data = data.get("data", {})
        expected_keys = ["pipeline", "partners", "pending", "revenue", "recent_bookings", "recent_activity", "announcements"]
        for key in expected_keys:
            assert key in dashboard_data, f"Missing key: {key}"
        print(f"B2B dashboard keys: {list(dashboard_data.keys())}")


class TestRouteInventory:
    """Route inventory and migration tests"""
    
    def test_route_count_above_threshold(self):
        """Backend should have 1400+ routes after migration"""
        import json
        inventory_path = "/app/backend/app/bootstrap/route_inventory.json"
        
        with open(inventory_path) as f:
            routes = json.load(f)
        
        route_count = len(routes)
        assert route_count >= 1400, f"Expected 1400+ routes, got {route_count}"
        print(f"Route count: {route_count}")
    
    def test_route_inventory_summary(self):
        """Route inventory summary should exist and be valid"""
        import json
        summary_path = "/app/backend/app/bootstrap/route_inventory_summary.json"
        
        with open(summary_path) as f:
            summary = json.load(f)
        
        assert "route_count" in summary
        assert summary["route_count"] >= 1400
        assert "namespaces" in summary
        print(f"Route summary: {summary['route_count']} routes across {len(summary['namespaces'])} namespaces")


class TestArchitectureGuard:
    """Architecture guard and scope audit tests"""
    
    def test_architecture_guard_passes(self):
        """Architecture guard test should pass"""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_architecture_guard.py", "-v", "--tb=short"],
            cwd="/app/backend",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Architecture guard failed:\n{result.stdout}\n{result.stderr}"
        print("Architecture guard: PASSED")
    
    def test_scope_audit_passes(self):
        """Scope audit test should pass"""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_scope_audit.py", "-v", "--tb=short"],
            cwd="/app/backend",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Scope audit failed:\n{result.stdout}\n{result.stderr}"
        print("Scope audit: PASSED")
    
    def test_event_cache_passes(self):
        """Event-cache tests should pass"""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_event_cache.py", "-v", "--tb=short"],
            cwd="/app/backend",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Event-cache tests failed:\n{result.stdout}\n{result.stderr}"
        print("Event-cache tests: PASSED")


class TestGeneratedDocs:
    """Generated architecture documentation tests"""
    
    def test_docs_freshness(self):
        """Generated docs should be up to date"""
        import subprocess
        result = subprocess.run(
            ["python", "scripts/generate_arch_docs.py", "--check"],
            cwd="/app/backend",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Docs freshness check failed:\n{result.stdout}\n{result.stderr}"
        assert "up to date" in result.stdout.lower() or result.returncode == 0
        print("Docs freshness: PASSED")
    
    def test_generated_docs_exist(self):
        """All expected generated docs should exist"""
        import os
        docs_dir = "/app/docs/generated"
        expected_files = [
            "CACHE_SURFACES.md",
            "DOMAIN_OWNERSHIP.md",
            "EVENT_CATALOG.md",
            "NAVIGATION_INDEX.md",
            "ROUTER_MAP.md"
        ]
        
        for filename in expected_files:
            filepath = os.path.join(docs_dir, filename)
            assert os.path.exists(filepath), f"Missing doc: {filename}"
        print(f"All {len(expected_files)} generated docs exist")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
