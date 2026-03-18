"""Tenant Isolation Admin API Tests — verifies all admin endpoints.

Tests:
1. GET /api/admin/tenant-isolation/health — health check (super admin only)
2. GET /api/admin/tenant-isolation/violations — violation logs (super admin only)
3. POST /api/admin/tenant-isolation/ensure-indexes — index creation (super admin only)
4. GET /api/admin/tenant-isolation/orphaned-documents — orphaned docs (super admin only)
5. GET /api/admin/tenant-isolation/scope-summary — scope summary (super admin only)
6. Non-super-admin users should get 'Super admin only' error

Run: pytest /app/backend/tests/test_tenant_isolation_api.py -v
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestTenantIsolationAdminAPI:
    """Test tenant isolation admin endpoints via HTTP."""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"},
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def agency_admin_token(self):
        """Get agency admin token (non-super-admin)."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agency1@demo.test", "password": "agency123"},
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    # ============================================================================
    # Test: /api/admin/tenant-isolation/health
    # ============================================================================
    
    def test_health_super_admin_success(self, super_admin_token):
        """Super admin should access health endpoint successfully."""
        response = requests.get(
            f"{BASE_URL}/api/admin/tenant-isolation/health",
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert "report" in data
        report = data["report"]
        assert "health_score" in report
        assert "collections_checked" in report
        assert "collections_healthy" in report
    
    def test_health_agency_admin_denied(self, agency_admin_token):
        """Agency admin should get 'Super admin only' error."""
        response = requests.get(
            f"{BASE_URL}/api/admin/tenant-isolation/health",
            headers={"Authorization": f"Bearer {agency_admin_token}"},
        )
        assert response.status_code == 200  # Returns 200 with error message
        data = response.json()
        assert data.get("error") == "Super admin only"
    
    def test_health_no_auth_denied(self):
        """Unauthenticated request should be denied."""
        response = requests.get(
            f"{BASE_URL}/api/admin/tenant-isolation/health",
        )
        # Should return 401 or 403
        assert response.status_code in [401, 403]
    
    # ============================================================================
    # Test: /api/admin/tenant-isolation/violations
    # ============================================================================
    
    def test_violations_super_admin_success(self, super_admin_token):
        """Super admin should access violations endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/admin/tenant-isolation/violations",
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "violations" in data
        assert "count" in data
        assert isinstance(data["violations"], list)
    
    def test_violations_agency_admin_denied(self, agency_admin_token):
        """Agency admin should get 'Super admin only' error."""
        response = requests.get(
            f"{BASE_URL}/api/admin/tenant-isolation/violations",
            headers={"Authorization": f"Bearer {agency_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("error") == "Super admin only"
    
    def test_violations_with_limit(self, super_admin_token):
        """Violations endpoint should respect limit parameter."""
        response = requests.get(
            f"{BASE_URL}/api/admin/tenant-isolation/violations?limit=5",
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["violations"]) <= 5
    
    # ============================================================================
    # Test: /api/admin/tenant-isolation/ensure-indexes
    # ============================================================================
    
    def test_ensure_indexes_super_admin_success(self, super_admin_token):
        """Super admin should be able to ensure indexes."""
        response = requests.post(
            f"{BASE_URL}/api/admin/tenant-isolation/ensure-indexes",
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert "created_indexes" in data
        assert "already_indexed" in data
        assert "errors" in data
        assert "timestamp" in data
    
    def test_ensure_indexes_agency_admin_denied(self, agency_admin_token):
        """Agency admin should get 'Super admin only' error."""
        response = requests.post(
            f"{BASE_URL}/api/admin/tenant-isolation/ensure-indexes",
            headers={"Authorization": f"Bearer {agency_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("error") == "Super admin only"
    
    # ============================================================================
    # Test: /api/admin/tenant-isolation/orphaned-documents
    # ============================================================================
    
    def test_orphaned_documents_super_admin_success(self, super_admin_token):
        """Super admin should access orphaned documents endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/admin/tenant-isolation/orphaned-documents",
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert "orphaned_documents" in data
        assert "total_orphaned" in data
        assert "collections_affected" in data
        assert "timestamp" in data
    
    def test_orphaned_documents_agency_admin_denied(self, agency_admin_token):
        """Agency admin should get 'Super admin only' error."""
        response = requests.get(
            f"{BASE_URL}/api/admin/tenant-isolation/orphaned-documents",
            headers={"Authorization": f"Bearer {agency_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("error") == "Super admin only"
    
    # ============================================================================
    # Test: /api/admin/tenant-isolation/scope-summary
    # ============================================================================
    
    def test_scope_summary_super_admin_success(self, super_admin_token):
        """Super admin should access scope summary endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/admin/tenant-isolation/scope-summary",
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert "collections" in data
        assert "timestamp" in data
        # Verify collection structure
        if data["collections"]:
            coll = data["collections"][0]
            assert "collection" in coll
            assert "total" in coll
            assert "scoped" in coll
            assert "unscoped" in coll
            assert "coverage" in coll
    
    def test_scope_summary_agency_admin_denied(self, agency_admin_token):
        """Agency admin should get 'Super admin only' error."""
        response = requests.get(
            f"{BASE_URL}/api/admin/tenant-isolation/scope-summary",
            headers={"Authorization": f"Bearer {agency_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("error") == "Super admin only"
    
    # ============================================================================
    # Test: All endpoints with no auth
    # ============================================================================
    
    def test_all_endpoints_require_auth(self):
        """All tenant isolation admin endpoints should require authentication."""
        endpoints = [
            ("GET", "/api/admin/tenant-isolation/health"),
            ("GET", "/api/admin/tenant-isolation/violations"),
            ("POST", "/api/admin/tenant-isolation/ensure-indexes"),
            ("GET", "/api/admin/tenant-isolation/orphaned-documents"),
            ("GET", "/api/admin/tenant-isolation/scope-summary"),
        ]
        
        for method, path in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{path}")
            else:
                response = requests.post(f"{BASE_URL}{path}")
            
            assert response.status_code in [401, 403], \
                f"{method} {path} should require auth, got {response.status_code}"
