"""Test Operations & Launch Readiness APIs (MEGA PROMPT #27).

Tests all /api/operations/* endpoints:
- Supplier Capability Matrix
- Supplier Validation Framework
- Performance Validation (cache burst, rate limit, fallback)
- Reconciliation Validation
- Monitoring Validation
- Launch Readiness Report
- Agency Onboarding Checklist
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# ==================== FIXTURES ====================

@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for super admin."""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"},
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json().get("access_token")
    pytest.fail(f"Login failed: {resp.status_code} - {resp.text[:200]}")

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return authorization headers."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

# ==================== CAPABILITY MATRIX TESTS ====================

class TestCapabilityMatrix:
    """Test /api/operations/capability-matrix endpoint."""
    
    def test_capability_matrix_returns_4_suppliers(self, auth_headers):
        """GET /api/operations/capability-matrix returns 4 suppliers with capability flags."""
        resp = requests.get(f"{BASE_URL}/api/operations/capability-matrix", headers=auth_headers, timeout=15)
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify structure
        assert "matrix" in data, "Response should contain 'matrix' key"
        assert "total_suppliers" in data, "Response should contain 'total_suppliers' key"
        assert data["total_suppliers"] == 4, f"Expected 4 suppliers, got {data['total_suppliers']}"
        
        # Verify all 4 suppliers
        supplier_codes = [s["supplier_code"] for s in data["matrix"]]
        expected_suppliers = ["ratehawk", "tbo", "paximum", "wwtatil"]
        for sup in expected_suppliers:
            assert sup in supplier_codes, f"Missing supplier: {sup}"
        
    def test_capability_matrix_has_all_flags(self, auth_headers):
        """Each supplier should have all capability flags."""
        resp = requests.get(f"{BASE_URL}/api/operations/capability-matrix", headers=auth_headers, timeout=15)
        assert resp.status_code == 200
        data = resp.json()
        
        required_flags = ["search", "price_check", "hold", "booking", "cancel", "sandbox_available"]
        for supplier in data["matrix"]:
            for flag in required_flags:
                assert flag in supplier, f"Supplier {supplier['supplier_code']} missing flag: {flag}"
                assert isinstance(supplier[flag], bool), f"Flag {flag} should be boolean"
    
    def test_capability_matrix_unauthorized(self):
        """GET /api/operations/capability-matrix without auth should return 401/403."""
        resp = requests.get(f"{BASE_URL}/api/operations/capability-matrix", timeout=15)
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"

# ==================== SUPPLIER VALIDATION TESTS ====================

class TestSupplierValidation:
    """Test /api/operations/validate-supplier and validate-all endpoints."""
    
    def test_validate_single_supplier_ratehawk(self, auth_headers):
        """POST /api/operations/validate-supplier with ratehawk returns validation report."""
        resp = requests.post(
            f"{BASE_URL}/api/operations/validate-supplier",
            headers=auth_headers,
            json={"supplier_code": "ratehawk"},
            timeout=30,
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify report structure
        assert "supplier_code" in data, "Response should contain 'supplier_code'"
        assert data["supplier_code"] == "ratehawk"
        assert "steps" in data, "Response should contain 'steps' array"
        assert "overall_status" in data, "Response should contain 'overall_status'"
        assert "duration_ms" in data or "timestamp" in data, "Response should have timing info"
        
    def test_validate_single_supplier_tbo(self, auth_headers):
        """POST /api/operations/validate-supplier with tbo returns validation report."""
        resp = requests.post(
            f"{BASE_URL}/api/operations/validate-supplier",
            headers=auth_headers,
            json={"supplier_code": "tbo"},
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["supplier_code"] == "tbo"
        assert "overall_status" in data
        
    def test_validate_all_suppliers(self, auth_headers):
        """POST /api/operations/validate-all validates all 4 suppliers."""
        resp = requests.post(
            f"{BASE_URL}/api/operations/validate-all",
            headers=auth_headers,
            json={},
            timeout=60,
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        
        # Verify structure
        assert "suppliers" in data, "Response should contain 'suppliers' dict"
        assert "summary" in data, "Response should contain 'summary' dict"
        
        # Verify all 4 suppliers validated
        supplier_codes = list(data["suppliers"].keys())
        expected = ["ratehawk", "tbo", "paximum", "wwtatil"]
        for sup in expected:
            assert sup in supplier_codes, f"Missing supplier validation: {sup}"
            
        # Summary should have status for each supplier
        for sup in expected:
            assert sup in data["summary"], f"Summary missing status for: {sup}"
    
    def test_validate_unknown_supplier(self, auth_headers):
        """POST /api/operations/validate-supplier with unknown supplier returns error."""
        resp = requests.post(
            f"{BASE_URL}/api/operations/validate-supplier",
            headers=auth_headers,
            json={"supplier_code": "unknown_supplier"},
            timeout=15,
        )
        assert resp.status_code == 200  # Still 200 but with error in body
        data = resp.json()
        assert data.get("overall_status") == "error" or "error" in data

# ==================== PERFORMANCE TESTS ====================

class TestPerformanceValidation:
    """Test cache burst, rate limit, and fallback validation endpoints."""
    
    def test_cache_burst_test(self, auth_headers):
        """POST /api/operations/cache-burst-test returns hit/miss summary."""
        resp = requests.post(
            f"{BASE_URL}/api/operations/cache-burst-test",
            headers=auth_headers,
            json={"burst_count": 5},
            timeout=30,
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify structure
        assert "test" in data and data["test"] == "cache_burst"
        assert "burst_count" in data and data["burst_count"] == 5
        assert "results" in data, "Response should contain 'results' array"
        assert "summary" in data, "Response should contain 'summary'"
        
        # Verify summary fields
        summary = data["summary"]
        assert "cache_hits" in summary
        assert "cache_misses" in summary
        assert "hit_rate_pct" in summary
    
    def test_rate_limit_stress_test(self, auth_headers):
        """POST /api/operations/rate-limit-test returns allowed/rejected counts."""
        resp = requests.post(
            f"{BASE_URL}/api/operations/rate-limit-test",
            headers=auth_headers,
            json={"supplier_code": "ratehawk", "request_count": 10},
            timeout=30,
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify structure
        assert "test" in data and data["test"] == "rate_limit_stress"
        assert "supplier_code" in data and data["supplier_code"] == "ratehawk"
        assert "request_count" in data
        assert "results" in data
        assert "summary" in data
        
        # Verify summary
        summary = data["summary"]
        assert "allowed" in summary
        assert "rejected" in summary
        assert "rejection_rate_pct" in summary
    
    def test_fallback_validation(self, auth_headers):
        """GET /api/operations/fallback-test returns 4 fallback scenarios."""
        resp = requests.get(
            f"{BASE_URL}/api/operations/fallback-test",
            headers=auth_headers,
            timeout=15,
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify structure
        assert "test" in data and data["test"] == "fallback_validation"
        assert "scenarios" in data, "Response should contain 'scenarios' array"
        assert "summary" in data
        
        # Verify 4 scenarios
        scenarios = data["scenarios"]
        assert len(scenarios) == 4, f"Expected 4 scenarios, got {len(scenarios)}"
        
        # Verify expected fallback chains
        primaries = [s["primary"] for s in scenarios]
        assert "ratehawk" in primaries
        assert "tbo" in primaries
        assert "paximum" in primaries
        assert "wwtatil" in primaries
        
        # Check all_chains_correct flag
        summary = data["summary"]
        assert "all_chains_correct" in summary
        assert summary["all_chains_correct"] == True, "All fallback chains should be correct"

# ==================== RECONCILIATION TESTS ====================

class TestReconciliationValidation:
    """Test /api/operations/reconciliation-test endpoint."""
    
    def test_reconciliation_test(self, auth_headers):
        """GET /api/operations/reconciliation-test returns reconciliation and commission stats."""
        resp = requests.get(
            f"{BASE_URL}/api/operations/reconciliation-test",
            headers=auth_headers,
            timeout=15,
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify structure
        assert "test" in data and data["test"] == "reconciliation_validation"
        assert "reconciliation" in data
        assert "bookings" in data
        assert "commission" in data
        assert "assessment" in data
        
        # Verify reconciliation fields
        recon = data["reconciliation"]
        assert "total_records" in recon
        assert "price_mismatches" in recon
        assert "status_mismatches" in recon
        assert "mismatch_rate_pct" in recon
        
        # Verify commission fields
        comm = data["commission"]
        assert "total_records" in comm
        assert "coverage_pct" in comm

# ==================== MONITORING TESTS ====================

class TestMonitoringValidation:
    """Test /api/operations/monitoring-test endpoint."""
    
    def test_monitoring_test(self, auth_headers):
        """GET /api/operations/monitoring-test returns monitoring checks."""
        resp = requests.get(
            f"{BASE_URL}/api/operations/monitoring-test",
            headers=auth_headers,
            timeout=15,
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify structure
        assert "test" in data and data["test"] == "monitoring_validation"
        assert "checks" in data
        assert "summary" in data
        assert "details" in data
        
        # Verify expected checks
        checks = data["checks"]
        expected_checks = ["redis_healthy", "scheduler_running", "jobs_configured"]
        for check in expected_checks:
            assert check in checks, f"Missing check: {check}"
        
        # Verify summary
        summary = data["summary"]
        assert "passed" in summary
        assert "total" in summary
        assert "score_pct" in summary

# ==================== LAUNCH READINESS TESTS ====================

class TestLaunchReadiness:
    """Test /api/operations/launch-readiness endpoint."""
    
    def test_launch_readiness_report(self, auth_headers):
        """GET /api/operations/launch-readiness returns full launch report."""
        resp = requests.get(
            f"{BASE_URL}/api/operations/launch-readiness",
            headers=auth_headers,
            timeout=30,
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        
        # Verify main structure
        assert "report_type" in data and data["report_type"] == "market_launch_readiness"
        assert "platform_maturity_score" in data
        assert "operational_risks" in data
        assert "launch_checklist" in data
        assert "key_metrics" in data
        
    def test_launch_readiness_maturity_score(self, auth_headers):
        """Launch report should have platform maturity score with dimensions."""
        resp = requests.get(f"{BASE_URL}/api/operations/launch-readiness", headers=auth_headers, timeout=30)
        assert resp.status_code == 200
        data = resp.json()
        
        ms = data["platform_maturity_score"]
        assert "overall" in ms, "Should have overall score"
        assert "dimensions" in ms, "Should have dimension scores"
        
        # Overall score should be between 0-10
        assert 0 <= ms["overall"] <= 10, f"Overall score {ms['overall']} should be 0-10"
        
        # Verify dimension scores
        dimensions = ms["dimensions"]
        expected_dimensions = ["supplier_integration", "booking_engine", "cache_performance", 
                              "fallback_reliability", "monitoring", "reconciliation", "revenue_tracking"]
        for dim in expected_dimensions:
            assert dim in dimensions, f"Missing dimension: {dim}"
            assert "score" in dimensions[dim]
            assert "status" in dimensions[dim]
    
    def test_launch_readiness_operational_risks(self, auth_headers):
        """Launch report should list operational risks."""
        resp = requests.get(f"{BASE_URL}/api/operations/launch-readiness", headers=auth_headers, timeout=30)
        assert resp.status_code == 200
        data = resp.json()
        
        risks = data["operational_risks"]
        assert isinstance(risks, list), "Risks should be a list"
        assert len(risks) > 0, "Should have at least 1 risk documented"
        
        # Verify risk structure
        for risk in risks:
            assert "id" in risk
            assert "severity" in risk
            assert "title" in risk
            assert "mitigation" in risk
    
    def test_launch_readiness_checklist(self, auth_headers):
        """Launch report should have checklist items."""
        resp = requests.get(f"{BASE_URL}/api/operations/launch-readiness", headers=auth_headers, timeout=30)
        assert resp.status_code == 200
        data = resp.json()
        
        checklist = data["launch_checklist"]
        assert isinstance(checklist, list)
        assert len(checklist) >= 5, f"Expected at least 5 checklist items, got {len(checklist)}"
        
        # Verify checklist item structure
        for item in checklist:
            assert "item" in item
            assert "priority" in item
            assert "status" in item
    
    def test_launch_readiness_key_metrics(self, auth_headers):
        """Launch report should have key metrics."""
        resp = requests.get(f"{BASE_URL}/api/operations/launch-readiness", headers=auth_headers, timeout=30)
        assert resp.status_code == 200
        data = resp.json()
        
        metrics = data["key_metrics"]
        expected_metrics = ["supplier_success_rate", "cache_hit_rate_pct", "monitoring_score_pct"]
        for m in expected_metrics:
            assert m in metrics, f"Missing key metric: {m}"

# ==================== ONBOARDING CHECKLIST TESTS ====================

class TestOnboardingChecklist:
    """Test /api/operations/onboarding-checklist endpoint."""
    
    def test_onboarding_checklist_returns_6_steps(self, auth_headers):
        """GET /api/operations/onboarding-checklist returns 6-step onboarding flow."""
        resp = requests.get(
            f"{BASE_URL}/api/operations/onboarding-checklist",
            headers=auth_headers,
            timeout=15,
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify structure
        assert "checklist" in data
        assert "estimated_time_minutes" in data
        assert "prerequisites" in data
        
        # Verify 6 steps
        checklist = data["checklist"]
        assert len(checklist) == 6, f"Expected 6 steps, got {len(checklist)}"
        
        # Verify step structure
        for step in checklist:
            assert "step" in step
            assert "title" in step
            assert "description" in step
            assert "endpoint" in step
            assert "status" in step

# ==================== SUPPLIER SLA TESTS ====================

class TestSupplierSLA:
    """Test /api/operations/supplier-sla endpoint."""
    
    def test_supplier_sla_metrics(self, auth_headers):
        """GET /api/operations/supplier-sla returns SLA metrics for all suppliers."""
        resp = requests.get(
            f"{BASE_URL}/api/operations/supplier-sla",
            headers=auth_headers,
            timeout=15,
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify structure
        assert "sla_metrics" in data
        assert "timestamp" in data
        
        # Verify SLA for all 4 suppliers
        sla = data["sla_metrics"]
        expected_suppliers = ["ratehawk", "tbo", "paximum", "wwtatil"]
        for sup in expected_suppliers:
            assert sup in sla, f"Missing SLA for supplier: {sup}"
            
            # Verify metric fields
            metrics = sla[sup]
            assert "supplier_code" in metrics
            assert "display_name" in metrics
            assert "search_count" in metrics
            assert "avg_search_latency_ms" in metrics
            assert "booking_success_rate_pct" in metrics
            assert "circuit_state" in metrics

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
