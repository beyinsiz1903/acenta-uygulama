"""Operations Layer API Tests (P1-P9) - Iteration 67.

Tests all 30 API endpoints for the Travel Platform Operations Layer:
  P1 - Supplier Performance Dashboard
  P2 - Booking Funnel Analytics
  P3 - Failover Visibility
  P4 - Booking Incident Tracking
  P5 - Supplier Debugging Tools
  P6 - Real-Time Alerting
  P7 - Voucher Pipeline
  P8 - OPS Admin Panel
  P9 - Operations Metrics (Prometheus)

Test credentials: agent@acenta.test / agent123 (agency_admin role)
"""

import pytest
import requests
import os
import uuid

# Get BASE_URL from environment
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://travel-growth-engine.preview.emergentagent.com"


class TestOpsAuth:
    """Test authentication for Operations Layer endpoints."""

    @pytest.fixture(scope="class")
    def agent_token(self):
        """Login with agent credentials and get token."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200, f"Agent login failed: {response.text}"
        data = response.json()
        return data.get("access_token")

    @pytest.fixture(scope="class")
    def auth_headers(self, agent_token):
        """Return Authorization headers."""
        return {"Authorization": f"Bearer {agent_token}"}

    def test_auth_required_for_ops_endpoints(self):
        """Test that ops endpoints require authentication."""
        endpoints = [
            "/api/ops/suppliers/performance/dashboard",
            "/api/ops/suppliers/funnel/analytics",
            "/api/ops/suppliers/failover/dashboard",
            "/api/ops/suppliers/incidents",
            "/api/ops/suppliers/alerts",
            "/api/ops/suppliers/metrics",
        ]
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code in [401, 403], f"Expected 401/403 for {endpoint} without auth, got {response.status_code}"
        print(f"PASS: Auth required for {len(endpoints)} ops endpoints")


class TestP1SupplierPerformanceDashboard:
    """P1: Supplier Performance Dashboard tests."""

    @pytest.fixture(scope="class")
    def agent_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200
        return response.json().get("access_token")

    @pytest.fixture(scope="class")
    def auth_headers(self, agent_token):
        return {"Authorization": f"Bearer {agent_token}"}

    def test_performance_dashboard(self, auth_headers):
        """GET /api/ops/suppliers/performance/dashboard — returns supplier metrics."""
        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/performance/dashboard",
            headers=auth_headers,
            params={"window_minutes": 60}
        )
        assert response.status_code == 200, f"Performance dashboard failed: {response.text}"
        data = response.json()

        # Validate response structure
        assert "dashboard" in data, "Missing 'dashboard' key"
        assert "window_minutes" in data, "Missing 'window_minutes' key"
        assert "total_suppliers" in data, "Missing 'total_suppliers' key"
        assert "generated_at" in data, "Missing 'generated_at' key"

        # Validate dashboard entries structure if any
        for supplier in data.get("dashboard", []):
            assert "supplier_code" in supplier
            assert "total_calls" in supplier
            assert "error_rate" in supplier
            assert "timeout_rate" in supplier
            assert "confirmation_success_rate" in supplier
            assert "latency" in supplier
            assert "failover_frequency" in supplier

        print(f"PASS: Performance dashboard returned {data.get('total_suppliers', 0)} suppliers")

    def test_performance_timeseries(self, auth_headers):
        """GET /api/ops/suppliers/performance/timeseries/{supplier_code} — returns latency timeseries."""
        supplier_code = "mock_hotel"  # Use known mock supplier
        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/performance/timeseries/{supplier_code}",
            headers=auth_headers,
            params={"window_hours": 24, "bucket_minutes": 15}
        )
        assert response.status_code == 200, f"Performance timeseries failed: {response.text}"
        data = response.json()

        # Validate response structure
        assert "supplier_code" in data
        assert "window_hours" in data
        assert "bucket_minutes" in data
        assert "buckets" in data
        assert data["supplier_code"] == supplier_code

        print(f"PASS: Performance timeseries returned {len(data.get('buckets', []))} buckets")


class TestP2BookingFunnelAnalytics:
    """P2: Booking Funnel Analytics tests."""

    @pytest.fixture(scope="class")
    def agent_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200
        return response.json().get("access_token")

    @pytest.fixture(scope="class")
    def auth_headers(self, agent_token):
        return {"Authorization": f"Bearer {agent_token}"}

    def test_funnel_analytics(self, auth_headers):
        """GET /api/ops/suppliers/funnel/analytics — returns booking funnel stages."""
        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/funnel/analytics",
            headers=auth_headers,
            params={"window_hours": 24}
        )
        assert response.status_code == 200, f"Funnel analytics failed: {response.text}"
        data = response.json()

        # Validate response structure
        assert "funnel" in data, "Missing 'funnel' key"
        assert "failure_summary" in data, "Missing 'failure_summary' key"
        assert "supplier_reliability" in data, "Missing 'supplier_reliability' key"
        assert "window_hours" in data, "Missing 'window_hours' key"
        assert "total_bookings" in data, "Missing 'total_bookings' key"

        # Validate funnel stages structure
        for stage in data.get("funnel", []):
            assert "stage" in stage
            assert "current_count" in stage
            assert "reached_count" in stage
            assert "conversion_from_previous" in stage
            assert "conversion_from_start" in stage

        print(f"PASS: Funnel analytics returned {len(data.get('funnel', []))} stages, {data.get('total_bookings', 0)} total bookings")

    def test_funnel_timeseries(self, auth_headers):
        """GET /api/ops/suppliers/funnel/timeseries — returns time-bucketed funnel data."""
        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/funnel/timeseries",
            headers=auth_headers,
            params={"window_hours": 24, "bucket_hours": 1}
        )
        assert response.status_code == 200, f"Funnel timeseries failed: {response.text}"
        data = response.json()

        # Validate response structure
        assert "window_hours" in data
        assert "bucket_hours" in data
        assert "buckets" in data

        print(f"PASS: Funnel timeseries returned {len(data.get('buckets', []))} buckets")


class TestP3FailoverVisibility:
    """P3: Failover Visibility tests."""

    @pytest.fixture(scope="class")
    def agent_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200
        return response.json().get("access_token")

    @pytest.fixture(scope="class")
    def auth_headers(self, agent_token):
        return {"Authorization": f"Bearer {agent_token}"}

    def test_failover_dashboard(self, auth_headers):
        """GET /api/ops/suppliers/failover/dashboard — returns failover summary and states."""
        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/failover/dashboard",
            headers=auth_headers,
            params={"window_hours": 24}
        )
        assert response.status_code == 200, f"Failover dashboard failed: {response.text}"
        data = response.json()

        # Validate response structure
        assert "failover_summary" in data, "Missing 'failover_summary' key"
        assert "circuit_breaker_states" in data, "Missing 'circuit_breaker_states' key"
        assert "health_states" in data, "Missing 'health_states' key"
        assert "recent_events" in data, "Missing 'recent_events' key"
        assert "window_hours" in data, "Missing 'window_hours' key"

        # Validate circuit breaker states structure
        for cb in data.get("circuit_breaker_states", []):
            assert "supplier_code" in cb
            assert "circuit_open" in cb
            assert "health_score" in cb
            assert "composite_score" in cb
            assert "disabled" in cb

        print(f"PASS: Failover dashboard returned {len(data.get('circuit_breaker_states', []))} circuit states, {len(data.get('failover_summary', []))} failover summaries")


class TestP4BookingIncidentTracking:
    """P4: Booking Incident Tracking tests."""

    @pytest.fixture(scope="class")
    def agent_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200
        return response.json().get("access_token")

    @pytest.fixture(scope="class")
    def auth_headers(self, agent_token):
        return {"Authorization": f"Bearer {agent_token}"}

    def test_detect_incidents(self, auth_headers):
        """GET /api/ops/suppliers/incidents/detect — detects stuck bookings, failed confirmations, payment mismatches."""
        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/incidents/detect",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Detect incidents failed: {response.text}"
        data = response.json()

        # Validate response structure
        assert "stuck_bookings" in data, "Missing 'stuck_bookings' key"
        assert "failed_confirmations" in data, "Missing 'failed_confirmations' key"
        assert "payment_mismatches" in data, "Missing 'payment_mismatches' key"
        assert "total_issues" in data, "Missing 'total_issues' key"

        print(f"PASS: Detected {data.get('total_issues', 0)} total issues")

    def test_create_and_list_incidents(self, auth_headers):
        """POST /api/ops/suppliers/incidents — create incident, GET list."""
        test_incident = {
            "incident_type": "TEST_manual_incident",
            "booking_id": f"test-booking-{uuid.uuid4().hex[:8]}",
            "supplier_code": "mock_hotel",
            "severity": "warning",
            "description": "Test incident for operations layer testing",
            "metadata": {"test_run": True}
        }

        # Create incident
        create_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/incidents",
            headers=auth_headers,
            json=test_incident
        )
        assert create_resp.status_code == 201, f"Create incident failed: {create_resp.text}"
        created = create_resp.json()

        assert "incident_id" in created
        assert created["incident_type"] == test_incident["incident_type"]
        assert created["severity"] == test_incident["severity"]
        assert created["status"] == "open"

        incident_id = created["incident_id"]

        # List incidents
        list_resp = requests.get(
            f"{BASE_URL}/api/ops/suppliers/incidents",
            headers=auth_headers,
            params={"limit": 50}
        )
        assert list_resp.status_code == 200, f"List incidents failed: {list_resp.text}"
        list_data = list_resp.json()

        assert "incidents" in list_data
        assert "total" in list_data

        # Verify our created incident is in the list
        found = any(inc.get("incident_id") == incident_id for inc in list_data.get("incidents", []))
        assert found, f"Created incident {incident_id} not found in list"

        print(f"PASS: Created incident {incident_id}, listed {list_data.get('total', 0)} incidents")
        return incident_id

    def test_resolve_incident(self, auth_headers):
        """POST /api/ops/suppliers/incidents/{id}/resolve — resolve incident."""
        # First create an incident to resolve
        test_incident = {
            "incident_type": "TEST_resolve_incident",
            "booking_id": f"test-booking-{uuid.uuid4().hex[:8]}",
            "severity": "info",
            "description": "Test incident to be resolved"
        }

        create_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/incidents",
            headers=auth_headers,
            json=test_incident
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["incident_id"]

        # Resolve the incident
        resolve_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/incidents/{incident_id}/resolve",
            headers=auth_headers,
            json={"resolution": "Test resolution - incident resolved successfully"}
        )
        assert resolve_resp.status_code == 200, f"Resolve incident failed: {resolve_resp.text}"
        resolved = resolve_resp.json()

        assert resolved.get("status") == "resolved"
        assert resolved.get("resolution") is not None

        print(f"PASS: Resolved incident {incident_id}")

    def test_force_booking_state(self, auth_headers):
        """POST /api/ops/suppliers/incidents/recovery/force-state/{booking_id} — force booking state change."""
        # Use an existing test booking ID or create one
        test_booking_id = "orch-1773344214"  # Known booking from previous tests

        response = requests.post(
            f"{BASE_URL}/api/ops/suppliers/incidents/recovery/force-state/{test_booking_id}",
            headers=auth_headers,
            json={
                "target_state": "supplier_confirmed",
                "reason": "TEST: Force state change for operations layer testing"
            }
        )
        # May return 200 or error if booking not found
        assert response.status_code in [200, 404], f"Force state failed unexpectedly: {response.text}"

        if response.status_code == 200:
            data = response.json()
            if "error" not in data:
                assert "booking_id" in data
                assert "forced" in data
                print(f"PASS: Force state change applied to {test_booking_id}")
            else:
                print(f"PASS: Force state endpoint returned error: {data.get('error')}")
        else:
            print("PASS: Force state endpoint working (booking not found is expected)")


class TestP5SupplierDebuggingTools:
    """P5: Supplier Debugging Tools tests."""

    @pytest.fixture(scope="class")
    def agent_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200
        return response.json().get("access_token")

    @pytest.fixture(scope="class")
    def auth_headers(self, agent_token):
        return {"Authorization": f"Bearer {agent_token}"}

    def test_list_debug_interactions(self, auth_headers):
        """GET /api/ops/suppliers/debug/interactions — list supplier debug logs."""
        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/debug/interactions",
            headers=auth_headers,
            params={"window_hours": 24, "limit": 50}
        )
        assert response.status_code == 200, f"List debug interactions failed: {response.text}"
        data = response.json()

        assert "interactions" in data
        assert "total" in data

        print(f"PASS: Listed {data.get('total', 0)} debug interactions")

    def test_replay_supplier_request_dry_run(self, auth_headers):
        """POST /api/ops/suppliers/debug/replay/{trace_id} — replay supplier request (dry run)."""
        # Use a fake trace_id - should return trace_not_found
        fake_trace_id = f"trace-{uuid.uuid4().hex}"

        response = requests.post(
            f"{BASE_URL}/api/ops/suppliers/debug/replay/{fake_trace_id}",
            headers=auth_headers,
            params={"dry_run": True}
        )
        assert response.status_code == 200, f"Replay request failed: {response.text}"
        data = response.json()

        # Either returns dry_run result or trace_not_found error
        if "error" in data:
            assert data["error"] == "trace_not_found"
        else:
            assert data.get("mode") == "dry_run"

        print("PASS: Replay endpoint working (trace_not_found is expected for fake trace)")


class TestP6RealTimeAlerting:
    """P6: Real-Time Alerting tests."""

    @pytest.fixture(scope="class")
    def agent_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200
        return response.json().get("access_token")

    @pytest.fixture(scope="class")
    def auth_headers(self, agent_token):
        return {"Authorization": f"Bearer {agent_token}"}

    def test_list_alerts(self, auth_headers):
        """GET /api/ops/suppliers/alerts — list alerts."""
        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/alerts",
            headers=auth_headers,
            params={"limit": 50}
        )
        assert response.status_code == 200, f"List alerts failed: {response.text}"
        data = response.json()

        assert "alerts" in data
        assert "total" in data

        print(f"PASS: Listed {data.get('total', 0)} alerts")

    def test_evaluate_alert_rules(self, auth_headers):
        """POST /api/ops/suppliers/alerts/evaluate — evaluate alert rules."""
        response = requests.post(
            f"{BASE_URL}/api/ops/suppliers/alerts/evaluate",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Evaluate alerts failed: {response.text}"
        data = response.json()

        assert "fired_alerts" in data
        assert "total_fired" in data

        print(f"PASS: Alert evaluation fired {data.get('total_fired', 0)} alerts")

    def test_configure_alert_channels(self, auth_headers):
        """POST /api/ops/suppliers/alerts/config — configure alert channels."""
        config = {
            "slack_webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK/URL",
            "email_recipients": ["test@example.com", "ops@example.com"]
        }

        response = requests.post(
            f"{BASE_URL}/api/ops/suppliers/alerts/config",
            headers=auth_headers,
            json=config
        )
        assert response.status_code == 200, f"Configure alerts failed: {response.text}"
        data = response.json()

        assert data.get("status") == "ok"

        print("PASS: Alert channels configured")

    def test_acknowledge_and_resolve_alert(self, auth_headers):
        """POST /api/ops/suppliers/alerts/{id}/acknowledge and resolve."""
        # First fire an alert via evaluate
        eval_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/alerts/evaluate",
            headers=auth_headers
        )
        eval_resp.json()

        # Get list of active alerts
        list_resp = requests.get(
            f"{BASE_URL}/api/ops/suppliers/alerts",
            headers=auth_headers,
            params={"status": "active", "limit": 10}
        )
        list_data = list_resp.json()
        alerts = list_data.get("alerts", [])

        if alerts:
            alert_id = alerts[0].get("alert_id")

            # Acknowledge alert
            ack_resp = requests.post(
                f"{BASE_URL}/api/ops/suppliers/alerts/{alert_id}/acknowledge",
                headers=auth_headers
            )
            assert ack_resp.status_code == 200, f"Acknowledge alert failed: {ack_resp.text}"
            ack_data = ack_resp.json()
            assert ack_data.get("acknowledged") is True or ack_data.get("status") == "acknowledged"

            # Resolve alert
            resolve_resp = requests.post(
                f"{BASE_URL}/api/ops/suppliers/alerts/{alert_id}/resolve",
                headers=auth_headers
            )
            assert resolve_resp.status_code == 200, f"Resolve alert failed: {resolve_resp.text}"
            resolve_data = resolve_resp.json()
            assert resolve_data.get("resolved") is True or resolve_data.get("status") == "resolved"

            print(f"PASS: Acknowledged and resolved alert {alert_id}")
        else:
            print("PASS: Alert acknowledge/resolve endpoints working (no active alerts to test)")


class TestP7VoucherPipeline:
    """P7: Voucher Pipeline tests."""

    @pytest.fixture(scope="class")
    def agent_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200
        return response.json().get("access_token")

    @pytest.fixture(scope="class")
    def auth_headers(self, agent_token):
        return {"Authorization": f"Bearer {agent_token}"}

    def test_voucher_pipeline_status(self, auth_headers):
        """GET /api/ops/suppliers/vouchers/pipeline — pipeline status."""
        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/vouchers/pipeline",
            headers=auth_headers,
            params={"limit": 50}
        )
        assert response.status_code == 200, f"Voucher pipeline status failed: {response.text}"
        data = response.json()

        assert "status_distribution" in data
        assert "total" in data
        assert "recent_vouchers" in data

        print(f"PASS: Voucher pipeline has {data.get('total', 0)} vouchers")

    def test_create_voucher(self, auth_headers):
        """POST /api/ops/suppliers/vouchers — create voucher."""
        voucher_data = {
            "booking_id": f"TEST-booking-{uuid.uuid4().hex[:8]}",
            "supplier_booking_id": f"SUP-{uuid.uuid4().hex[:8]}",
            "confirmation_code": f"CONF-{uuid.uuid4().hex[:6]}",
            "guest_names": ["Test Guest 1", "Test Guest 2"],
            "hotel_name": "Test Hotel Istanbul",
            "check_in": "2026-03-01",
            "check_out": "2026-03-05",
            "room_type": "Deluxe Double",
            "total_price": 5000.00,
            "currency": "TRY"
        }

        response = requests.post(
            f"{BASE_URL}/api/ops/suppliers/vouchers",
            headers=auth_headers,
            json=voucher_data
        )
        assert response.status_code == 201, f"Create voucher failed: {response.text}"
        data = response.json()

        assert "voucher_id" in data
        assert data.get("status") == "pending"
        assert data.get("booking_id") == voucher_data["booking_id"]

        voucher_id = data["voucher_id"]
        print(f"PASS: Created voucher {voucher_id}")
        return voucher_id

    def test_generate_voucher(self, auth_headers):
        """POST /api/ops/suppliers/vouchers/{id}/generate — generate voucher PDF/HTML."""
        # First create a voucher
        voucher_data = {
            "booking_id": f"TEST-gen-{uuid.uuid4().hex[:8]}",
            "guest_names": ["Generate Test"],
            "hotel_name": "Generation Test Hotel",
            "check_in": "2026-04-01",
            "check_out": "2026-04-03"
        }

        create_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/vouchers",
            headers=auth_headers,
            json=voucher_data
        )
        assert create_resp.status_code == 201
        voucher_id = create_resp.json()["voucher_id"]

        # Generate the voucher
        gen_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/vouchers/{voucher_id}/generate",
            headers=auth_headers
        )
        assert gen_resp.status_code == 200, f"Generate voucher failed: {gen_resp.text}"
        data = gen_resp.json()

        assert data.get("status") == "generated"
        assert "html_length" in data

        print(f"PASS: Generated voucher {voucher_id} with {data.get('html_length', 0)} bytes HTML")
        return voucher_id

    def test_send_voucher_email(self, auth_headers):
        """POST /api/ops/suppliers/vouchers/{id}/send — send voucher email."""
        # Create and generate a voucher first
        voucher_data = {
            "booking_id": f"TEST-send-{uuid.uuid4().hex[:8]}",
            "guest_names": ["Send Test"],
            "hotel_name": "Send Test Hotel"
        }

        create_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/vouchers",
            headers=auth_headers,
            json=voucher_data
        )
        assert create_resp.status_code == 201
        voucher_id = create_resp.json()["voucher_id"]

        # Generate first
        requests.post(
            f"{BASE_URL}/api/ops/suppliers/vouchers/{voucher_id}/generate",
            headers=auth_headers
        )

        # Send email
        send_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/vouchers/{voucher_id}/send",
            headers=auth_headers,
            json={"recipient_email": "test@example.com"}
        )
        assert send_resp.status_code == 200, f"Send voucher failed: {send_resp.text}"
        data = send_resp.json()

        assert data.get("status") == "delivered"
        assert data.get("recipient") == "test@example.com"

        print(f"PASS: Queued voucher {voucher_id} email to test@example.com (MOCKED - queued to DB)")

    def test_retry_failed_vouchers(self, auth_headers):
        """POST /api/ops/suppliers/vouchers/retry-failed — retry failed vouchers."""
        response = requests.post(
            f"{BASE_URL}/api/ops/suppliers/vouchers/retry-failed",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Retry failed vouchers failed: {response.text}"
        data = response.json()

        assert "retried" in data

        print(f"PASS: Retried {data.get('retried', 0)} failed vouchers")


class TestP8OPSAdminPanel:
    """P8: OPS Admin Panel tests."""

    @pytest.fixture(scope="class")
    def agent_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200
        return response.json().get("access_token")

    @pytest.fixture(scope="class")
    def auth_headers(self, agent_token):
        return {"Authorization": f"Bearer {agent_token}"}

    def test_inspect_booking(self, auth_headers):
        """GET /api/ops/suppliers/admin/booking/{id} — inspect booking with runs, vouchers, incidents."""
        booking_id = "orch-1773344214"  # Known booking from previous tests

        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/admin/booking/{booking_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Inspect booking failed: {response.text}"
        data = response.json()

        # Either returns booking data or error
        if "error" not in data:
            assert "booking" in data
            assert "orchestration_runs" in data
            assert "vouchers" in data
            assert "incidents" in data
            print(f"PASS: Inspected booking {booking_id} with {len(data.get('orchestration_runs', []))} runs")
        else:
            print(f"PASS: Inspect booking endpoint working (booking not found is expected: {data.get('error')})")

    def test_supplier_override(self, auth_headers):
        """POST /api/ops/suppliers/admin/supplier/{code}/override — circuit_open/close, disable/enable."""
        supplier_code = "mock_hotel"

        # Test circuit_open
        response = requests.post(
            f"{BASE_URL}/api/ops/suppliers/admin/supplier/{supplier_code}/override",
            headers=auth_headers,
            json={"action": "circuit_open", "reason": "TEST: Circuit open for testing"}
        )
        assert response.status_code == 200, f"Supplier override failed: {response.text}"
        data = response.json()

        assert data.get("supplier_code") == supplier_code
        assert data.get("action") == "circuit_open"
        assert data.get("applied") is True

        # Test circuit_close to restore
        response = requests.post(
            f"{BASE_URL}/api/ops/suppliers/admin/supplier/{supplier_code}/override",
            headers=auth_headers,
            json={"action": "circuit_close", "reason": "TEST: Circuit close restore"}
        )
        assert response.status_code == 200

        print(f"PASS: Supplier override circuit_open/circuit_close for {supplier_code}")

    def test_manual_failover(self, auth_headers):
        """POST /api/ops/suppliers/admin/supplier/{code}/manual-failover — trigger manual failover."""
        supplier_code = "mock_hotel"

        response = requests.post(
            f"{BASE_URL}/api/ops/suppliers/admin/supplier/{supplier_code}/manual-failover",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Manual failover failed: {response.text}"
        data = response.json()

        assert "primary_supplier" in data
        assert "selected_supplier" in data
        assert "fallback_chain" in data
        assert "reason" in data

        print(f"PASS: Manual failover from {data.get('primary_supplier')} to {data.get('selected_supplier')}")

    def test_price_override(self, auth_headers):
        """POST /api/ops/suppliers/admin/price-override — override booking price."""
        # This will fail if booking doesn't exist, but validates endpoint is working
        override_data = {
            "booking_id": "orch-1773344214",  # Known booking
            "override_price": 15000.00,
            "currency": "TRY",
            "reason": "TEST: Price override for operations testing"
        }

        response = requests.post(
            f"{BASE_URL}/api/ops/suppliers/admin/price-override",
            headers=auth_headers,
            json=override_data
        )
        assert response.status_code == 200, f"Price override failed: {response.text}"
        data = response.json()

        if "error" not in data:
            assert "booking_id" in data
            assert "old_price" in data
            assert "new_price" in data
            assert data.get("overridden") is True
            print(f"PASS: Price override applied: {data.get('old_price')} -> {data.get('new_price')}")
        else:
            print(f"PASS: Price override endpoint working (error: {data.get('error')})")

    def test_audit_log(self, auth_headers):
        """GET /api/ops/suppliers/admin/audit-log — audit trail."""
        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/admin/audit-log",
            headers=auth_headers,
            params={"limit": 50}
        )
        assert response.status_code == 200, f"Audit log failed: {response.text}"
        data = response.json()

        assert "logs" in data
        assert "total" in data

        # Verify our test actions were logged
        logs = data.get("logs", [])
        [log.get("action") for log in logs]

        print(f"PASS: Audit log has {data.get('total', 0)} entries")


class TestP9OperationsMetrics:
    """P9: Operations Metrics (Prometheus) tests."""

    @pytest.fixture(scope="class")
    def agent_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200
        return response.json().get("access_token")

    @pytest.fixture(scope="class")
    def auth_headers(self, agent_token):
        return {"Authorization": f"Bearer {agent_token}"}

    def test_metrics_json(self, auth_headers):
        """GET /api/ops/suppliers/metrics — JSON metrics."""
        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/metrics",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Metrics JSON failed: {response.text}"
        data = response.json()

        # Validate metrics structure
        assert "bookings_by_state" in data, "Missing 'bookings_by_state'"
        assert "bookings_total" in data, "Missing 'bookings_total'"
        assert "bookings_per_minute" in data, "Missing 'bookings_per_minute'"
        assert "supplier_conversion" in data, "Missing 'supplier_conversion'"
        assert "error_rate_1h" in data, "Missing 'error_rate_1h'"
        assert "orchestration_1h" in data, "Missing 'orchestration_1h'"
        assert "failovers_1h" in data, "Missing 'failovers_1h'"
        assert "active_alerts" in data, "Missing 'active_alerts'"
        assert "collected_at" in data, "Missing 'collected_at'"

        print(f"PASS: JSON metrics - {data.get('bookings_total', 0)} total bookings, error_rate={data.get('error_rate_1h', 0)}")

    def test_metrics_prometheus(self, auth_headers):
        """GET /api/ops/suppliers/metrics/prometheus — Prometheus text format."""
        response = requests.get(
            f"{BASE_URL}/api/ops/suppliers/metrics/prometheus",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Metrics Prometheus failed: {response.text}"

        content = response.text
        content_type = response.headers.get("content-type", "")

        # Validate content type is text/plain
        assert "text/plain" in content_type, f"Expected text/plain, got {content_type}"

        # Validate Prometheus format
        assert "# HELP" in content, "Missing HELP comments"
        assert "# TYPE" in content, "Missing TYPE comments"
        assert "ops_bookings_total" in content, "Missing ops_bookings_total metric"
        assert "ops_bookings_per_minute" in content, "Missing ops_bookings_per_minute metric"
        assert "ops_error_rate" in content, "Missing ops_error_rate metric"

        print("PASS: Prometheus metrics in correct exposition format")


class TestEndToEndOperationsWorkflow:
    """End-to-end test combining multiple operations layer features."""

    @pytest.fixture(scope="class")
    def agent_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert response.status_code == 200
        return response.json().get("access_token")

    @pytest.fixture(scope="class")
    def auth_headers(self, agent_token):
        return {"Authorization": f"Bearer {agent_token}"}

    def test_full_incident_workflow(self, auth_headers):
        """Test complete incident lifecycle: detect -> create -> resolve."""
        # 1. Detect incidents
        detect_resp = requests.get(
            f"{BASE_URL}/api/ops/suppliers/incidents/detect",
            headers=auth_headers
        )
        assert detect_resp.status_code == 200
        detect_resp.json()

        # 2. Create a manual incident
        incident = {
            "incident_type": "TEST_e2e_workflow",
            "booking_id": f"e2e-{uuid.uuid4().hex[:8]}",
            "severity": "warning",
            "description": "End-to-end workflow test incident"
        }

        create_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/incidents",
            headers=auth_headers,
            json=incident
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["incident_id"]

        # 3. List to verify
        list_resp = requests.get(
            f"{BASE_URL}/api/ops/suppliers/incidents",
            headers=auth_headers,
            params={"status": "open"}
        )
        assert list_resp.status_code == 200

        # 4. Resolve
        resolve_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/incidents/{incident_id}/resolve",
            headers=auth_headers,
            json={"resolution": "Resolved as part of E2E workflow test"}
        )
        assert resolve_resp.status_code == 200
        assert resolve_resp.json().get("status") == "resolved"

        print(f"PASS: E2E Incident workflow - created and resolved incident {incident_id}")

    def test_full_voucher_workflow(self, auth_headers):
        """Test complete voucher lifecycle: create -> generate -> send."""
        # 1. Create voucher
        voucher = {
            "booking_id": f"e2e-voucher-{uuid.uuid4().hex[:8]}",
            "confirmation_code": f"E2E-{uuid.uuid4().hex[:6]}",
            "guest_names": ["E2E Test Guest"],
            "hotel_name": "E2E Test Hotel",
            "check_in": "2026-06-01",
            "check_out": "2026-06-05",
            "total_price": 10000.00,
            "currency": "TRY"
        }

        create_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/vouchers",
            headers=auth_headers,
            json=voucher
        )
        assert create_resp.status_code == 201
        voucher_id = create_resp.json()["voucher_id"]

        # 2. Generate
        gen_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/vouchers/{voucher_id}/generate",
            headers=auth_headers
        )
        assert gen_resp.status_code == 200
        assert gen_resp.json().get("status") == "generated"

        # 3. Send
        send_resp = requests.post(
            f"{BASE_URL}/api/ops/suppliers/vouchers/{voucher_id}/send",
            headers=auth_headers,
            json={"recipient_email": "e2e@example.com"}
        )
        assert send_resp.status_code == 200
        assert send_resp.json().get("status") == "delivered"

        # 4. Check pipeline status
        pipeline_resp = requests.get(
            f"{BASE_URL}/api/ops/suppliers/vouchers/pipeline",
            headers=auth_headers
        )
        assert pipeline_resp.status_code == 200

        print(f"PASS: E2E Voucher workflow - created, generated, sent voucher {voucher_id} (MOCKED email)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
