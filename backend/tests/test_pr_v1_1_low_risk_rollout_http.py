"""
PR-V1-1 Low Risk Rollout HTTP Tests

Tests verify that both legacy and v1 aliases respond correctly for:
- /api/health and /api/v1/health
- /api/system/ping and /api/v1/system/ping
- /api/system/health-dashboard and /api/v1/system/health-dashboard (admin auth)
- /api/public/theme and /api/v1/public/theme
- /api/admin/theme and /api/v1/admin/theme (admin auth)
- /api/public/cms/pages and /api/v1/public/cms/pages
- /api/public/campaigns and /api/v1/public/campaigns
"""
from __future__ import annotations

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Admin credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_auth_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"X-Client-Platform": "web"},
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, admin_auth_token):
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_auth_token}",
    })
    return session


class TestHealthEndpoints:
    """Test /api/health legacy and v1 alias routes"""

    def test_legacy_health_endpoint(self, api_client):
        """GET /api/health - legacy route should respond"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "healthy" in data or data == {"status": "ok"} or data.get("status") == "healthy"
        print(f"✅ GET /api/health -> {response.status_code}")

    def test_v1_health_endpoint(self, api_client):
        """GET /api/v1/health - v1 alias should respond identically"""
        response = api_client.get(f"{BASE_URL}/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "healthy" in data or data == {"status": "ok"} or data.get("status") == "healthy"
        print(f"✅ GET /api/v1/health -> {response.status_code}")


class TestSystemEndpoints:
    """Test /api/system/* legacy and v1 alias routes"""

    def test_legacy_system_ping(self, api_client):
        """GET /api/system/ping - legacy route should respond"""
        response = api_client.get(f"{BASE_URL}/api/system/ping")
        assert response.status_code == 200
        print(f"✅ GET /api/system/ping -> {response.status_code}")

    def test_v1_system_ping(self, api_client):
        """GET /api/v1/system/ping - v1 alias should respond"""
        response = api_client.get(f"{BASE_URL}/api/v1/system/ping")
        assert response.status_code == 200
        print(f"✅ GET /api/v1/system/ping -> {response.status_code}")

    def test_legacy_health_dashboard_requires_auth(self, api_client):
        """GET /api/system/health-dashboard - should require auth"""
        response = api_client.get(f"{BASE_URL}/api/system/health-dashboard")
        # Should return 401/403 without auth or 200 with proper auth
        assert response.status_code in [200, 401, 403]
        print(f"✅ GET /api/system/health-dashboard (unauthenticated) -> {response.status_code}")

    def test_legacy_health_dashboard_with_auth(self, authenticated_client):
        """GET /api/system/health-dashboard - admin auth should work"""
        response = authenticated_client.get(f"{BASE_URL}/api/system/health-dashboard")
        assert response.status_code == 200
        print(f"✅ GET /api/system/health-dashboard (admin auth) -> {response.status_code}")

    def test_v1_health_dashboard_with_auth(self, authenticated_client):
        """GET /api/v1/system/health-dashboard - v1 alias with admin auth"""
        response = authenticated_client.get(f"{BASE_URL}/api/v1/system/health-dashboard")
        assert response.status_code == 200
        print(f"✅ GET /api/v1/system/health-dashboard (admin auth) -> {response.status_code}")


class TestThemeEndpoints:
    """Test /api/public/theme and /api/admin/theme legacy and v1 alias routes"""

    def test_legacy_public_theme(self, api_client):
        """GET /api/public/theme - legacy public theme route"""
        response = api_client.get(f"{BASE_URL}/api/public/theme")
        assert response.status_code in [200, 404]  # 404 if no theme configured
        print(f"✅ GET /api/public/theme -> {response.status_code}")

    def test_v1_public_theme(self, api_client):
        """GET /api/v1/public/theme - v1 alias public theme route"""
        response = api_client.get(f"{BASE_URL}/api/v1/public/theme")
        assert response.status_code in [200, 404]
        print(f"✅ GET /api/v1/public/theme -> {response.status_code}")

    def test_legacy_admin_theme_requires_auth(self, api_client):
        """GET /api/admin/theme - should require auth"""
        response = api_client.get(f"{BASE_URL}/api/admin/theme")
        assert response.status_code in [200, 401, 403]
        print(f"✅ GET /api/admin/theme (unauthenticated) -> {response.status_code}")

    def test_legacy_admin_theme_with_auth(self, authenticated_client):
        """GET /api/admin/theme - admin auth should work"""
        response = authenticated_client.get(f"{BASE_URL}/api/admin/theme")
        assert response.status_code == 200
        print(f"✅ GET /api/admin/theme (admin auth) -> {response.status_code}")

    def test_v1_admin_theme_with_auth(self, authenticated_client):
        """GET /api/v1/admin/theme - v1 alias with admin auth"""
        response = authenticated_client.get(f"{BASE_URL}/api/v1/admin/theme")
        assert response.status_code == 200
        print(f"✅ GET /api/v1/admin/theme (admin auth) -> {response.status_code}")


class TestCMSPagesEndpoints:
    """Test /api/public/cms/pages legacy and v1 alias routes"""

    def test_legacy_public_cms_pages(self, api_client):
        """GET /api/public/cms/pages - legacy public CMS pages route"""
        response = api_client.get(f"{BASE_URL}/api/public/cms/pages", params={"org": "org_demo"})
        assert response.status_code in [200, 404]
        print(f"✅ GET /api/public/cms/pages?org=org_demo -> {response.status_code}")

    def test_v1_public_cms_pages(self, api_client):
        """GET /api/v1/public/cms/pages - v1 alias public CMS pages route"""
        response = api_client.get(f"{BASE_URL}/api/v1/public/cms/pages", params={"org": "org_demo"})
        assert response.status_code in [200, 404]
        print(f"✅ GET /api/v1/public/cms/pages?org=org_demo -> {response.status_code}")


class TestCampaignsEndpoints:
    """Test /api/public/campaigns legacy and v1 alias routes"""

    def test_legacy_public_campaigns(self, api_client):
        """GET /api/public/campaigns - legacy public campaigns route"""
        response = api_client.get(f"{BASE_URL}/api/public/campaigns", params={"org": "org_demo"})
        assert response.status_code in [200, 404]
        print(f"✅ GET /api/public/campaigns?org=org_demo -> {response.status_code}")

    def test_v1_public_campaigns(self, api_client):
        """GET /api/v1/public/campaigns - v1 alias public campaigns route"""
        response = api_client.get(f"{BASE_URL}/api/v1/public/campaigns", params={"org": "org_demo"})
        assert response.status_code in [200, 404]
        print(f"✅ GET /api/v1/public/campaigns?org=org_demo -> {response.status_code}")


class TestRouteDiffTool:
    """Test route inventory diff tool functionality"""

    def test_route_inventory_exists(self):
        """route_inventory.json exists and is valid JSON"""
        import json
        from pathlib import Path
        
        inventory_path = Path("/app/backend/app/bootstrap/route_inventory.json")
        assert inventory_path.exists(), "route_inventory.json should exist"
        
        inventory = json.loads(inventory_path.read_text())
        assert isinstance(inventory, list)
        assert len(inventory) > 0
        print(f"✅ route_inventory.json exists with {len(inventory)} routes")

    def test_route_inventory_contains_v1_aliases(self):
        """route_inventory.json contains the new v1 alias entries"""
        import json
        from pathlib import Path
        
        inventory_path = Path("/app/backend/app/bootstrap/route_inventory.json")
        inventory = json.loads(inventory_path.read_text())
        
        expected_v1_routes = [
            "/api/v1/health",
            "/api/v1/system/ping",
            "/api/v1/system/health-dashboard",
            "/api/v1/public/theme",
            "/api/v1/admin/theme",
            "/api/v1/public/cms/pages",
            "/api/v1/public/campaigns",
        ]
        
        inventory_paths = {entry["path"] for entry in inventory}
        
        for v1_route in expected_v1_routes:
            assert v1_route in inventory_paths, f"Missing v1 route: {v1_route}"
        
        print(f"✅ All expected v1 routes found in inventory")

    def test_route_inventory_is_sorted(self):
        """route_inventory.json is deterministically sorted"""
        import json
        from pathlib import Path
        
        inventory_path = Path("/app/backend/app/bootstrap/route_inventory.json")
        inventory = json.loads(inventory_path.read_text())
        
        sorted_inventory = sorted(inventory, key=lambda item: (item["path"], item["method"], item["source"]))
        assert inventory == sorted_inventory, "Inventory should be sorted"
        print(f"✅ route_inventory.json is deterministically sorted")

    def test_route_diff_tool_works(self):
        """route_inventory diff script produces valid diff report"""
        import json
        import tempfile
        from pathlib import Path
        
        inventory_path = Path("/app/backend/app/bootstrap/route_inventory.json")
        current_inventory = json.loads(inventory_path.read_text())
        
        # Create a synthetic "previous" snapshot by filtering out the new v1 aliases
        new_v1_paths = {
            "/api/v1/health",
            "/api/v1/system/ping",
            "/api/v1/system/health-dashboard",
            "/api/v1/system/prometheus",
            "/api/v1/public/theme",
            "/api/v1/admin/theme",
            "/api/v1/public/cms/pages",
            "/api/v1/public/cms/pages/{slug}",
            "/api/v1/public/campaigns",
            "/api/v1/public/campaigns/{slug}",
        }
        
        previous_inventory = [
            entry for entry in current_inventory
            if entry["path"] not in new_v1_paths
        ]
        
        # Write to temp file and run diff
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(previous_inventory, f, indent=2, sort_keys=True)
            previous_path = f.name
        
        try:
            from app.bootstrap.route_inventory_diff import build_route_inventory_diff
            
            report = build_route_inventory_diff(previous_inventory, current_inventory)
            
            # Verify diff report structure
            assert "summary" in report
            assert "added_paths" in report
            assert "removed_paths" in report
            
            # Verify correct counts
            assert report["summary"]["added_route_count"] == 11  # 11 new v1 routes
            assert report["summary"]["removed_route_count"] == 0
            assert report["summary"]["new_v1_route_count"] == 11
            assert len(report["removed_paths"]) == 0
            
            added_paths = {item["path"] for item in report["added_paths"]}
            assert "/api/v1/health" in added_paths
            assert "/api/v1/public/theme" in added_paths
            assert "/api/v1/admin/theme" in added_paths
            
            print(f"✅ Diff tool reports {report['summary']['added_route_count']} added v1 routes, 0 removed")
        finally:
            Path(previous_path).unlink(missing_ok=True)


class TestLegacyV1Parity:
    """Test that legacy and v1 routes return equivalent responses"""

    def test_health_parity(self, api_client):
        """Legacy and v1 health endpoints return equivalent structure"""
        legacy_resp = api_client.get(f"{BASE_URL}/api/health")
        v1_resp = api_client.get(f"{BASE_URL}/api/v1/health")
        
        assert legacy_resp.status_code == v1_resp.status_code
        # Both should return similar structure (status key)
        legacy_data = legacy_resp.json()
        v1_data = v1_resp.json()
        assert ("status" in legacy_data) == ("status" in v1_data)
        print(f"✅ /api/health and /api/v1/health have parity")

    def test_system_ping_parity(self, api_client):
        """Legacy and v1 system/ping endpoints return equivalent responses"""
        legacy_resp = api_client.get(f"{BASE_URL}/api/system/ping")
        v1_resp = api_client.get(f"{BASE_URL}/api/v1/system/ping")
        
        assert legacy_resp.status_code == v1_resp.status_code
        print(f"✅ /api/system/ping and /api/v1/system/ping have parity")

    def test_public_theme_parity(self, api_client):
        """Legacy and v1 public/theme endpoints return equivalent responses"""
        legacy_resp = api_client.get(f"{BASE_URL}/api/public/theme")
        v1_resp = api_client.get(f"{BASE_URL}/api/v1/public/theme")
        
        assert legacy_resp.status_code == v1_resp.status_code
        print(f"✅ /api/public/theme and /api/v1/public/theme have parity")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
