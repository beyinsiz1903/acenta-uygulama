"""
Iteration 39 - Agency Reports, Global Search, and Admin Tenant Features Testing

Features to test:
1. Agency login and /app/reports page access
2. Global search API: /api/search with query param
3. Operations report generation: /api/reports/generate with tenant fallback
4. Sales summary and CSV export: /api/reports/sales-summary, /api/reports/sales-summary.csv
5. Admin tenant features: /api/admin/tenants, /api/admin/tenants/{id}/features
6. Agency backend no-regression: /api/agency/hotels, /api/agency/bookings, /api/agency/settlements
"""
import os
import pytest
import requests
from typing import Dict, Any, Optional

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

class AuthHelper:
    """Helper for authentication"""
    
    @staticmethod
    def login(email: str, password: str) -> Optional[str]:
        """Get auth token via login"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": email, "password": password},
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token") or data.get("token")
            elif response.status_code == 429:
                pytest.skip(f"Rate limited on login for {email}")
            return None
        except Exception as e:
            pytest.skip(f"Login error: {str(e)}")
            return None


@pytest.fixture(scope="module")
def agency_token():
    """Get agency user token"""
    token = AuthHelper.login("agent@acenta.test", "agent123")
    if not token:
        pytest.skip("Could not authenticate agency user")
    return token


@pytest.fixture(scope="module")
def admin_token():
    """Get admin user token"""
    token = AuthHelper.login("admin@acenta.test", "admin123")
    if not token:
        pytest.skip("Could not authenticate admin user")
    return token


@pytest.fixture(scope="module")
def agency_session(agency_token):
    """Agency authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {agency_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def admin_session(admin_token):
    """Admin authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


# =============================================================================
# Section 1: Agency Hotels, Bookings, Settlements (No-Regression)
# =============================================================================

class TestAgencyEndpointsNoRegression:
    """Test agency backend endpoints are working"""
    
    def test_agency_hotels_returns_200(self, agency_session):
        """GET /api/agency/hotels returns 200"""
        response = agency_session.get(f"{BASE_URL}/api/agency/hotels", timeout=15)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Should return a list (can be empty)
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Agency hotels returned {len(data)} hotels")
    
    def test_agency_bookings_returns_200(self, agency_session):
        """GET /api/agency/bookings returns 200"""
        response = agency_session.get(f"{BASE_URL}/api/agency/bookings", timeout=15)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Could be list or dict with items
        if isinstance(data, dict):
            items = data.get("items") or data.get("bookings") or []
            print(f"Agency bookings returned {len(items)} bookings")
        else:
            print(f"Agency bookings returned {len(data)} bookings")
    
    def test_agency_settlements_returns_200_with_month(self, agency_session):
        """GET /api/agency/settlements?month=2026-03 returns 200"""
        response = agency_session.get(
            f"{BASE_URL}/api/agency/settlements",
            params={"month": "2026-03"},
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        print(f"Agency settlements returned: {type(data)}")


# =============================================================================
# Section 2: Global Search API
# =============================================================================

class TestGlobalSearchAPI:
    """Test /api/search endpoint"""
    
    def test_global_search_returns_200(self, agency_session):
        """GET /api/search?q=demo returns 200 with sections"""
        response = agency_session.get(
            f"{BASE_URL}/api/search",
            params={"q": "demo", "limit": 4},
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "query" in data, "Response should have 'query' field"
        assert "sections" in data, "Response should have 'sections' field"
        assert "counts" in data, "Response should have 'counts' field"
        assert "total_results" in data, "Response should have 'total_results' field"
        
        # Verify sections structure
        sections = data["sections"]
        assert "customers" in sections, "sections should have 'customers'"
        assert "bookings" in sections, "sections should have 'bookings'"
        assert "hotels" in sections, "sections should have 'hotels'"
        assert "tours" in sections, "sections should have 'tours'"
        
        print(f"Global search: query='{data['query']}', total={data['total_results']}, counts={data['counts']}")
    
    def test_global_search_requires_minimum_query_length(self, agency_session):
        """GET /api/search?q=a returns 422 (min 2 chars)"""
        response = agency_session.get(
            f"{BASE_URL}/api/search",
            params={"q": "a"},
            timeout=15
        )
        assert response.status_code == 422, f"Expected 422 for single char, got {response.status_code}"
    
    def test_global_search_with_admin_scope(self, admin_session):
        """Admin search returns organization scope"""
        response = admin_session.get(
            f"{BASE_URL}/api/search",
            params={"q": "test", "limit": 3},
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("scope") == "organization", f"Admin should have organization scope, got {data.get('scope')}"
        print(f"Admin global search: scope={data.get('scope')}, total={data.get('total_results')}")


# =============================================================================
# Section 3: Reports Generation API (with tenant fallback)
# =============================================================================

class TestReportsGenerateAPI:
    """Test /api/reports/generate endpoint with tenant fallback"""
    
    def test_reports_generate_returns_200_with_agency_user(self, agency_session):
        """GET /api/reports/generate?days=30 returns 200 with KPIs"""
        response = agency_session.get(
            f"{BASE_URL}/api/reports/generate",
            params={"days": 30},
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify KPI structure
        assert "kpis" in data, "Response should have 'kpis' field"
        assert "period" in data, "Response should have 'period' field"
        assert "generated_at" in data, "Response should have 'generated_at' field"
        
        kpis = data["kpis"]
        assert "booking_count" in kpis, "kpis should have 'booking_count'"
        assert "revenue_total" in kpis, "kpis should have 'revenue_total'"
        assert "avg_booking_value" in kpis, "kpis should have 'avg_booking_value'"
        assert "active_customer_count" in kpis, "kpis should have 'active_customer_count'"
        
        print(f"Reports generate: bookings={kpis['booking_count']}, revenue={kpis['revenue_total']}")
    
    def test_reports_generate_returns_200_with_admin_user(self, admin_session):
        """Admin can also generate reports"""
        response = admin_session.get(
            f"{BASE_URL}/api/reports/generate",
            params={"days": 7},
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "kpis" in data, "Admin report should have KPIs"
        print(f"Admin reports generate: period={data.get('period')}")
    
    def test_reports_generate_post_method_works(self, agency_session):
        """POST /api/reports/generate also works"""
        response = agency_session.post(
            f"{BASE_URL}/api/reports/generate",
            json={"days": 14},
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "kpis" in data, "POST response should have KPIs"


# =============================================================================
# Section 4: Sales Summary and CSV Export
# =============================================================================

class TestSalesSummaryAPI:
    """Test sales summary endpoints"""
    
    def test_sales_summary_returns_200(self, agency_session):
        """GET /api/reports/sales-summary returns 200"""
        response = agency_session.get(
            f"{BASE_URL}/api/reports/sales-summary",
            params={"days": 14},
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Sales summary returned {len(data)} day entries")
    
    def test_reservations_summary_returns_200(self, agency_session):
        """GET /api/reports/reservations-summary returns 200"""
        response = agency_session.get(
            f"{BASE_URL}/api/reports/reservations-summary",
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Reservations summary returned {len(data)} status entries")
    
    def test_sales_summary_csv_returns_csv(self, agency_session):
        """GET /api/reports/sales-summary.csv returns CSV"""
        response = agency_session.get(
            f"{BASE_URL}/api/reports/sales-summary.csv",
            params={"days": 7},
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        content_type = response.headers.get("Content-Type", "")
        assert "text/csv" in content_type, f"Expected text/csv, got {content_type}"
        print(f"CSV export returned {len(response.text)} bytes")


# =============================================================================
# Section 5: Admin Tenant Features
# =============================================================================

class TestAdminTenantFeaturesAPI:
    """Test admin tenant management endpoints"""
    
    def test_admin_tenants_list_returns_200(self, admin_session):
        """GET /api/admin/tenants returns list of tenants"""
        response = admin_session.get(f"{BASE_URL}/api/admin/tenants", timeout=15)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Could be list or dict with items
        if isinstance(data, dict):
            items = data.get("items") or data.get("tenants") or []
        else:
            items = data
        
        assert len(items) > 0, "Should have at least one tenant"
        print(f"Admin tenants list returned {len(items)} tenants")
        
        # Return first tenant ID for subsequent tests
        return items[0].get("id")
    
    def test_admin_tenant_features_returns_200(self, admin_session):
        """GET /api/admin/tenants/{id}/features returns plan and add-ons"""
        # First get tenant list
        tenants_response = admin_session.get(f"{BASE_URL}/api/admin/tenants", timeout=15)
        assert tenants_response.status_code == 200
        tenants_data = tenants_response.json()
        
        if isinstance(tenants_data, dict):
            items = tenants_data.get("items") or tenants_data.get("tenants") or []
        else:
            items = tenants_data
        
        if not items:
            pytest.skip("No tenants available")
        
        tenant_id = items[0].get("id")
        
        # Get features for tenant
        response = admin_session.get(
            f"{BASE_URL}/api/admin/tenants/{tenant_id}/features",
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "plan" in data, "Response should have 'plan' field"
        print(f"Tenant features: plan={data.get('plan')}, add_ons={data.get('add_ons')}")
    
    def test_admin_tenant_subscription_returns_200_or_404(self, admin_session):
        """GET /api/admin/billing/tenants/{id}/subscription returns subscription info"""
        # First get tenant list
        tenants_response = admin_session.get(f"{BASE_URL}/api/admin/tenants", timeout=15)
        assert tenants_response.status_code == 200
        tenants_data = tenants_response.json()
        
        if isinstance(tenants_data, dict):
            items = tenants_data.get("items") or tenants_data.get("tenants") or []
        else:
            items = tenants_data
        
        if not items:
            pytest.skip("No tenants available")
        
        tenant_id = items[0].get("id")
        
        # Get subscription for tenant
        response = admin_session.get(
            f"{BASE_URL}/api/admin/billing/tenants/{tenant_id}/subscription",
            timeout=15
        )
        # Can be 200 (has subscription) or 404 (no subscription)
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            print(f"Tenant subscription: {data.get('subscription', {}).get('status')}")
        else:
            print("Tenant has no active subscription")


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
