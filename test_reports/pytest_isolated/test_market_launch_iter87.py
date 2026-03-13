"""Market Launch API Tests - MEGA PROMPT #28

Tests for Market Launch & First Customers endpoints:
- Pilot agency management (list, onboard, update)
- Usage metrics
- Feedback collection
- SaaS pricing tiers
- Launch KPIs & Report
- Support channels
- Market positioning
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestAuth:
    """Get authentication token for API tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login as super_admin to get access token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]


@pytest.fixture(scope="module")
def auth_headers():
    """Module-scoped auth headers fixture"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ================== PILOT AGENCIES ==================

class TestPilotAgencies:
    """Pilot agency management tests"""
    
    def test_get_pilot_agencies(self, auth_headers):
        """GET /api/market-launch/pilot-agencies returns list with summary"""
        response = requests.get(
            f"{BASE_URL}/api/market-launch/pilot-agencies",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Data assertions
        assert "agencies" in data, "No agencies list"
        assert "summary" in data, "No summary"
        
        summary = data["summary"]
        assert "total" in summary
        assert "active" in summary
        assert "onboarding" in summary
        assert "with_bookings" in summary
        assert "with_feedback" in summary
        assert "adoption_rate_pct" in summary
        
        # Should have at least 3 seeded agencies
        assert len(data["agencies"]) >= 3, "Expected at least 3 pilot agencies"
    
    def test_onboard_new_agency(self, auth_headers):
        """POST /api/market-launch/pilot-agencies/onboard creates new agency"""
        payload = {
            "company_name": "TEST_MARKET_LAUNCH_AGENCY",
            "contact_name": "Test Contact",
            "contact_email": "test@marketlaunch.com",
            "contact_phone": "+90 555 123 4567",
            "pricing_tier": "starter"
        }
        response = requests.post(
            f"{BASE_URL}/api/market-launch/pilot-agencies/onboard",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Data assertions
        assert data.get("status") == "onboarded"
        assert "agency" in data
        agency = data["agency"]
        assert agency["company_name"] == payload["company_name"]
        assert agency["contact_name"] == payload["contact_name"]
        assert agency["contact_email"] == payload["contact_email"]
        assert agency["pricing_tier"] == payload["pricing_tier"]
        assert agency["status"] == "onboarding"
        assert agency["supplier_credentials_status"] == "pending"
    
    def test_update_agency_status(self, auth_headers):
        """PUT /api/market-launch/pilot-agencies/update changes status"""
        # First get agencies to get a valid company name
        response = requests.get(
            f"{BASE_URL}/api/market-launch/pilot-agencies",
            headers=auth_headers
        )
        agencies = response.json().get("agencies", [])
        
        # Find our test agency or first available
        test_agency = next((a for a in agencies if "TEST_MARKET_LAUNCH" in a.get("company_name", "")), None)
        if test_agency:
            company_name = test_agency["company_name"]
        else:
            # Use first agency if test one doesn't exist
            assert len(agencies) > 0, "No agencies to update"
            company_name = agencies[0]["company_name"]
        
        payload = {
            "company_name": company_name,
            "status": "active",
            "supplier_credentials_status": "configured"
        }
        response = requests.put(
            f"{BASE_URL}/api/market-launch/pilot-agencies/update",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Data assertions
        assert data.get("status") == "updated"
        assert "agency" in data
        updated = data["agency"]
        assert updated["status"] == "active"
        assert updated["supplier_credentials_status"] == "configured"
    
    def test_pilot_agencies_requires_auth(self):
        """Pilot agencies endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/market-launch/pilot-agencies")
        assert response.status_code in [401, 403]


# ================== USAGE METRICS ==================

class TestUsageMetrics:
    """Usage metrics tests"""
    
    def test_get_usage_metrics_default(self, auth_headers):
        """GET /api/market-launch/usage-metrics returns 7-day metrics"""
        response = requests.get(
            f"{BASE_URL}/api/market-launch/usage-metrics",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Data assertions
        assert data.get("period_days") == 7
        assert "searches" in data
        assert "bookings" in data
        assert "commissions" in data
        assert "conversion_rate_pct" in data
        assert "revenue" in data
        assert "margin" in data
        assert "daily" in data
        
        # Daily breakdown should have 7 entries
        assert len(data["daily"]) == 7, "Expected 7 daily entries"
    
    def test_get_usage_metrics_custom_days(self, auth_headers):
        """GET /api/market-launch/usage-metrics?days=14 returns 14-day metrics"""
        response = requests.get(
            f"{BASE_URL}/api/market-launch/usage-metrics?days=14",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data.get("period_days") == 14
        assert len(data["daily"]) == 14
    
    def test_get_usage_metrics_30_days(self, auth_headers):
        """GET /api/market-launch/usage-metrics?days=30 returns 30-day metrics"""
        response = requests.get(
            f"{BASE_URL}/api/market-launch/usage-metrics?days=30",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data.get("period_days") == 30


# ================== FEEDBACK ==================

class TestFeedback:
    """Feedback collection tests"""
    
    def test_submit_feedback(self, auth_headers):
        """POST /api/market-launch/feedback submits agency feedback"""
        payload = {
            "agency_name": "TEST_FEEDBACK_AGENCY",
            "ratings": {
                "search_speed": 4,
                "supplier_coverage": 5,
                "price_comparison": 4,
                "booking_experience": 5,
                "support_quality": 3,
                "overall_satisfaction": 4
            },
            "comments": "Test feedback comment from iteration 87"
        }
        response = requests.post(
            f"{BASE_URL}/api/market-launch/feedback",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Data assertions
        assert data.get("status") == "submitted"
        assert "feedback" in data
        fb = data["feedback"]
        assert fb["agency_name"] == payload["agency_name"]
        assert fb["ratings"] == payload["ratings"]
        assert "submitted_at" in fb
    
    def test_get_feedback_summary(self, auth_headers):
        """GET /api/market-launch/feedback returns feedback summary"""
        response = requests.get(
            f"{BASE_URL}/api/market-launch/feedback",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Data assertions
        assert "total_responses" in data
        assert "averages" in data
        assert "overall_score" in data
        assert "feedbacks" in data
        assert "questions" in data
        
        # Should have at least 1 feedback (seeded + our test)
        assert data["total_responses"] >= 1
        
        # Questions should have 7 items
        assert len(data["questions"]) == 7


# ================== PRICING ==================

class TestPricing:
    """SaaS pricing tiers tests"""
    
    def test_get_pricing_tiers(self, auth_headers):
        """GET /api/market-launch/pricing returns 4 pricing tiers"""
        response = requests.get(
            f"{BASE_URL}/api/market-launch/pricing",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Data assertions
        assert "tiers" in data
        tiers = data["tiers"]
        assert len(tiers) == 4, "Expected 4 pricing tiers"
        
        tier_names = [t["tier"] for t in tiers]
        assert "free" in tier_names
        assert "starter" in tier_names
        assert "pro" in tier_names
        assert "enterprise" in tier_names
        
        # Verify Free tier
        free_tier = next(t for t in tiers if t["tier"] == "free")
        assert free_tier["price_monthly_eur"] == 0
        assert free_tier["commission_pct"] == 3.0
        
        # Verify Starter tier
        starter_tier = next(t for t in tiers if t["tier"] == "starter")
        assert starter_tier["price_monthly_eur"] == 49
        assert starter_tier["commission_pct"] == 2.0
        
        # Verify Pro tier
        pro_tier = next(t for t in tiers if t["tier"] == "pro")
        assert pro_tier["price_monthly_eur"] == 149
        assert pro_tier["commission_pct"] == 1.0
        
        # Verify Enterprise tier (custom pricing)
        enterprise_tier = next(t for t in tiers if t["tier"] == "enterprise")
        assert enterprise_tier["price_monthly_eur"] == -1  # custom


# ================== LAUNCH KPIs ==================

class TestLaunchKPIs:
    """Launch KPI dashboard tests"""
    
    def test_get_launch_kpis(self, auth_headers):
        """GET /api/market-launch/launch-kpis returns KPI dashboard data"""
        response = requests.get(
            f"{BASE_URL}/api/market-launch/launch-kpis",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Data assertions
        assert "active_agencies" in data
        assert "total_agencies" in data
        assert "daily_searches" in data
        assert "total_searches_30d" in data
        assert "total_bookings_30d" in data
        assert "booking_conversion_pct" in data
        assert "supplier_success_rate_pct" in data
        assert "cache_hit_rate_pct" in data
        assert "platform_revenue_30d" in data
        assert "platform_margin_30d" in data
        assert "feedback_score" in data
        assert "feedback_count" in data


# ================== LAUNCH REPORT ==================

class TestLaunchReport:
    """Launch report tests"""
    
    def test_get_launch_report(self, auth_headers):
        """GET /api/market-launch/launch-report returns full report"""
        response = requests.get(
            f"{BASE_URL}/api/market-launch/launch-report",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Data assertions
        assert data.get("report_type") == "market_launch"
        assert "generated_at" in data
        assert "market_readiness_score" in data
        assert "pilot_summary" in data
        assert "usage_metrics" in data
        assert "feedback_summary" in data
        assert "kpis" in data
        assert "pricing_model" in data
        assert "positioning" in data
        assert "support_channels" in data
        assert "technical_readiness" in data
        
        # Check market readiness score structure
        mrs = data["market_readiness_score"]
        assert "overall" in mrs
        assert "dimensions" in mrs
        assert isinstance(mrs["overall"], (int, float))
        
        # Dimensions should have expected keys
        dims = mrs["dimensions"]
        assert "pilot_adoption" in dims
        assert "search_volume" in dims
        assert "booking_activity" in dims
        assert "feedback_quality" in dims
        assert "technical_maturity" in dims
        assert "monitoring_readiness" in dims
        assert "revenue_tracking" in dims


# ================== SUPPORT ==================

class TestSupport:
    """Support channels tests"""
    
    def test_get_support_channels(self, auth_headers):
        """GET /api/market-launch/support returns support channels"""
        response = requests.get(
            f"{BASE_URL}/api/market-launch/support",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Data assertions
        assert "channels" in data
        channels = data["channels"]
        assert len(channels) == 4, "Expected 4 support channels"
        
        channel_types = [ch["channel"] for ch in channels]
        assert "email" in channel_types
        assert "whatsapp" in channel_types
        assert "documentation" in channel_types
        assert "faq" in channel_types
        
        # Check SLA fields
        for ch in channels:
            assert "response_sla" in ch


# ================== POSITIONING ==================

class TestPositioning:
    """Market positioning tests"""
    
    def test_get_market_positioning(self, auth_headers):
        """GET /api/market-launch/positioning returns market positioning"""
        response = requests.get(
            f"{BASE_URL}/api/market-launch/positioning",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Data assertions
        assert "tagline" in data
        assert "headline" in data
        assert "value_props" in data
        assert "target_audience" in data
        assert "differentiators" in data
        
        assert data["tagline"] == "Multi-Supplier Travel Automation Platform"
        assert len(data["value_props"]) >= 4
        assert len(data["differentiators"]) >= 4


# ================== AUTHORIZATION TESTS ==================

class TestAuthorization:
    """Authorization tests for market launch endpoints"""
    
    def test_all_endpoints_require_auth(self):
        """All market launch endpoints should require authentication"""
        endpoints = [
            ("GET", "/api/market-launch/pilot-agencies"),
            ("POST", "/api/market-launch/pilot-agencies/onboard"),
            ("PUT", "/api/market-launch/pilot-agencies/update"),
            ("GET", "/api/market-launch/usage-metrics"),
            ("POST", "/api/market-launch/feedback"),
            ("GET", "/api/market-launch/feedback"),
            ("GET", "/api/market-launch/pricing"),
            ("GET", "/api/market-launch/launch-kpis"),
            ("GET", "/api/market-launch/launch-report"),
            ("GET", "/api/market-launch/support"),
            ("GET", "/api/market-launch/positioning"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            elif method == "POST":
                response = requests.post(f"{BASE_URL}{endpoint}", json={})
            elif method == "PUT":
                response = requests.put(f"{BASE_URL}{endpoint}", json={})
            
            assert response.status_code in [401, 403], f"{method} {endpoint} should require auth, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
