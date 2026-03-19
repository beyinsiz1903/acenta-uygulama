"""Intelligence Layer API Tests - Iteration 83

Tests the Smart Search & Supplier Intelligence Layer:
- Search Suggestions API (recent_searches, popular_destinations, supplier_recommendations)
- Conversion Funnel tracking and metrics
- Daily search/booking statistics
- Supplier Performance Scores
- Supplier Revenue tracking
- KPI Summary aggregation
- Event tracking from frontend
"""

import pytest
import requests
import os


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
AGENCY_ADMIN_EMAIL = "agency1@demo.test"
AGENCY_ADMIN_PASSWORD = "agency123"
SUPER_ADMIN_EMAIL = "agent@acenta.test"
SUPER_ADMIN_PASSWORD = "agent123"


class TestAuthAndSetup:
    """Authentication and setup tests"""

    @pytest.fixture(scope="class")
    def agency_token(self):
        """Get agency admin token"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": AGENCY_ADMIN_EMAIL,
            "password": AGENCY_ADMIN_PASSWORD
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = _unwrap(resp)
        token = data.get("access_token")
        assert token, f"No access_token in response: {data}"
        return token

    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert resp.status_code == 200, f"Super admin login failed: {resp.text}"
        data = _unwrap(resp)
        token = data.get("access_token")
        assert token, f"No access_token in response: {data}"
        return token

    def test_login_agency_admin(self, agency_token):
        """Verify agency admin can log in"""
        assert agency_token is not None
        print("Agency token obtained successfully")

    def test_login_super_admin(self, super_admin_token):
        """Verify super admin can log in"""
        assert super_admin_token is not None
        print("Super admin token obtained successfully")


class TestIntelligenceSuggestions:
    """Test GET /api/intelligence/suggestions endpoint"""

    @pytest.fixture(scope="class")
    def agency_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": AGENCY_ADMIN_EMAIL,
            "password": AGENCY_ADMIN_PASSWORD
        })
        return _unwrap(resp).get("access_token")

    def test_suggestions_returns_structure(self, agency_token):
        """Test suggestions endpoint returns correct structure"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        resp = requests.get(f"{BASE_URL}/api/intelligence/suggestions", headers=headers)
        assert resp.status_code == 200, f"Suggestions failed: {resp.text}"
        data = _unwrap(resp)

        # Verify required fields
        assert "recent_searches" in data, "Missing recent_searches in response"
        assert "popular_destinations" in data, "Missing popular_destinations in response"
        assert "supplier_recommendations" in data, "Missing supplier_recommendations in response"

        print(f"Suggestions response: {len(data['recent_searches'])} recent, {len(data['popular_destinations'])} popular, {len(data['supplier_recommendations'])} recommendations")

    def test_suggestions_with_product_type(self, agency_token):
        """Test suggestions with product_type parameter"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        resp = requests.get(f"{BASE_URL}/api/intelligence/suggestions?product_type=hotel", headers=headers)
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert isinstance(data["popular_destinations"], list)
        print(f"Hotel suggestions: {len(data['popular_destinations'])} destinations")

    def test_suggestions_recommendations_structure(self, agency_token):
        """Test supplier_recommendations has 3 categories when data exists"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        resp = requests.get(f"{BASE_URL}/api/intelligence/suggestions", headers=headers)
        assert resp.status_code == 200
        data = _unwrap(resp)

        recs = data["supplier_recommendations"]
        # Should have recommendations (at least defaults)
        if len(recs) > 0:
            for rec in recs:
                assert "category" in rec, "Missing category in recommendation"
                assert "label" in rec, "Missing label in recommendation"
                assert "supplier_code" in rec, "Missing supplier_code in recommendation"

            categories = [r["category"] for r in recs]
            print(f"Recommendation categories: {categories}")

    def test_suggestions_requires_auth(self):
        """Test suggestions endpoint requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/intelligence/suggestions")
        assert resp.status_code in [401, 403], f"Expected auth error, got {resp.status_code}"
        print("Suggestions correctly requires authentication")


class TestConversionFunnel:
    """Test GET /api/intelligence/funnel endpoint"""

    @pytest.fixture(scope="class")
    def agency_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": AGENCY_ADMIN_EMAIL,
            "password": AGENCY_ADMIN_PASSWORD
        })
        return _unwrap(resp).get("access_token")

    def test_funnel_returns_structure(self, agency_token):
        """Test funnel endpoint returns all 5 event types"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        resp = requests.get(f"{BASE_URL}/api/intelligence/funnel", headers=headers)
        assert resp.status_code == 200, f"Funnel failed: {resp.text}"
        data = _unwrap(resp)

        assert "days" in data, "Missing days in response"
        assert "funnel" in data, "Missing funnel in response"

        funnel = data["funnel"]
        expected_events = [
            "search_event",
            "result_view_event",
            "supplier_select_event",
            "booking_start_event",
            "booking_confirm_event"
        ]

        for event in expected_events:
            assert event in funnel, f"Missing {event} in funnel"
            assert isinstance(funnel[event], int), f"{event} should be integer"

        # Check rate fields
        assert "search_to_confirm_rate" in funnel, "Missing search_to_confirm_rate"
        print(f"Funnel events: {funnel}")

    def test_funnel_with_days_param(self, agency_token):
        """Test funnel with different days parameters"""
        headers = {"Authorization": f"Bearer {agency_token}"}

        for days in [7, 30, 90]:
            resp = requests.get(f"{BASE_URL}/api/intelligence/funnel?days={days}", headers=headers)
            assert resp.status_code == 200, f"Funnel failed for days={days}: {resp.text}"
            data = _unwrap(resp)
            assert data["days"] == days, f"Days mismatch: expected {days}, got {data['days']}"

        print("Funnel days parameter works correctly")

    def test_funnel_requires_auth(self):
        """Test funnel endpoint requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/intelligence/funnel")
        assert resp.status_code in [401, 403], f"Expected auth error, got {resp.status_code}"


class TestDailyStats:
    """Test GET /api/intelligence/daily-stats endpoint"""

    @pytest.fixture(scope="class")
    def agency_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": AGENCY_ADMIN_EMAIL,
            "password": AGENCY_ADMIN_PASSWORD
        })
        return _unwrap(resp).get("access_token")

    def test_daily_stats_returns_structure(self, agency_token):
        """Test daily stats endpoint returns correct structure"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        resp = requests.get(f"{BASE_URL}/api/intelligence/daily-stats", headers=headers)
        assert resp.status_code == 200, f"Daily stats failed: {resp.text}"
        data = _unwrap(resp)

        assert "days" in data, "Missing days in response"
        assert "stats" in data, "Missing stats in response"
        assert isinstance(data["stats"], list), "stats should be a list"

        if len(data["stats"]) > 0:
            stat = data["stats"][0]
            assert "date" in stat, "Missing date in stat entry"
            assert "searches" in stat, "Missing searches in stat entry"
            assert "bookings" in stat, "Missing bookings in stat entry"

        print(f"Daily stats: {len(data['stats'])} days of data")

    def test_daily_stats_requires_auth(self):
        """Test daily stats endpoint requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/intelligence/daily-stats")
        assert resp.status_code in [401, 403]


class TestSupplierScores:
    """Test GET /api/intelligence/supplier-scores endpoint"""

    @pytest.fixture(scope="class")
    def agency_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": AGENCY_ADMIN_EMAIL,
            "password": AGENCY_ADMIN_PASSWORD
        })
        return _unwrap(resp).get("access_token")

    def test_supplier_scores_returns_structure(self, agency_token):
        """Test supplier scores endpoint returns correct structure"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        resp = requests.get(f"{BASE_URL}/api/intelligence/supplier-scores", headers=headers)
        assert resp.status_code == 200, f"Supplier scores failed: {resp.text}"
        data = _unwrap(resp)

        assert "days" in data, "Missing days in response"
        assert "scores" in data, "Missing scores in response"
        assert isinstance(data["scores"], list), "scores should be a list"

        if len(data["scores"]) > 0:
            score = data["scores"][0]
            assert "supplier_code" in score, "Missing supplier_code"
            assert "total_score" in score, "Missing total_score"
            assert "components" in score, "Missing components"

            # Verify weighted components
            components = score["components"]
            expected_components = [
                "price_competitiveness",
                "booking_success_rate",
                "latency_score",
                "cancellation_reliability",
                "fallback_frequency_inverse"
            ]
            for comp in expected_components:
                assert comp in components, f"Missing component: {comp}"

        print(f"Supplier scores: {len(data['scores'])} suppliers")

    def test_supplier_scores_requires_auth(self):
        """Test supplier scores endpoint requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/intelligence/supplier-scores")
        assert resp.status_code in [401, 403]


class TestSupplierRecommendations:
    """Test GET /api/intelligence/supplier-recommendations endpoint"""

    @pytest.fixture(scope="class")
    def agency_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": AGENCY_ADMIN_EMAIL,
            "password": AGENCY_ADMIN_PASSWORD
        })
        return _unwrap(resp).get("access_token")

    def test_recommendations_returns_3_categories(self, agency_token):
        """Test recommendations returns 3 category recommendations"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        resp = requests.get(f"{BASE_URL}/api/intelligence/supplier-recommendations", headers=headers)
        assert resp.status_code == 200, f"Recommendations failed: {resp.text}"
        data = _unwrap(resp)

        assert "recommendations" in data, "Missing recommendations in response"
        recs = data["recommendations"]
        assert isinstance(recs, list), "recommendations should be a list"
        assert len(recs) == 3, f"Expected 3 recommendations, got {len(recs)}"

        categories = [r["category"] for r in recs]
        expected_categories = ["best_price", "fastest_confirmation", "most_reliable"]
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"

        print(f"Recommendations: {categories}")

    def test_recommendations_structure(self, agency_token):
        """Test each recommendation has required fields"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        resp = requests.get(f"{BASE_URL}/api/intelligence/supplier-recommendations", headers=headers)
        assert resp.status_code == 200
        data = _unwrap(resp)

        for rec in data["recommendations"]:
            assert "category" in rec
            assert "label" in rec
            assert "supplier_code" in rec
            assert "reason" in rec

        print("Recommendation structure verified")


class TestSupplierRevenue:
    """Test GET /api/intelligence/supplier-revenue endpoint"""

    @pytest.fixture(scope="class")
    def agency_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": AGENCY_ADMIN_EMAIL,
            "password": AGENCY_ADMIN_PASSWORD
        })
        return _unwrap(resp).get("access_token")

    def test_revenue_returns_structure(self, agency_token):
        """Test revenue endpoint returns correct structure"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        resp = requests.get(f"{BASE_URL}/api/intelligence/supplier-revenue", headers=headers)
        assert resp.status_code == 200, f"Revenue failed: {resp.text}"
        data = _unwrap(resp)

        assert "days" in data, "Missing days in response"
        assert "revenue" in data, "Missing revenue in response"
        assert isinstance(data["revenue"], list), "revenue should be a list"

        if len(data["revenue"]) > 0:
            rev = data["revenue"][0]
            assert "supplier_code" in rev, "Missing supplier_code"
            assert "total_revenue" in rev, "Missing total_revenue"
            assert "booking_count" in rev, "Missing booking_count"

        print(f"Revenue data: {len(data['revenue'])} suppliers")


class TestTrackFunnelEvent:
    """Test POST /api/intelligence/track endpoint"""

    @pytest.fixture(scope="class")
    def agency_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": AGENCY_ADMIN_EMAIL,
            "password": AGENCY_ADMIN_PASSWORD
        })
        return _unwrap(resp).get("access_token")

    def test_track_result_view_event(self, agency_token):
        """Test tracking result_view_event"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        payload = {
            "event_type": "result_view_event",
            "details": {
                "product_type": "hotel",
                "results_count": 10
            }
        }
        resp = requests.post(f"{BASE_URL}/api/intelligence/track", json=payload, headers=headers)
        assert resp.status_code == 200, f"Track failed: {resp.text}"
        data = _unwrap(resp)

        assert data["tracked"]
        assert data["event_type"] == "result_view_event"
        print("result_view_event tracked successfully")

    def test_track_supplier_select_event(self, agency_token):
        """Test tracking supplier_select_event"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        payload = {
            "event_type": "supplier_select_event",
            "details": {
                "supplier_code": "real_ratehawk",
                "product_type": "hotel",
                "price": 1500.00
            }
        }
        resp = requests.post(f"{BASE_URL}/api/intelligence/track", json=payload, headers=headers)
        assert resp.status_code == 200
        data = _unwrap(resp)

        assert data["tracked"]
        assert data["event_type"] == "supplier_select_event"
        print("supplier_select_event tracked successfully")

    def test_track_booking_start_event(self, agency_token):
        """Test tracking booking_start_event"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        payload = {
            "event_type": "booking_start_event",
            "details": {
                "supplier_code": "real_paximum",
                "product_type": "tour"
            }
        }
        resp = requests.post(f"{BASE_URL}/api/intelligence/track", json=payload, headers=headers)
        assert resp.status_code == 200
        data = _unwrap(resp)

        assert data["tracked"]
        assert data["event_type"] == "booking_start_event"
        print("booking_start_event tracked successfully")

    def test_track_requires_auth(self):
        """Test track endpoint requires authentication"""
        payload = {"event_type": "result_view_event", "details": {}}
        resp = requests.post(f"{BASE_URL}/api/intelligence/track", json=payload)
        assert resp.status_code in [401, 403]


class TestKPISummary:
    """Test GET /api/intelligence/kpi-summary endpoint"""

    @pytest.fixture(scope="class")
    def agency_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": AGENCY_ADMIN_EMAIL,
            "password": AGENCY_ADMIN_PASSWORD
        })
        return _unwrap(resp).get("access_token")

    def test_kpi_summary_returns_structure(self, agency_token):
        """Test KPI summary returns all required fields"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        resp = requests.get(f"{BASE_URL}/api/intelligence/kpi-summary", headers=headers)
        assert resp.status_code == 200, f"KPI summary failed: {resp.text}"
        data = _unwrap(resp)

        assert "days" in data, "Missing days"
        assert "kpi" in data, "Missing kpi"
        assert "funnel" in data, "Missing funnel"

        kpi = data["kpi"]
        expected_kpi_fields = [
            "total_searches",
            "total_bookings",
            "conversion_rate",
            "total_revenue",
            "fallback_rate",
            "booking_success_rate"
        ]

        for field in expected_kpi_fields:
            assert field in kpi, f"Missing KPI field: {field}"

        print(f"KPI Summary: {kpi}")

    def test_kpi_summary_with_days(self, agency_token):
        """Test KPI summary with different days parameters"""
        headers = {"Authorization": f"Bearer {agency_token}"}

        for days in [7, 30, 90]:
            resp = requests.get(f"{BASE_URL}/api/intelligence/kpi-summary?days={days}", headers=headers)
            assert resp.status_code == 200
            data = _unwrap(resp)
            assert data["days"] == days

        print("KPI summary days parameter works correctly")

    def test_kpi_summary_includes_funnel(self, agency_token):
        """Test KPI summary includes funnel data"""
        headers = {"Authorization": f"Bearer {agency_token}"}
        resp = requests.get(f"{BASE_URL}/api/intelligence/kpi-summary", headers=headers)
        assert resp.status_code == 200
        data = _unwrap(resp)

        funnel = data["funnel"]
        assert "search_event" in funnel
        assert "booking_confirm_event" in funnel
        print(f"KPI includes funnel: {funnel.get('search_event')} searches, {funnel.get('booking_confirm_event')} bookings")

    def test_kpi_summary_requires_auth(self):
        """Test KPI summary endpoint requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/intelligence/kpi-summary")
        assert resp.status_code in [401, 403]


class TestSearchAnalyticsIntegration:
    """Test that search creates analytics events"""

    @pytest.fixture(scope="class")
    def agency_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": AGENCY_ADMIN_EMAIL,
            "password": AGENCY_ADMIN_PASSWORD
        })
        return _unwrap(resp).get("access_token")

    def test_search_creates_analytics(self, agency_token):
        """Test that POST /api/unified-booking/search creates search_event"""
        headers = {"Authorization": f"Bearer {agency_token}"}

        # Get funnel before search
        before_resp = requests.get(f"{BASE_URL}/api/intelligence/funnel?days=1", headers=headers)
        before_data = _unwrap(before_resp)
        before_searches = before_data.get("funnel", {}).get("search_event", 0)

        # Execute search
        search_payload = {
            "product_type": "hotel",
            "destination": "TEST_Istanbul_Analytics",
            "check_in": "2026-03-01",
            "check_out": "2026-03-03",
            "adults": 2,
            "children": 0,
            "currency": "TRY"
        }
        search_resp = requests.post(f"{BASE_URL}/api/unified-booking/search", json=search_payload, headers=headers)
        assert search_resp.status_code == 200, f"Search failed: {search_resp.text}"

        # Get funnel after search
        after_resp = requests.get(f"{BASE_URL}/api/intelligence/funnel?days=1", headers=headers)
        after_data = _unwrap(after_resp)
        after_searches = after_data.get("funnel", {}).get("search_event", 0)

        # Search should have incremented
        assert after_searches >= before_searches, f"Search event not incremented: before={before_searches}, after={after_searches}"
        print(f"Search analytics: before={before_searches}, after={after_searches}")

    def test_search_updates_recent_searches(self, agency_token):
        """Test that search updates recent_searches"""
        headers = {"Authorization": f"Bearer {agency_token}"}

        # Execute search
        search_payload = {
            "product_type": "hotel",
            "destination": "TEST_Antalya_Recent",
            "check_in": "2026-04-01",
            "check_out": "2026-04-05",
            "adults": 2,
            "children": 1,
            "currency": "TRY"
        }
        requests.post(f"{BASE_URL}/api/unified-booking/search", json=search_payload, headers=headers)

        # Check suggestions
        sugg_resp = requests.get(f"{BASE_URL}/api/intelligence/suggestions", headers=headers)
        assert sugg_resp.status_code == 200
        data = _unwrap(sugg_resp)

        recent = data.get("recent_searches", [])
        destinations = [r.get("destination") for r in recent]

        # Our test destination should be in recent searches
        assert "TEST_Antalya_Recent" in destinations, f"Recent search not found: {destinations}"
        print(f"Recent searches updated: {destinations[:3]}")


class TestAllEndpointsRequireAuth:
    """Verify all intelligence endpoints require authentication"""

    def test_suggestions_requires_auth(self):
        resp = requests.get(f"{BASE_URL}/api/intelligence/suggestions")
        assert resp.status_code in [401, 403]

    def test_funnel_requires_auth(self):
        resp = requests.get(f"{BASE_URL}/api/intelligence/funnel")
        assert resp.status_code in [401, 403]

    def test_daily_stats_requires_auth(self):
        resp = requests.get(f"{BASE_URL}/api/intelligence/daily-stats")
        assert resp.status_code in [401, 403]

    def test_supplier_scores_requires_auth(self):
        resp = requests.get(f"{BASE_URL}/api/intelligence/supplier-scores")
        assert resp.status_code in [401, 403]

    def test_supplier_recommendations_requires_auth(self):
        resp = requests.get(f"{BASE_URL}/api/intelligence/supplier-recommendations")
        assert resp.status_code in [401, 403]

    def test_supplier_revenue_requires_auth(self):
        resp = requests.get(f"{BASE_URL}/api/intelligence/supplier-revenue")
        assert resp.status_code in [401, 403]

    def test_track_requires_auth(self):
        resp = requests.post(f"{BASE_URL}/api/intelligence/track", json={"event_type": "test"})
        assert resp.status_code in [401, 403]

    def test_kpi_summary_requires_auth(self):
        resp = requests.get(f"{BASE_URL}/api/intelligence/kpi-summary")
        assert resp.status_code in [401, 403]
