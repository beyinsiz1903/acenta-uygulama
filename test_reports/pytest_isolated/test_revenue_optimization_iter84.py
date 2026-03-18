"""Revenue & Supplier Optimization Engine API Tests - Iteration 84.

Tests all 13 new API endpoints under /api/revenue/*:
1. GET /api/revenue/supplier-analytics - Supplier revenue data
2. GET /api/revenue/profitability-scores - Supplier profitability scores with tiers
3. POST /api/revenue/supplier-selection - Revenue-aware supplier ranking
4. GET /api/revenue/commission-summary - Commission aggregation data
5. GET /api/revenue/markup-rules - Active markup rules
6. POST /api/revenue/markup-rules - Create/update a markup rule
7. DELETE /api/revenue/markup-rules/{rule_id} - Deactivate a rule
8. POST /api/revenue/calculate-markup - Calculate markup for booking params
9. GET /api/revenue/supplier-economics - Combined economics data
10. GET /api/revenue/agency-analytics - Agency revenue analytics
11. GET /api/revenue/forecast - Revenue and booking forecasting
12. GET /api/revenue/business-kpi - Complete business KPI dashboard data
13. GET /api/revenue/destination-revenue - Destination revenue breakdown
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://async-queue-preview.preview.emergentagent.com").rstrip("/")

# Test credentials
SUPER_ADMIN_EMAIL = "agent@acenta.test"
SUPER_ADMIN_PASSWORD = "agent123"
AGENCY_ADMIN_EMAIL = "agency1@demo.test"
AGENCY_ADMIN_PASSWORD = "agency123"


class TestAuthAndSetup:
    """Authentication and setup tests."""

    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin authentication token."""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        assert resp.status_code == 200, f"Super admin login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data, f"No access_token in response: {data}"
        return data["access_token"]

    @pytest.fixture(scope="class")
    def agency_admin_token(self):
        """Get agency admin authentication token."""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": AGENCY_ADMIN_EMAIL, "password": AGENCY_ADMIN_PASSWORD}
        )
        assert resp.status_code == 200, f"Agency admin login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data, f"No access_token in response: {data}"
        return data["access_token"]

    def test_super_admin_login(self, super_admin_token):
        """Test super admin authentication."""
        assert super_admin_token is not None
        assert len(super_admin_token) > 20
        print(f"Super admin token: {super_admin_token[:30]}...")

    def test_agency_admin_login(self, agency_admin_token):
        """Test agency admin authentication."""
        assert agency_admin_token is not None
        assert len(agency_admin_token) > 20
        print(f"Agency admin token: {agency_admin_token[:30]}...")


class TestSupplierRevenueAnalytics:
    """Test GET /api/revenue/supplier-analytics endpoint."""

    @pytest.fixture(scope="class")
    def auth_header(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_supplier_analytics_returns_200(self, auth_header):
        """Test supplier analytics endpoint returns 200."""
        resp = requests.get(f"{BASE_URL}/api/revenue/supplier-analytics", headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "days" in data
        assert "suppliers" in data
        assert isinstance(data["suppliers"], list)
        print(f"Supplier analytics: {len(data['suppliers'])} suppliers, {data['days']} days")

    def test_supplier_analytics_with_days_param(self, auth_header):
        """Test supplier analytics with days parameter."""
        for days in [7, 30, 90]:
            resp = requests.get(f"{BASE_URL}/api/revenue/supplier-analytics?days={days}", headers=auth_header)
            assert resp.status_code == 200
            data = resp.json()
            assert data["days"] == days

    def test_supplier_analytics_structure(self, auth_header):
        """Test supplier analytics response structure."""
        resp = requests.get(f"{BASE_URL}/api/revenue/supplier-analytics", headers=auth_header)
        data = resp.json()
        # Structure is valid even if no suppliers exist
        assert isinstance(data["suppliers"], list)
        if data["suppliers"]:
            supplier = data["suppliers"][0]
            expected_keys = ["supplier_code", "total_bookings", "total_revenue", "avg_booking_value"]
            for key in expected_keys:
                assert key in supplier, f"Missing key: {key}"

    def test_supplier_analytics_unauthenticated(self):
        """Test supplier analytics without auth returns 401/403."""
        resp = requests.get(f"{BASE_URL}/api/revenue/supplier-analytics")
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"


class TestProfitabilityScores:
    """Test GET /api/revenue/profitability-scores endpoint."""

    @pytest.fixture(scope="class")
    def auth_header(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_profitability_scores_returns_200(self, auth_header):
        """Test profitability scores endpoint returns 200."""
        resp = requests.get(f"{BASE_URL}/api/revenue/profitability-scores", headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "days" in data
        assert "scores" in data
        assert isinstance(data["scores"], list)
        print(f"Profitability scores: {len(data['scores'])} suppliers")

    def test_profitability_scores_structure(self, auth_header):
        """Test profitability scores response structure with tiers."""
        resp = requests.get(f"{BASE_URL}/api/revenue/profitability-scores", headers=auth_header)
        data = resp.json()
        # Should return default scores when no booking data
        assert isinstance(data["scores"], list)
        if data["scores"]:
            score = data["scores"][0]
            assert "supplier_code" in score
            assert "profitability_score" in score
            assert "tier" in score
            assert score["tier"] in ["platinum", "gold", "silver", "bronze"]
            assert "components" in score
            assert "stats" in score
            print(f"First supplier: {score['supplier_code']}, tier: {score['tier']}, score: {score['profitability_score']}")

    def test_profitability_scores_components(self, auth_header):
        """Test profitability scores have required components."""
        resp = requests.get(f"{BASE_URL}/api/revenue/profitability-scores", headers=auth_header)
        data = resp.json()
        if data["scores"]:
            components = data["scores"][0]["components"]
            expected = ["commission_margin", "success_rate", "fallback_frequency_inv", "latency_score", "cancellation_risk_inv"]
            for key in expected:
                assert key in components, f"Missing component: {key}"


class TestSupplierSelection:
    """Test POST /api/revenue/supplier-selection endpoint."""

    @pytest.fixture(scope="class")
    def auth_header(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_supplier_selection_returns_200(self, auth_header):
        """Test supplier selection endpoint returns 200."""
        payload = {
            "candidates": [
                {"supplier_code": "real_ratehawk", "price": 1000},
                {"supplier_code": "real_tbo", "price": 950},
                {"supplier_code": "real_paximum", "price": 1100}
            ],
            "destination": "Istanbul",
            "agency_tier": "standard"
        }
        resp = requests.post(f"{BASE_URL}/api/revenue/supplier-selection", json=payload, headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "ranked" in data
        assert "weights" in data
        assert "best_pick" in data
        print(f"Best pick: {data['best_pick']}")

    def test_supplier_selection_ranking_order(self, auth_header):
        """Test supplier selection returns sorted by total_score descending."""
        payload = {
            "candidates": [
                {"supplier_code": "real_ratehawk", "price": 1000},
                {"supplier_code": "real_tbo", "price": 950},
                {"supplier_code": "real_paximum", "price": 1100}
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/revenue/supplier-selection", json=payload, headers=auth_header)
        data = resp.json()
        ranked = data["ranked"]
        assert len(ranked) == 3
        # Verify sorted by total_score descending
        scores = [r["total_score"] for r in ranked]
        assert scores == sorted(scores, reverse=True), "Ranking not sorted by score"

    def test_supplier_selection_empty_candidates(self, auth_header):
        """Test supplier selection with empty candidates."""
        payload = {"candidates": []}
        resp = requests.post(f"{BASE_URL}/api/revenue/supplier-selection", json=payload, headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ranked"] == []

    def test_supplier_selection_weight_components(self, auth_header):
        """Test supplier selection returns weight configuration."""
        payload = {
            "candidates": [{"supplier_code": "real_ratehawk", "price": 1000}]
        }
        resp = requests.post(f"{BASE_URL}/api/revenue/supplier-selection", json=payload, headers=auth_header)
        data = resp.json()
        weights = data["weights"]
        assert "price" in weights
        assert "reliability" in weights
        assert "profitability" in weights
        assert "preference" in weights
        # Weights should sum to 1.0
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected 1.0"


class TestCommissionSummary:
    """Test GET /api/revenue/commission-summary endpoint."""

    @pytest.fixture(scope="class")
    def auth_header(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_commission_summary_returns_200(self, auth_header):
        """Test commission summary endpoint returns 200."""
        resp = requests.get(f"{BASE_URL}/api/revenue/commission-summary", headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        expected_keys = ["total_supplier_cost", "total_sell_price", "total_platform_commission", 
                        "total_platform_markup", "total_agency_markup", "total_margin", "booking_count"]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"
        print(f"Commission summary: total_margin={data['total_margin']}, bookings={data['booking_count']}")


class TestMarkupRules:
    """Test markup rules CRUD endpoints."""

    @pytest.fixture(scope="class")
    def auth_header(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_get_markup_rules_returns_200(self, auth_header):
        """Test GET /api/revenue/markup-rules returns 200."""
        resp = requests.get(f"{BASE_URL}/api/revenue/markup-rules", headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)
        # Should have default rules
        print(f"Markup rules: {len(data['rules'])} rules")

    def test_markup_rules_structure(self, auth_header):
        """Test markup rules have required structure."""
        resp = requests.get(f"{BASE_URL}/api/revenue/markup-rules", headers=auth_header)
        data = resp.json()
        if data["rules"]:
            rule = data["rules"][0]
            expected = ["rule_id", "rule_type", "target", "markup_pct", "active"]
            for key in expected:
                assert key in rule, f"Missing key: {key}"

    def test_create_markup_rule(self, auth_header):
        """Test POST /api/revenue/markup-rules creates a new rule."""
        rule_id = f"test_rule_{int(time.time())}"
        payload = {
            "rule_id": rule_id,
            "rule_type": "destination",
            "target": "antalya",
            "markup_pct": 4.5,
            "max_pct": 12.0,
            "priority": 60,
            "active": True
        }
        resp = requests.post(f"{BASE_URL}/api/revenue/markup-rules", json=payload, headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "rule" in data
        assert data["rule"]["rule_id"] == rule_id
        assert data["rule"]["markup_pct"] == 4.5
        print(f"Created rule: {rule_id}")
        return rule_id

    def test_delete_markup_rule(self, auth_header):
        """Test DELETE /api/revenue/markup-rules/{rule_id} deactivates a rule."""
        # First create a rule to delete
        rule_id = f"test_delete_rule_{int(time.time())}"
        payload = {
            "rule_id": rule_id,
            "rule_type": "platform",
            "target": "all",
            "markup_pct": 2.0,
            "active": True
        }
        create_resp = requests.post(f"{BASE_URL}/api/revenue/markup-rules", json=payload, headers=auth_header)
        assert create_resp.status_code == 200

        # Now delete
        resp = requests.delete(f"{BASE_URL}/api/revenue/markup-rules/{rule_id}", headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data.get("deleted") == True
        print(f"Deleted rule: {rule_id}")

    def test_delete_nonexistent_rule(self, auth_header):
        """Test DELETE for nonexistent rule returns 404."""
        resp = requests.delete(f"{BASE_URL}/api/revenue/markup-rules/nonexistent_rule_xyz123", headers=auth_header)
        assert resp.status_code == 404


class TestCalculateMarkup:
    """Test POST /api/revenue/calculate-markup endpoint."""

    @pytest.fixture(scope="class")
    def auth_header(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_calculate_markup_returns_200(self, auth_header):
        """Test calculate markup endpoint returns 200."""
        payload = {
            "supplier_code": "real_ratehawk",
            "base_price": 1000.0,
            "destination": "istanbul",
            "agency_tier": "standard"
        }
        resp = requests.post(f"{BASE_URL}/api/revenue/calculate-markup", json=payload, headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "base_price" in data
        assert "total_markup" in data
        assert "final_price" in data
        assert "applied_rules" in data
        print(f"Markup calculation: base={data['base_price']}, markup={data['total_markup']}, final={data['final_price']}")

    def test_calculate_markup_applies_rules(self, auth_header):
        """Test calculate markup applies rules correctly."""
        payload = {
            "supplier_code": "real_ratehawk",
            "base_price": 1000.0,
            "destination": "dubai",  # Dubai has special rule
            "agency_tier": "vip"     # VIP tier has special rule
        }
        resp = requests.post(f"{BASE_URL}/api/revenue/calculate-markup", json=payload, headers=auth_header)
        data = resp.json()
        # Final price should be >= base price
        assert data["final_price"] >= data["base_price"]
        assert isinstance(data["applied_rules"], list)


class TestSupplierEconomics:
    """Test GET /api/revenue/supplier-economics endpoint."""

    @pytest.fixture(scope="class")
    def auth_header(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_supplier_economics_returns_200(self, auth_header):
        """Test supplier economics endpoint returns 200."""
        resp = requests.get(f"{BASE_URL}/api/revenue/supplier-economics", headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "days" in data
        assert "economics" in data
        assert isinstance(data["economics"], list)
        print(f"Supplier economics: {len(data['economics'])} suppliers")

    def test_supplier_economics_structure(self, auth_header):
        """Test supplier economics has combined revenue+profitability+performance."""
        resp = requests.get(f"{BASE_URL}/api/revenue/supplier-economics", headers=auth_header)
        data = resp.json()
        if data["economics"]:
            econ = data["economics"][0]
            assert "supplier_code" in econ
            assert "revenue" in econ
            assert "profitability" in econ
            assert "performance" in econ
            # Revenue structure
            assert "total_revenue" in econ["revenue"]
            # Profitability structure
            assert "score" in econ["profitability"]
            assert "tier" in econ["profitability"]
            # Performance structure
            assert "score" in econ["performance"]


class TestAgencyAnalytics:
    """Test GET /api/revenue/agency-analytics endpoint."""

    @pytest.fixture(scope="class")
    def auth_header(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_agency_analytics_returns_200(self, auth_header):
        """Test agency analytics endpoint returns 200."""
        resp = requests.get(f"{BASE_URL}/api/revenue/agency-analytics", headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "days" in data
        assert "agencies" in data
        assert isinstance(data["agencies"], list)
        print(f"Agency analytics: {len(data['agencies'])} agencies")

    def test_agency_analytics_structure(self, auth_header):
        """Test agency analytics response structure."""
        resp = requests.get(f"{BASE_URL}/api/revenue/agency-analytics", headers=auth_header)
        data = resp.json()
        if data["agencies"]:
            agency = data["agencies"][0]
            expected = ["organization_id", "total_bookings", "total_revenue", "avg_booking_value", "preferred_suppliers"]
            for key in expected:
                assert key in agency, f"Missing key: {key}"


class TestRevenueForecast:
    """Test GET /api/revenue/forecast endpoint."""

    @pytest.fixture(scope="class")
    def auth_header(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_forecast_returns_200(self, auth_header):
        """Test revenue forecast endpoint returns 200."""
        resp = requests.get(f"{BASE_URL}/api/revenue/forecast", headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "historical" in data
        assert "revenue_forecast" in data
        assert "booking_forecast" in data
        assert "forecast_months" in data
        print(f"Forecast: {data['forecast_months']} months, {len(data['revenue_forecast'])} predictions")

    def test_forecast_with_months_param(self, auth_header):
        """Test forecast with months parameter."""
        resp = requests.get(f"{BASE_URL}/api/revenue/forecast?months=6", headers=auth_header)
        data = resp.json()
        assert data["forecast_months"] == 6
        assert len(data["revenue_forecast"]) == 6
        assert len(data["booking_forecast"]) == 6

    def test_forecast_structure(self, auth_header):
        """Test forecast response structure."""
        resp = requests.get(f"{BASE_URL}/api/revenue/forecast", headers=auth_header)
        data = resp.json()
        if data["revenue_forecast"]:
            forecast = data["revenue_forecast"][0]
            assert "period" in forecast
            assert "predicted" in forecast
            assert "confidence" in forecast
            assert forecast["confidence"] in ["high", "medium", "low"]


class TestBusinessKPI:
    """Test GET /api/revenue/business-kpi endpoint."""

    @pytest.fixture(scope="class")
    def auth_header(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_business_kpi_returns_200(self, auth_header):
        """Test business KPI endpoint returns 200."""
        resp = requests.get(f"{BASE_URL}/api/revenue/business-kpi", headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "days" in data
        assert "gmv" in data
        assert "commission" in data
        assert "funnel" in data
        assert "top_suppliers" in data
        assert "profitability" in data
        assert "top_destinations" in data
        print(f"Business KPI: GMV={data['gmv'].get('gmv', 0)}, bookings={data['gmv'].get('total_bookings', 0)}")

    def test_business_kpi_gmv_structure(self, auth_header):
        """Test business KPI GMV structure."""
        resp = requests.get(f"{BASE_URL}/api/revenue/business-kpi", headers=auth_header)
        data = resp.json()
        gmv = data["gmv"]
        expected = ["gmv", "total_bookings", "avg_booking_value", "unique_agencies", "unique_suppliers"]
        for key in expected:
            assert key in gmv, f"Missing GMV key: {key}"

    def test_business_kpi_commission_structure(self, auth_header):
        """Test business KPI commission structure."""
        resp = requests.get(f"{BASE_URL}/api/revenue/business-kpi", headers=auth_header)
        data = resp.json()
        commission = data["commission"]
        expected = ["total_supplier_cost", "total_sell_price", "total_platform_commission", "total_margin"]
        for key in expected:
            assert key in commission, f"Missing commission key: {key}"


class TestDestinationRevenue:
    """Test GET /api/revenue/destination-revenue endpoint."""

    @pytest.fixture(scope="class")
    def auth_header(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_destination_revenue_returns_200(self, auth_header):
        """Test destination revenue endpoint returns 200."""
        resp = requests.get(f"{BASE_URL}/api/revenue/destination-revenue", headers=auth_header)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "days" in data
        assert "destinations" in data
        assert isinstance(data["destinations"], list)
        print(f"Destination revenue: {len(data['destinations'])} destinations")

    def test_destination_revenue_with_limit(self, auth_header):
        """Test destination revenue with limit parameter."""
        resp = requests.get(f"{BASE_URL}/api/revenue/destination-revenue?limit=5", headers=auth_header)
        data = resp.json()
        assert len(data["destinations"]) <= 5

    def test_destination_revenue_structure(self, auth_header):
        """Test destination revenue response structure."""
        resp = requests.get(f"{BASE_URL}/api/revenue/destination-revenue", headers=auth_header)
        data = resp.json()
        if data["destinations"]:
            dest = data["destinations"][0]
            assert "destination" in dest
            assert "search_count" in dest


class TestAuthorizationRestrictions:
    """Test that all revenue endpoints require admin/super_admin role."""

    def test_all_endpoints_require_auth(self):
        """Test all revenue endpoints return 401/403 without auth."""
        endpoints = [
            ("GET", "/api/revenue/supplier-analytics"),
            ("GET", "/api/revenue/profitability-scores"),
            ("POST", "/api/revenue/supplier-selection"),
            ("GET", "/api/revenue/commission-summary"),
            ("GET", "/api/revenue/markup-rules"),
            ("POST", "/api/revenue/markup-rules"),
            ("DELETE", "/api/revenue/markup-rules/test"),
            ("POST", "/api/revenue/calculate-markup"),
            ("GET", "/api/revenue/supplier-economics"),
            ("GET", "/api/revenue/agency-analytics"),
            ("GET", "/api/revenue/forecast"),
            ("GET", "/api/revenue/business-kpi"),
            ("GET", "/api/revenue/destination-revenue"),
        ]
        
        for method, endpoint in endpoints:
            url = f"{BASE_URL}{endpoint}"
            if method == "GET":
                resp = requests.get(url)
            elif method == "POST":
                resp = requests.post(url, json={})
            elif method == "DELETE":
                resp = requests.delete(url)
            
            assert resp.status_code in [401, 403], f"{method} {endpoint} should require auth, got {resp.status_code}"
            print(f"{method} {endpoint} - correctly requires auth (status: {resp.status_code})")


class TestAgencyAdminAccess:
    """Test that agency admin can access supplier selection and markup calculation."""

    @pytest.fixture(scope="class")
    def agency_header(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": AGENCY_ADMIN_EMAIL, "password": AGENCY_ADMIN_PASSWORD}
        )
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_agency_can_access_supplier_selection(self, agency_header):
        """Test agency admin can access supplier selection (has agency_admin role allowed)."""
        payload = {
            "candidates": [{"supplier_code": "real_ratehawk", "price": 1000}]
        }
        resp = requests.post(f"{BASE_URL}/api/revenue/supplier-selection", json=payload, headers=agency_header)
        assert resp.status_code == 200, f"Agency should have access, got {resp.status_code}: {resp.text}"

    def test_agency_can_access_calculate_markup(self, agency_header):
        """Test agency admin can access calculate markup (has agency_admin role allowed)."""
        payload = {
            "supplier_code": "real_ratehawk",
            "base_price": 1000.0
        }
        resp = requests.post(f"{BASE_URL}/api/revenue/calculate-markup", json=payload, headers=agency_header)
        assert resp.status_code == 200, f"Agency should have access, got {resp.status_code}: {resp.text}"

    def test_agency_cannot_access_admin_only_endpoints(self, agency_header):
        """Test agency admin cannot access admin-only endpoints."""
        # These endpoints require admin/super_admin only
        admin_only = [
            ("GET", "/api/revenue/supplier-analytics"),
            ("GET", "/api/revenue/commission-summary"),
            ("GET", "/api/revenue/markup-rules"),
            ("GET", "/api/revenue/supplier-economics"),
            ("GET", "/api/revenue/agency-analytics"),
            ("GET", "/api/revenue/forecast"),
            ("GET", "/api/revenue/business-kpi"),
            ("GET", "/api/revenue/destination-revenue"),
        ]
        
        for method, endpoint in admin_only:
            url = f"{BASE_URL}{endpoint}"
            resp = requests.get(url, headers=agency_header)
            assert resp.status_code in [401, 403], f"Agency should NOT have access to {endpoint}, got {resp.status_code}"
            print(f"Agency correctly denied access to {endpoint}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
