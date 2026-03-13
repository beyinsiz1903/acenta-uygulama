"""
Test Suite for Supplier Activation Feature - Iteration 76
Tests all 10 parts of the Supplier Activation Engine:
  Part 1  — Activation Plan
  Part 2  — Shadow Traffic
  Part 3  — Canary Deployment
  Part 4  — Response Normalization
  Part 5  — Failover Strategy
  Part 6  — Rate Limit Management
  Part 7  — Health Monitoring
  Part 8  — Incident Handling
  Part 9  — Traffic Analysis
  Part 10 — Activation Score & Dashboard
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

class TestSupplierActivationBackend:
    """Backend tests for Supplier Activation feature (16 endpoints)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200, f"Auth failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Auth headers for requests"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }

    # ========== DASHBOARD (Combined) ==========
    def test_dashboard_returns_activation_data(self, headers):
        """GET /api/supplier-activation/dashboard - returns all dashboard data"""
        response = requests.get(f"{BASE_URL}/api/supplier-activation/dashboard", headers=headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        
        data = response.json()
        # Verify required fields
        assert "activation_score" in data, "Missing activation_score"
        assert "meets_target" in data, "Missing meets_target"
        assert "target" in data, "Missing target"
        assert "suppliers" in data, "Missing suppliers"
        assert "health_summary" in data, "Missing health_summary"
        
        # Verify activation score is a valid number
        assert isinstance(data["activation_score"], (int, float)), "activation_score should be numeric"
        assert 0 <= data["activation_score"] <= 10, "activation_score should be 0-10"
        
        # Verify suppliers list
        assert len(data["suppliers"]) == 3, "Should have 3 suppliers"
        supplier_codes = [s["code"] for s in data["suppliers"]]
        assert "paximum" in supplier_codes, "Missing paximum supplier"
        assert "aviationstack" in supplier_codes, "Missing aviationstack supplier"
        assert "amadeus" in supplier_codes, "Missing amadeus supplier"
        
        print(f"PASS: Dashboard - score={data['activation_score']}, meets_target={data['meets_target']}")

    # ========== PART 1: Activation Plan ==========
    def test_activation_plan_returns_3_suppliers(self, headers):
        """GET /api/supplier-activation/plan - returns 3 suppliers with auth, rate limits, endpoints"""
        response = requests.get(f"{BASE_URL}/api/supplier-activation/plan", headers=headers)
        assert response.status_code == 200, f"Plan failed: {response.text}"
        
        data = response.json()
        assert "suppliers" in data, "Missing suppliers"
        assert "total_suppliers" in data, "Missing total_suppliers"
        assert data["total_suppliers"] == 3, f"Expected 3 suppliers, got {data['total_suppliers']}"
        
        # Verify each supplier has required fields
        for supplier in data["suppliers"]:
            assert "code" in supplier, "Missing supplier code"
            assert "auth" in supplier, "Missing auth config"
            assert "rate_limits" in supplier, "Missing rate_limits"
            assert "endpoints" in supplier, "Missing endpoints"
            assert "sandbox" in supplier["endpoints"], "Missing sandbox endpoint"
            assert "production" in supplier["endpoints"], "Missing production endpoint"
            
        print(f"PASS: Activation Plan - {data['total_suppliers']} suppliers configured")

    # ========== PART 2: Shadow Traffic ==========
    def test_shadow_traffic_paximum(self, headers):
        """POST /api/supplier-activation/shadow/paximum - runs shadow traffic comparison"""
        response = requests.post(f"{BASE_URL}/api/supplier-activation/shadow/paximum", headers=headers)
        assert response.status_code == 200, f"Shadow failed: {response.text}"
        
        data = response.json()
        assert "supplier_code" in data, "Missing supplier_code"
        assert data["supplier_code"] == "paximum", "Wrong supplier"
        assert "success_rate_pct" in data, "Missing success_rate_pct"
        assert "avg_latency_ms" in data, "Missing avg_latency_ms"
        assert "comparisons" in data, "Missing comparisons"
        assert "verdict" in data, "Missing verdict"
        
        print(f"PASS: Shadow Traffic Paximum - success={data['success_rate_pct']}%, verdict={data['verdict']}")

    def test_shadow_traffic_aviationstack(self, headers):
        """POST /api/supplier-activation/shadow/aviationstack"""
        response = requests.post(f"{BASE_URL}/api/supplier-activation/shadow/aviationstack", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["supplier_code"] == "aviationstack"
        print(f"PASS: Shadow Traffic AviationStack - verdict={data['verdict']}")

    def test_shadow_traffic_amadeus(self, headers):
        """POST /api/supplier-activation/shadow/amadeus"""
        response = requests.post(f"{BASE_URL}/api/supplier-activation/shadow/amadeus", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["supplier_code"] == "amadeus"
        print(f"PASS: Shadow Traffic Amadeus - verdict={data['verdict']}")

    # ========== PART 3: Canary Deployment ==========
    def test_canary_status_returns_3_configs(self, headers):
        """GET /api/supplier-activation/canary - returns canary configs for 3 suppliers"""
        response = requests.get(f"{BASE_URL}/api/supplier-activation/canary", headers=headers)
        assert response.status_code == 200, f"Canary failed: {response.text}"
        
        data = response.json()
        assert "canary_configs" in data, "Missing canary_configs"
        assert len(data["canary_configs"]) == 3, f"Expected 3 configs, got {len(data['canary_configs'])}"
        
        for config in data["canary_configs"]:
            assert "supplier_code" in config
            assert "enabled" in config
            assert "traffic_pct" in config
            assert "max_pct" in config
            
        print(f"PASS: Canary Status - {data['total']} configs returned")

    def test_canary_enable_paximum(self, headers):
        """POST /api/supplier-activation/canary/paximum/enable - enables canary for paximum"""
        response = requests.post(f"{BASE_URL}/api/supplier-activation/canary/paximum/enable", headers=headers)
        assert response.status_code == 200, f"Enable failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "enabled", f"Expected enabled, got {data['status']}"
        assert data["supplier_code"] == "paximum"
        assert data["traffic_pct"] == 5, "Initial traffic should be 5%"
        
        print(f"PASS: Canary Enable Paximum - traffic_pct={data['traffic_pct']}%")

    def test_canary_promote_paximum(self, headers):
        """POST /api/supplier-activation/canary/paximum/promote - promotes canary traffic %"""
        response = requests.post(f"{BASE_URL}/api/supplier-activation/canary/paximum/promote", headers=headers)
        assert response.status_code == 200, f"Promote failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "promoted", f"Expected promoted, got {data['status']}"
        assert data["traffic_pct"] == 10, "Traffic should increase by step (5% -> 10%)"
        
        print(f"PASS: Canary Promote Paximum - traffic_pct={data['traffic_pct']}%")

    def test_canary_rollback_paximum(self, headers):
        """POST /api/supplier-activation/canary/paximum/rollback - rolls back canary"""
        response = requests.post(f"{BASE_URL}/api/supplier-activation/canary/paximum/rollback", headers=headers)
        assert response.status_code == 200, f"Rollback failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "rolled_back", f"Expected rolled_back, got {data['status']}"
        assert data["traffic_pct"] == 0, "Traffic should be 0% after rollback"
        
        print(f"PASS: Canary Rollback Paximum - traffic_pct={data['traffic_pct']}%")

    # ========== PART 4: Response Normalization ==========
    def test_normalization_paximum(self, headers):
        """POST /api/supplier-activation/normalization/paximum - tests response normalization"""
        response = requests.post(f"{BASE_URL}/api/supplier-activation/normalization/paximum", headers=headers)
        assert response.status_code == 200, f"Normalization failed: {response.text}"
        
        data = response.json()
        assert "supplier_code" in data
        assert "rules" in data
        assert "conformance_pct" in data
        assert "verdict" in data
        
        print(f"PASS: Normalization Paximum - conformance={data['conformance_pct']}%, verdict={data['verdict']}")

    # ========== PART 5: Failover Strategy ==========
    def test_failover_status_returns_chains(self, headers):
        """GET /api/supplier-activation/failover - returns failover chains"""
        response = requests.get(f"{BASE_URL}/api/supplier-activation/failover", headers=headers)
        assert response.status_code == 200, f"Failover failed: {response.text}"
        
        data = response.json()
        assert "failover_chains" in data
        assert len(data["failover_chains"]) == 3
        
        for chain in data["failover_chains"]:
            assert "primary" in chain
            assert "fallbacks" in chain
            assert "circuit_breaker" in chain
            
        print(f"PASS: Failover Status - {data['total']} chains configured")

    def test_failover_simulate_paximum(self, headers):
        """POST /api/supplier-activation/failover/paximum/simulate - simulates failover"""
        response = requests.post(f"{BASE_URL}/api/supplier-activation/failover/paximum/simulate", headers=headers)
        assert response.status_code == 200, f"Failover sim failed: {response.text}"
        
        data = response.json()
        assert "supplier_code" in data
        assert "steps" in data
        assert "verdict" in data
        assert data["primary_failed"] == True
        assert data["circuit_breaker_triggered"] == True
        
        print(f"PASS: Failover Simulate Paximum - verdict={data['verdict']}, steps={len(data['steps'])}")

    # ========== PART 6: Rate Limit Management ==========
    def test_rate_limits_returns_token_bucket_state(self, headers):
        """GET /api/supplier-activation/rate-limits - returns token bucket state"""
        response = requests.get(f"{BASE_URL}/api/supplier-activation/rate-limits", headers=headers)
        assert response.status_code == 200, f"Rate limits failed: {response.text}"
        
        data = response.json()
        assert "rate_limiters" in data
        assert len(data["rate_limiters"]) == 3
        
        for limiter in data["rate_limiters"]:
            assert "supplier_code" in limiter
            assert "bucket" in limiter
            assert "adaptive_throttling" in limiter
            
        print(f"PASS: Rate Limits - {data['total']} limiters configured")

    def test_rate_limit_simulate_paximum(self, headers):
        """POST /api/supplier-activation/rate-limits/paximum/simulate?requests_count=100"""
        response = requests.post(
            f"{BASE_URL}/api/supplier-activation/rate-limits/paximum/simulate?requests_count=100",
            headers=headers
        )
        assert response.status_code == 200, f"Rate limit sim failed: {response.text}"
        
        data = response.json()
        assert "supplier_code" in data
        assert "total_requests" in data
        assert "allowed" in data
        assert "throttled" in data
        assert "verdict" in data
        
        print(f"PASS: Rate Limit Simulate - allowed={data['allowed']}, throttled={data['throttled']}")

    # ========== PART 7: Health Monitoring ==========
    def test_health_returns_all_suppliers(self, headers):
        """GET /api/supplier-activation/health - returns health for all 3 suppliers"""
        response = requests.get(f"{BASE_URL}/api/supplier-activation/health", headers=headers)
        assert response.status_code == 200, f"Health failed: {response.text}"
        
        data = response.json()
        assert "suppliers" in data
        assert len(data["suppliers"]) == 3
        
        for supplier in data["suppliers"]:
            assert "supplier_code" in supplier
            assert "health_state" in supplier
            assert "health_score" in supplier
            assert "metrics" in supplier
            
        print(f"PASS: Health Monitoring - {data['total']} suppliers monitored")

    # ========== PART 8: Incident Handling ==========
    def test_incident_simulate_paximum(self, headers):
        """POST /api/supplier-activation/incident/paximum - simulates incident detection"""
        response = requests.post(f"{BASE_URL}/api/supplier-activation/incident/paximum", headers=headers)
        assert response.status_code == 200, f"Incident failed: {response.text}"
        
        data = response.json()
        assert "supplier_code" in data
        assert "outage_detected" in data
        assert "steps" in data
        assert "verdict" in data
        
        print(f"PASS: Incident Simulate - outage={data['outage_detected']}, verdict={data['verdict']}")

    # ========== PART 9: Traffic Analysis ==========
    def test_traffic_analysis_returns_rates(self, headers):
        """GET /api/supplier-activation/traffic-analysis - returns conversion and booking rates"""
        response = requests.get(f"{BASE_URL}/api/supplier-activation/traffic-analysis", headers=headers)
        assert response.status_code == 200, f"Traffic failed: {response.text}"
        
        data = response.json()
        assert "suppliers" in data
        assert len(data["suppliers"]) == 3
        
        for supplier in data["suppliers"]:
            assert "funnel" in supplier
            assert "rates" in supplier
            assert "revenue" in supplier
            
        print(f"PASS: Traffic Analysis - {data['total']} suppliers analyzed")

    # ========== PART 10: Activation Score ==========
    def test_activation_score_meets_target(self, headers):
        """GET /api/supplier-activation/score - returns activation score >= 9.5"""
        response = requests.get(f"{BASE_URL}/api/supplier-activation/score", headers=headers)
        assert response.status_code == 200, f"Score failed: {response.text}"
        
        data = response.json()
        assert "activation_score" in data
        assert "target" in data
        assert "meets_target" in data
        assert "score_components" in data
        assert "deployment_checklist" in data
        
        # Verify score is reasonable
        assert isinstance(data["activation_score"], (int, float))
        assert data["target"] == 9.5, f"Target should be 9.5, got {data['target']}"
        
        print(f"PASS: Activation Score - score={data['activation_score']}, target={data['target']}, meets_target={data['meets_target']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
