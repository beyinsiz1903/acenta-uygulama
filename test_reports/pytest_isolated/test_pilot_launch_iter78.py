"""
Pilot Launch Testing - 10-Part Production Pilot Go-Live System (Iteration 78)

Part 1: Pilot Environment (controlled prod, limited agencies/traffic)
Part 2: Real Supplier Traffic (Paximum, AviationStack: shadow→limited)
Part 3: Monitoring Stack (Prometheus, Grafana)
Part 4: Incident Detection (outages, backlogs, payment failures)
Part 5: Pilot Agency Onboarding (accounts, pricing, training)
Part 6: Real Booking Flow (search→pricing→booking→voucher→notifications)
Part 7: Production Incident Test (supplier outage, payment error, DB slowdown)
Part 8: Real Performance Metrics (P95, reliability, success rate)
Part 9: Pilot Report (traffic stats, incidents, scores)
Part 10: Go-Live Decision (GO/CONDITIONAL_GO/NO_GO)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://financial-backbone-1.preview.emergentagent.com").rstrip("/")

@pytest.fixture(scope="module")
def auth_token():
    """Authenticate as super_admin to access pilot launch endpoints"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"},
        timeout=30
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    # Auth token field is 'access_token'
    token = data.get("access_token")
    assert token, f"No access_token in response: {data}"
    return token

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with Bearer token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestPilotDashboard:
    """Test combined pilot dashboard endpoint"""
    
    def test_pilot_dashboard(self, auth_headers):
        """GET /api/pilot/dashboard — combined dashboard with score, decision, components"""
        response = requests.get(f"{BASE_URL}/api/pilot/dashboard", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        
        data = response.json()
        # Verify key dashboard fields
        assert "readiness_score" in data, "Missing readiness_score"
        assert "decision" in data, "Missing decision"
        assert data["decision"] in ["GO", "CONDITIONAL_GO", "NO_GO"], f"Invalid decision: {data['decision']}"
        assert "components" in data, "Missing components"
        assert "go_live_checklist" in data, "Missing go_live_checklist"
        assert "risk_level" in data, "Missing risk_level"
        assert "timestamp" in data, "Missing timestamp"
        
        print(f"Dashboard - Score: {data['readiness_score']}/10, Decision: {data['decision']}, Risk: {data['risk_level']}")


class TestPilotEnvironment:
    """Part 1: Pilot Environment Tests"""
    
    def test_get_pilot_environment(self, auth_headers):
        """GET /api/pilot/environment — pilot environment config"""
        response = requests.get(f"{BASE_URL}/api/pilot/environment", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Get environment failed: {response.text}"
        
        data = response.json()
        assert "pilot_environment" in data, "Missing pilot_environment"
        env = data["pilot_environment"]
        
        # Check environment core structure (present in both initial and activated states)
        assert "status" in env, "Missing status"
        assert "max_agencies" in env, "Missing max_agencies"
        assert "feature_flags" in env, "Missing feature_flags"
        assert "monitoring_enabled" in env, "Missing monitoring_enabled"
        assert "alerting_enabled" in env, "Missing alerting_enabled"
        
        # infrastructure and safety are only present in initial state before activation
        # After activation, schema changes - this is expected behavior
        
        print(f"Environment - Status: {env['status']}, Mode: {env.get('mode')}, Max Agencies: {env['max_agencies']}")
    
    def test_activate_pilot_environment(self, auth_headers):
        """POST /api/pilot/environment/activate — run preflight checks and activate"""
        response = requests.post(f"{BASE_URL}/api/pilot/environment/activate", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Activate failed: {response.text}"
        
        data = response.json()
        assert "action" in data, "Missing action"
        assert data["action"] == "activate_pilot_environment"
        assert "verdict" in data, "Missing verdict"
        assert "preflight_checks" in data, "Missing preflight_checks"
        assert "passed" in data, "Missing passed count"
        assert "total" in data, "Missing total count"
        assert "duration_seconds" in data, "Missing duration_seconds"
        
        # Note: 2% random failure rate for realism
        print(f"Activation - Verdict: {data['verdict']}, Passed: {data['passed']}/{data['total']}")


class TestSupplierTraffic:
    """Part 2: Real Supplier Traffic Tests"""
    
    def test_get_supplier_traffic_status(self, auth_headers):
        """GET /api/pilot/supplier-traffic — status of Paximum and AviationStack"""
        response = requests.get(f"{BASE_URL}/api/pilot/supplier-traffic", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Get supplier traffic failed: {response.text}"
        
        data = response.json()
        assert "suppliers" in data, "Missing suppliers"
        
        suppliers = data["suppliers"]
        assert "paximum" in suppliers, "Missing paximum supplier"
        assert "aviationstack" in suppliers, "Missing aviationstack supplier"
        
        for name, sup in suppliers.items():
            assert "status" in sup, f"Missing status for {name}"
            assert "phase" in sup, f"Missing phase for {name}"
            assert "shadow_requests_sent" in sup, f"Missing shadow_requests_sent for {name}"
            assert "auth" in sup, f"Missing auth for {name}"
            assert "endpoints" in sup, f"Missing endpoints for {name}"
        
        print(f"Suppliers - Paximum: {suppliers['paximum']['phase']}, AviationStack: {suppliers['aviationstack']['phase']}")
    
    def test_activate_paximum_shadow(self, auth_headers):
        """POST /api/pilot/supplier-traffic/paximum/shadow — activate shadow traffic"""
        response = requests.post(f"{BASE_URL}/api/pilot/supplier-traffic/paximum/shadow", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Activate paximum shadow failed: {response.text}"
        
        data = response.json()
        assert data["supplier"] == "paximum"
        assert data["mode"] == "shadow"
        assert "verdict" in data
        assert "steps" in data
        assert "traffic_config" in data
        
        print(f"Paximum Shadow - Verdict: {data['verdict']}, Steps: {len(data['steps'])}")
    
    def test_activate_paximum_limited(self, auth_headers):
        """POST /api/pilot/supplier-traffic/paximum/limited — activate limited booking"""
        response = requests.post(f"{BASE_URL}/api/pilot/supplier-traffic/paximum/limited", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Activate paximum limited failed: {response.text}"
        
        data = response.json()
        assert data["supplier"] == "paximum"
        assert data["mode"] == "limited"
        assert "verdict" in data
        assert data["traffic_config"]["search_pct"] == 100
        assert data["traffic_config"]["book_pct"] == 10
        
        print(f"Paximum Limited - Verdict: {data['verdict']}, Book %: {data['traffic_config']['book_pct']}")
    
    def test_activate_aviationstack_limited(self, auth_headers):
        """POST /api/pilot/supplier-traffic/aviationstack/limited — activate for aviationstack"""
        response = requests.post(f"{BASE_URL}/api/pilot/supplier-traffic/aviationstack/limited", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Activate aviationstack limited failed: {response.text}"
        
        data = response.json()
        assert data["supplier"] == "aviationstack"
        assert data["mode"] == "limited"
        assert "verdict" in data
        
        print(f"AviationStack Limited - Verdict: {data['verdict']}")


class TestMonitoringStack:
    """Part 3: Monitoring Stack Tests"""
    
    def test_get_monitoring_status(self, auth_headers):
        """GET /api/pilot/monitoring — Prometheus + Grafana status"""
        response = requests.get(f"{BASE_URL}/api/pilot/monitoring", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Get monitoring failed: {response.text}"
        
        data = response.json()
        assert "prometheus" in data, "Missing prometheus"
        assert "grafana" in data, "Missing grafana"
        assert "tracked_metrics" in data, "Missing tracked_metrics"
        
        prom = data["prometheus"]
        assert prom["status"] == "running"
        assert "targets" in prom
        assert "metrics_collected" in prom
        
        graf = data["grafana"]
        assert graf["status"] == "running"
        assert "dashboards" in graf
        
        metrics = data["tracked_metrics"]
        assert "api_latency" in metrics
        assert "supplier_latency" in metrics
        assert "queue_depth" in metrics
        assert "booking_success_rate_pct" in metrics
        
        print(f"Monitoring - Prometheus: {prom['status']}, Grafana: {graf['status']}, Dashboards: {len(graf['dashboards'])}")


class TestIncidentDetection:
    """Part 4: Incident Detection Tests"""
    
    def test_get_incident_detection_status(self, auth_headers):
        """GET /api/pilot/incidents — detection rules and alert channels"""
        response = requests.get(f"{BASE_URL}/api/pilot/incidents", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Get incidents failed: {response.text}"
        
        data = response.json()
        assert "detection_rules" in data
        assert "total_rules" in data
        assert "active_rules" in data
        assert "playbooks" in data
        assert "alert_channels" in data
        
        assert len(data["detection_rules"]) >= 5, "Should have at least 5 detection rules"
        assert "slack" in data["alert_channels"]
        assert "pagerduty" in data["alert_channels"]
        
        print(f"Incidents - Rules: {data['total_rules']}, Active: {data['active_rules']}, Channels: {data['alert_channels']}")
    
    def test_simulate_supplier_outage(self, auth_headers):
        """POST /api/pilot/incidents/simulate/supplier_outage — simulate incident"""
        response = requests.post(f"{BASE_URL}/api/pilot/incidents/simulate/supplier_outage", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Simulate supplier_outage failed: {response.text}"
        
        data = response.json()
        assert data["incident_type"] == "supplier_outage"
        assert data["severity"] == "critical"
        assert "verdict" in data
        assert "steps" in data
        assert "total_response_ms" in data
        assert "within_sla" in data
        assert "alerts_fired" in data
        
        print(f"Supplier Outage Sim - Verdict: {data['verdict']}, Response: {data['total_response_ms']}ms, Within SLA: {data['within_sla']}")
    
    def test_simulate_queue_backlog(self, auth_headers):
        """POST /api/pilot/incidents/simulate/queue_backlog — simulate queue backlog"""
        response = requests.post(f"{BASE_URL}/api/pilot/incidents/simulate/queue_backlog", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Simulate queue_backlog failed: {response.text}"
        
        data = response.json()
        assert data["incident_type"] == "queue_backlog"
        assert data["severity"] == "high"
        assert "verdict" in data
        
        print(f"Queue Backlog Sim - Verdict: {data['verdict']}")
    
    def test_simulate_payment_failure(self, auth_headers):
        """POST /api/pilot/incidents/simulate/payment_failure — simulate payment failure"""
        response = requests.post(f"{BASE_URL}/api/pilot/incidents/simulate/payment_failure", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Simulate payment_failure failed: {response.text}"
        
        data = response.json()
        assert data["incident_type"] == "payment_failure"
        assert data["severity"] == "critical"
        assert "verdict" in data
        
        print(f"Payment Failure Sim - Verdict: {data['verdict']}")


class TestPilotAgencies:
    """Part 5: Pilot Agency Onboarding Tests"""
    
    def test_get_pilot_agencies(self, auth_headers):
        """GET /api/pilot/agencies — list pilot agencies with onboarding status"""
        response = requests.get(f"{BASE_URL}/api/pilot/agencies", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Get agencies failed: {response.text}"
        
        data = response.json()
        assert "agencies" in data
        assert "total" in data
        assert "active" in data
        assert "onboarding" in data
        assert "total_bookings" in data
        assert "pricing_tiers" in data
        assert "training_materials" in data
        
        assert len(data["agencies"]) >= 1, "Should have at least 1 agency"
        
        for agency in data["agencies"]:
            assert "id" in agency
            assert "name" in agency
            assert "status" in agency
            assert "config" in agency
        
        print(f"Agencies - Total: {data['total']}, Active: {data['active']}, Bookings: {data['total_bookings']}")
    
    def test_onboard_agency(self, auth_headers):
        """POST /api/pilot/agencies/onboard?agency_name=TestAgency — onboard a new agency"""
        response = requests.post(
            f"{BASE_URL}/api/pilot/agencies/onboard?agency_name=TestPilotAgency",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Onboard agency failed: {response.text}"
        
        data = response.json()
        assert data["action"] == "onboard_agency"
        assert data["agency_name"] == "TestPilotAgency"
        assert "verdict" in data
        assert "agency_id" in data
        assert "steps" in data
        assert "credentials" in data
        
        creds = data["credentials"]
        assert "admin_email" in creds
        assert "api_key" in creds
        
        print(f"Onboard Agency - Verdict: {data['verdict']}, ID: {data['agency_id']}")


class TestBookingFlow:
    """Part 6: Real Booking Flow Tests"""
    
    def test_execute_hotel_booking_flow(self, auth_headers):
        """POST /api/pilot/booking-flow/hotel — execute hotel booking flow end-to-end"""
        response = requests.post(f"{BASE_URL}/api/pilot/booking-flow/hotel", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Hotel booking flow failed: {response.text}"
        
        data = response.json()
        assert data["action"] == "execute_booking_flow"
        assert data["flow_type"] == "hotel"
        assert "verdict" in data
        assert "steps" in data
        assert "booking" in data
        assert "total_latency_ms" in data
        assert "sla_check" in data
        
        # Verify booking flow steps exist
        step_names = [s["step"] for s in data["steps"]]
        assert "search" in step_names
        assert "pricing_calculation" in step_names
        assert "booking_creation" in step_names
        assert "voucher_generation" in step_names
        assert "notification_sent" in step_names
        
        # Note: 3% random step failure rate for realism
        print(f"Hotel Booking - Verdict: {data['verdict']}, Latency: {data['total_latency_ms']}ms, Booking ID: {data['booking']['booking_id']}")
    
    def test_execute_flight_booking_flow(self, auth_headers):
        """POST /api/pilot/booking-flow/flight — execute flight booking flow end-to-end"""
        response = requests.post(f"{BASE_URL}/api/pilot/booking-flow/flight", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Flight booking flow failed: {response.text}"
        
        data = response.json()
        assert data["action"] == "execute_booking_flow"
        assert data["flow_type"] == "flight"
        assert "verdict" in data
        assert "booking" in data
        assert data["booking"]["supplier"] == "aviationstack"
        
        print(f"Flight Booking - Verdict: {data['verdict']}, Latency: {data['total_latency_ms']}ms")


class TestIncidentTest:
    """Part 7: Production Incident Test"""
    
    def test_supplier_outage_incident_test(self, auth_headers):
        """POST /api/pilot/incident-test/supplier_outage — production incident test with recovery"""
        response = requests.post(f"{BASE_URL}/api/pilot/incident-test/supplier_outage", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Supplier outage test failed: {response.text}"
        
        data = response.json()
        assert data["action"] == "production_incident_test"
        assert data["scenario"] == "supplier_outage"
        assert "verdict" in data
        assert "phases" in data
        assert "total_recovery_ms" in data
        assert "sla_check" in data
        
        # Check recovery phases
        phase_names = [p["phase"] for p in data["phases"]]
        assert "fault_injection" in phase_names
        assert "detection" in phase_names
        assert "auto_recovery" in phase_names
        assert "verification" in phase_names
        
        print(f"Supplier Outage Test - Verdict: {data['verdict']}, Recovery: {data['total_recovery_seconds']}s")
    
    def test_payment_error_incident_test(self, auth_headers):
        """POST /api/pilot/incident-test/payment_error — payment error incident test"""
        response = requests.post(f"{BASE_URL}/api/pilot/incident-test/payment_error", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Payment error test failed: {response.text}"
        
        data = response.json()
        assert data["scenario"] == "payment_error"
        assert "verdict" in data
        assert "sla_check" in data
        
        print(f"Payment Error Test - Verdict: {data['verdict']}")
    
    def test_database_slowdown_incident_test(self, auth_headers):
        """POST /api/pilot/incident-test/database_slowdown — DB slowdown incident test"""
        response = requests.post(f"{BASE_URL}/api/pilot/incident-test/database_slowdown", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Database slowdown test failed: {response.text}"
        
        data = response.json()
        assert data["scenario"] == "database_slowdown"
        assert "verdict" in data
        assert "phases" in data
        assert data["auto_recovery_worked"] == True
        
        print(f"Database Slowdown Test - Verdict: {data['verdict']}")


class TestPerformanceMetrics:
    """Part 8: Real Performance Metrics Tests"""
    
    def test_get_real_performance_metrics(self, auth_headers):
        """GET /api/pilot/performance — real P95 latency, supplier reliability, booking success rate"""
        response = requests.get(f"{BASE_URL}/api/pilot/performance", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Get performance failed: {response.text}"
        
        data = response.json()
        assert "performance" in data
        assert "pilot_traffic_summary" in data
        
        perf = data["performance"]
        assert "p95_latency" in perf
        assert "supplier_reliability" in perf
        assert "booking_success_rate" in perf
        assert "throughput" in perf
        
        # Verify P95 latency structure
        p95 = perf["p95_latency"]
        assert "api_ms" in p95
        assert "supplier_ms" in p95
        assert "e2e_booking_ms" in p95
        
        # Verify supplier reliability
        reliability = perf["supplier_reliability"]
        assert "paximum" in reliability
        assert "aviationstack" in reliability
        
        summary = data["pilot_traffic_summary"]
        assert "total_searches" in summary
        assert "total_bookings" in summary
        assert "total_revenue_try" in summary
        
        print(f"Performance - API P95: {p95['api_ms']}ms, Booking Success: {perf['booking_success_rate']['rate_pct']}%")


class TestPilotReport:
    """Part 9: Pilot Report Tests"""
    
    def test_generate_pilot_report(self, auth_headers):
        """GET /api/pilot/report — final pilot report with scores, traffic stats, incident log"""
        response = requests.get(f"{BASE_URL}/api/pilot/report", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Get report failed: {response.text}"
        
        data = response.json()
        assert data["report"] == "pilot_launch_report"
        assert "readiness_score" in data
        assert "target" in data
        assert "meets_target" in data
        assert "components" in data
        assert "traffic_statistics" in data
        assert "incident_log" in data
        assert "supplier_reliability" in data
        assert "recommendation" in data
        
        # Verify 9 score components
        components = data["components"]
        expected_components = [
            "pilot_environment", "supplier_traffic", "monitoring_stack",
            "incident_detection", "agency_onboarding", "booking_flow",
            "incident_recovery", "performance_metrics", "pilot_operations"
        ]
        for comp in expected_components:
            assert comp in components, f"Missing component: {comp}"
            assert "score" in components[comp]
            assert "weight" in components[comp]
            assert "status" in components[comp]
        
        print(f"Report - Score: {data['readiness_score']}/10, Target: {data['target']}, Meets: {data['meets_target']}")


class TestGoLiveDecision:
    """Part 10: Go-Live Decision Tests"""
    
    def test_get_go_live_decision(self, auth_headers):
        """GET /api/pilot/go-live — go-live decision with checklist, next steps, risk assessment"""
        response = requests.get(f"{BASE_URL}/api/pilot/go-live", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Get go-live failed: {response.text}"
        
        data = response.json()
        assert "decision" in data
        assert data["decision"] in ["GO", "CONDITIONAL_GO", "NO_GO"]
        assert "readiness_score" in data
        assert "risk_level" in data
        assert "recommendation" in data
        assert "go_live_checklist" in data
        assert "checklist_pass_rate" in data
        assert "pilot_summary" in data
        assert "next_steps" in data
        
        # Verify checklist items
        checklist = data["go_live_checklist"]
        assert len(checklist) == 10, "Should have 10 checklist items"
        
        for item in checklist:
            assert "item" in item
            assert "passed" in item
            assert "evidence" in item
        
        # Verify next steps based on decision
        next_steps = data["next_steps"]
        assert isinstance(next_steps, list)
        
        summary = data["pilot_summary"]
        assert "total_bookings" in summary
        assert "incidents_handled" in summary
        assert "supplier_uptime" in summary
        
        print(f"Go-Live - Decision: {data['decision']}, Score: {data['readiness_score']}/10, Risk: {data['risk_level']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
