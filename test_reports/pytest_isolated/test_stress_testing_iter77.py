"""
Stress Testing API - Iteration 77
Tests all 10 parts of the stress testing engine:
Part 1: Load Testing (10k searches/hr, 1k bookings/hr)
Part 2: Queue Stress (5k jobs, autoscaling)
Part 3: Supplier Outage (failover, fallback)
Part 4: Payment Failure (retry, incident logging)
Part 5: Cache Failure (Redis degradation)
Part 6: Database Stress (query latency, index)
Part 7: Incident Response (supplier outage, queue overload)
Part 8: Tenant Safety (no cross-tenant access)
Part 9: Performance Metrics (P95, error rate, queue depth)
Part 10: Stress Test Report (bottlenecks, capacity, readiness score)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestAuth:
    """Authentication tests - get token for subsequent tests."""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token using super admin credentials."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        # Auth uses access_token field
        token = data.get("access_token") or data.get("token")
        assert token, f"No token in response: {data}"
        return token

    def test_auth_login(self, auth_token):
        """Verify authentication works."""
        assert auth_token is not None
        print(f"Auth token obtained: {auth_token[:20]}...")


class TestStressTestAPIs:
    """Test all 10 stress test API endpoints."""

    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for all stress test API calls."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200
        data = response.json()
        token = data.get("access_token") or data.get("token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # ==================== PART 1: LOAD TESTING ====================
    def test_load_testing_endpoint(self, auth_headers):
        """Part 1: POST /api/stress-test/load - Load testing 10k searches/hr, 1k bookings/hr."""
        response = requests.post(f"{BASE_URL}/api/stress-test/load", headers=auth_headers)
        assert response.status_code == 200, f"Load test failed: {response.status_code} - {response.text}"
        
        data = response.json()
        # Verify verdict
        assert "verdict" in data, f"Missing verdict: {data}"
        assert data["verdict"] in ["PASS", "FAIL"], f"Invalid verdict: {data['verdict']}"
        
        # Verify api_latency
        assert "api_latency" in data, f"Missing api_latency: {data}"
        latency = data["api_latency"]
        assert "search_p95_ms" in latency
        assert "booking_p95_ms" in latency
        
        # Verify supplier_latency
        assert "supplier_latency" in data, f"Missing supplier_latency: {data}"
        suppliers = data["supplier_latency"]
        assert "paximum" in suppliers
        assert "aviationstack" in suppliers
        assert "amadeus" in suppliers
        
        # Verify worker_throughput
        assert "worker_throughput" in data, f"Missing worker_throughput: {data}"
        
        # Verify sla_check
        assert "sla_check" in data, f"Missing sla_check: {data}"
        sla = data["sla_check"]
        assert "search_p95_under_500ms" in sla
        assert "booking_p95_under_500ms" in sla
        
        print(f"Load Test - Verdict: {data['verdict']}, Search P95: {latency['search_p95_ms']}ms, Booking P95: {latency['booking_p95_ms']}ms")

    # ==================== PART 2: QUEUE STRESS ====================
    def test_queue_stress_endpoint(self, auth_headers):
        """Part 2: POST /api/stress-test/queue - Queue stress with 5k jobs and autoscaling."""
        response = requests.post(f"{BASE_URL}/api/stress-test/queue", headers=auth_headers)
        assert response.status_code == 200, f"Queue stress failed: {response.status_code} - {response.text}"
        
        data = response.json()
        # Verify verdict
        assert "verdict" in data
        assert data["verdict"] in ["PASS", "FAIL"]
        
        # Verify job_distribution
        assert "job_distribution" in data
        job_dist = data["job_distribution"]
        assert len(job_dist) > 0, "No job distribution data"
        
        # Verify autoscaling
        assert "autoscaling" in data
        autoscale = data["autoscaling"]
        assert "initial_workers" in autoscale
        assert "peak_workers" in autoscale
        assert "scale_up_triggered" in autoscale
        
        # Verify completion_rate_pct
        assert "completion_rate_pct" in data
        
        print(f"Queue Stress - Verdict: {data['verdict']}, Completion: {data['completion_rate_pct']}%, Peak Workers: {autoscale['peak_workers']}")

    # ==================== PART 3: SUPPLIER OUTAGE ====================
    def test_supplier_outage_paximum(self, auth_headers):
        """Part 3: POST /api/stress-test/supplier-outage/paximum - Paximum outage test."""
        response = requests.post(f"{BASE_URL}/api/stress-test/supplier-outage/paximum", headers=auth_headers)
        assert response.status_code == 200, f"Supplier outage failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "verdict" in data
        assert data["verdict"] in ["PASS", "FAIL"]
        
        # Verify failover_target
        assert "failover_target" in data
        assert data["failover_target"] == "amadeus"
        
        # Verify circuit_breaker
        assert "circuit_breaker" in data
        cb = data["circuit_breaker"]
        assert "state" in cb
        assert cb["state"] == "open"
        
        # Verify sla_check
        assert "sla_check" in data
        
        print(f"Supplier Outage (Paximum) - Verdict: {data['verdict']}, Failover: {data['failover_target']}, Circuit: {cb['state']}")

    def test_supplier_outage_aviationstack(self, auth_headers):
        """Part 3: POST /api/stress-test/supplier-outage/aviationstack - AviationStack outage test."""
        response = requests.post(f"{BASE_URL}/api/stress-test/supplier-outage/aviationstack", headers=auth_headers)
        assert response.status_code == 200, f"Supplier outage failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "verdict" in data
        assert "failover_target" in data
        assert data["failover_target"] == "paximum"
        
        print(f"Supplier Outage (AviationStack) - Verdict: {data['verdict']}, Failover: {data['failover_target']}")

    def test_supplier_outage_amadeus(self, auth_headers):
        """Part 3: POST /api/stress-test/supplier-outage/amadeus - Amadeus outage test."""
        response = requests.post(f"{BASE_URL}/api/stress-test/supplier-outage/amadeus", headers=auth_headers)
        assert response.status_code == 200, f"Supplier outage failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "verdict" in data
        assert "failover_target" in data
        assert data["failover_target"] == "paximum"
        
        print(f"Supplier Outage (Amadeus) - Verdict: {data['verdict']}, Failover: {data['failover_target']}")

    # ==================== PART 4: PAYMENT FAILURE ====================
    def test_payment_failure_endpoint(self, auth_headers):
        """Part 4: POST /api/stress-test/payment-failure - Payment failure with retry logic."""
        response = requests.post(f"{BASE_URL}/api/stress-test/payment-failure", headers=auth_headers)
        assert response.status_code == 200, f"Payment failure test failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "verdict" in data
        assert data["verdict"] in ["PASS", "FAIL"]
        
        # Verify failure_scenarios
        assert "failure_scenarios" in data
        scenarios = data["failure_scenarios"]
        assert len(scenarios) > 0, "No failure scenarios"
        
        # Verify retry_recovery_rate_pct
        assert "retry_recovery_rate_pct" in data
        
        print(f"Payment Failure - Verdict: {data['verdict']}, Recovery Rate: {data['retry_recovery_rate_pct']}%")

    # ==================== PART 5: CACHE FAILURE ====================
    def test_cache_failure_endpoint(self, auth_headers):
        """Part 5: POST /api/stress-test/cache-failure - Redis degradation test."""
        response = requests.post(f"{BASE_URL}/api/stress-test/cache-failure", headers=auth_headers)
        assert response.status_code == 200, f"Cache failure test failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "verdict" in data
        assert data["verdict"] in ["PASS", "FAIL"]
        
        # Verify phases (normal, disconnect, degraded, recovery)
        assert "phases" in data
        phases = data["phases"]
        assert len(phases) == 4, f"Expected 4 phases, got {len(phases)}"
        
        phase_names = [p["phase"] for p in phases]
        assert "normal" in phase_names
        assert "redis_disconnect" in phase_names
        assert "degraded" in phase_names
        assert "recovery" in phase_names
        
        print(f"Cache Failure - Verdict: {data['verdict']}, Phases: {phase_names}")

    # ==================== PART 6: DATABASE STRESS ====================
    def test_database_stress_endpoint(self, auth_headers):
        """Part 6: POST /api/stress-test/database - Database stress with query latency."""
        response = requests.post(f"{BASE_URL}/api/stress-test/database", headers=auth_headers)
        assert response.status_code == 200, f"DB stress test failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "verdict" in data
        assert data["verdict"] in ["PASS", "FAIL"]
        
        # Verify collections
        assert "collections" in data
        collections = data["collections"]
        assert len(collections) > 0, "No collection results"
        
        # Verify write_test
        assert "write_test" in data
        write = data["write_test"]
        assert "concurrent_writes" in write
        assert "completed" in write
        
        # Verify aggregation_test
        assert "aggregation_test" in data
        
        # Verify summary
        assert "summary" in data
        summary = data["summary"]
        assert "avg_query_latency_ms" in summary
        assert "index_coverage_pct" in summary
        
        print(f"DB Stress - Verdict: {data['verdict']}, Avg Query: {summary['avg_query_latency_ms']}ms, Index Coverage: {summary['index_coverage_pct']}%")

    # ==================== PART 7: INCIDENT RESPONSE ====================
    def test_incident_response_supplier_outage(self, auth_headers):
        """Part 7: POST /api/stress-test/incident/supplier_outage - Incident response test."""
        response = requests.post(f"{BASE_URL}/api/stress-test/incident/supplier_outage", headers=auth_headers)
        assert response.status_code == 200, f"Incident response failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "verdict" in data
        assert data["verdict"] in ["PASS", "FAIL"]
        
        # Verify steps
        assert "steps" in data
        steps = data["steps"]
        assert len(steps) > 0, "No incident steps"
        
        # Verify severity
        assert "severity" in data
        assert data["severity"] == "critical"
        
        # Verify sla compliance
        assert "within_sla" in data
        
        print(f"Incident Response (supplier_outage) - Verdict: {data['verdict']}, Severity: {data['severity']}, Within SLA: {data['within_sla']}")

    def test_incident_response_queue_overload(self, auth_headers):
        """Part 7: POST /api/stress-test/incident/queue_overload - Queue overload incident test."""
        response = requests.post(f"{BASE_URL}/api/stress-test/incident/queue_overload", headers=auth_headers)
        assert response.status_code == 200, f"Incident response failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "verdict" in data
        assert "steps" in data
        assert "severity" in data
        assert data["severity"] == "high"
        
        print(f"Incident Response (queue_overload) - Verdict: {data['verdict']}, Severity: {data['severity']}")

    # ==================== PART 8: TENANT SAFETY ====================
    def test_tenant_safety_endpoint(self, auth_headers):
        """Part 8: POST /api/stress-test/tenant-safety - Multi-tenant isolation test."""
        response = requests.post(f"{BASE_URL}/api/stress-test/tenant-safety", headers=auth_headers)
        assert response.status_code == 200, f"Tenant safety test failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "verdict" in data
        assert data["verdict"] in ["PASS", "FAIL"]
        
        # Verify test_cases
        assert "test_cases" in data
        test_cases = data["test_cases"]
        assert len(test_cases) > 0, "No test cases"
        
        # Verify isolation_mechanisms
        assert "isolation_mechanisms" in data
        isolation = data["isolation_mechanisms"]
        assert "query_filter" in isolation
        assert "middleware_enforcement" in isolation
        
        # Verify zero leaks
        assert "sla_check" in data
        sla = data["sla_check"]
        assert "zero_cross_tenant_leaks" in sla
        
        print(f"Tenant Safety - Verdict: {data['verdict']}, Test Cases: {len(test_cases)}, Zero Leaks: {sla['zero_cross_tenant_leaks']}")

    # ==================== PART 9: PERFORMANCE METRICS ====================
    def test_performance_metrics_endpoint(self, auth_headers):
        """Part 9: GET /api/stress-test/metrics - Performance metrics (P95, error rate, queue depth)."""
        response = requests.get(f"{BASE_URL}/api/stress-test/metrics", headers=auth_headers)
        assert response.status_code == 200, f"Metrics failed: {response.status_code} - {response.text}"
        
        data = response.json()
        # Verify metrics structure
        assert "metrics" in data
        metrics = data["metrics"]
        
        # Verify p95_latency
        assert "p95_latency" in metrics
        p95 = metrics["p95_latency"]
        assert "search_ms" in p95
        assert "booking_ms" in p95
        
        # Verify error_rate
        assert "error_rate" in metrics
        err = metrics["error_rate"]
        assert "current_pct" in err
        
        # Verify queue_depth
        assert "queue_depth" in metrics
        queue = metrics["queue_depth"]
        assert "total" in queue
        
        # Verify supplier_availability
        assert "supplier_availability" in metrics
        suppliers = metrics["supplier_availability"]
        assert "paximum" in suppliers
        assert "aviationstack" in suppliers
        assert "amadeus" in suppliers
        
        print(f"Metrics - P95 Search: {p95['search_ms']}ms, Error Rate: {err['current_pct']}%, Queue Total: {queue['total']}")

    # ==================== PART 10: STRESS TEST REPORT ====================
    def test_stress_test_report_endpoint(self, auth_headers):
        """Part 10: GET /api/stress-test/report - Final stress test report with readiness score."""
        response = requests.get(f"{BASE_URL}/api/stress-test/report", headers=auth_headers)
        assert response.status_code == 200, f"Report failed: {response.status_code} - {response.text}"
        
        data = response.json()
        # Verify readiness_score
        assert "readiness_score" in data
        score = data["readiness_score"]
        assert isinstance(score, (int, float))
        
        # Verify components
        assert "components" in data
        components = data["components"]
        assert len(components) > 0, "No components"
        
        # Verify bottlenecks
        assert "bottlenecks" in data
        
        # Verify capacity_limits
        assert "capacity_limits" in data
        limits = data["capacity_limits"]
        assert "max_searches_per_hour" in limits
        assert "max_bookings_per_hour" in limits
        
        # Verify sla_compliance
        assert "sla_compliance" in data
        
        # Verify recommendation
        assert "recommendation" in data
        
        print(f"Report - Readiness Score: {score}/10, Target: {data.get('target')}, Recommendation: {data['recommendation'][:50]}...")

    # ==================== DASHBOARD ====================
    def test_stress_test_dashboard_endpoint(self, auth_headers):
        """GET /api/stress-test/dashboard - Combined dashboard with all test data."""
        response = requests.get(f"{BASE_URL}/api/stress-test/dashboard", headers=auth_headers)
        assert response.status_code == 200, f"Dashboard failed: {response.status_code} - {response.text}"
        
        data = response.json()
        # Verify readiness_score
        assert "readiness_score" in data
        
        # Verify components
        assert "components" in data
        
        # Verify bottlenecks
        assert "bottlenecks" in data
        
        # Verify capacity_limits
        assert "capacity_limits" in data
        
        # Verify sla_compliance
        assert "sla_compliance" in data
        
        # Verify performance_metrics
        assert "performance_metrics" in data
        
        # Verify recent_history
        assert "recent_history" in data
        
        # Verify recommendation
        assert "recommendation" in data
        
        print(f"Dashboard - Score: {data['readiness_score']}/10, Tests Run: {data.get('tests_run', 'N/A')}, Tests Passed: {data.get('tests_passed', 'N/A')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
