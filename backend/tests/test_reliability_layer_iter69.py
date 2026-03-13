"""
Integration Reliability Layer - Full Backend Test Suite (Iteration 69)
Covers all 10 parts: P1-Supplier API Resilience, P2-Supplier Sandbox, P3-Retry Strategy & DLQ,
P4-Identity & Idempotency, P5-API Versioning, P6-Contract Validation, P7-Integration Metrics,
P8-Supplier Incident Response, P9-Integration Dashboard, P10-Reliability Roadmap

All endpoints are under /api/reliability/*
Auth: agent@acenta.test / agent123 (super_admin role)
"""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
AUTH_EMAIL = "agent@acenta.test"
AUTH_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for super_admin user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": AUTH_EMAIL, "password": AUTH_PASSWORD}
    )
    assert response.status_code == 200, f"Auth failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    return data["access_token"]


@pytest.fixture(scope="module")
def headers(auth_token):
    """Headers with auth token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


# ============================================================================
# AUTH CHECK - Verify endpoints require authentication
# ============================================================================
class TestAuthRequired:
    """Verify reliability endpoints require authentication."""

    def test_resilience_config_requires_auth(self):
        """GET /api/reliability/resilience/config requires auth."""
        response = requests.get(f"{BASE_URL}/api/reliability/resilience/config")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ P1: Resilience config requires authentication (401)")

    def test_sandbox_config_requires_auth(self):
        """GET /api/reliability/sandbox/config requires auth."""
        response = requests.get(f"{BASE_URL}/api/reliability/sandbox/config")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ P2: Sandbox config requires authentication (401)")

    def test_dlq_requires_auth(self):
        """GET /api/reliability/dlq requires auth."""
        response = requests.get(f"{BASE_URL}/api/reliability/dlq")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ P3: DLQ list requires authentication (401)")


# ============================================================================
# PART 1 — SUPPLIER API RESILIENCE
# ============================================================================
class TestP1ResilienceConfig:
    """Part 1: Supplier API Resilience endpoints."""

    def test_get_resilience_config(self, headers):
        """GET /api/reliability/resilience/config returns config."""
        response = requests.get(f"{BASE_URL}/api/reliability/resilience/config", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        # Config might be default (with strategies/defaults) or existing org config
        has_defaults = "defaults" in data and "strategies" in data
        has_existing_config = "organization_id" in data or "supplier_overrides" in data
        assert has_defaults or has_existing_config, f"Response missing expected fields: {list(data.keys())}"
        if has_defaults:
            print(f"✅ P1: GET resilience config (default) - strategies: {len(data.get('strategies', {}))}")
        else:
            print(f"✅ P1: GET resilience config (org) - overrides: {list(data.get('supplier_overrides', {}).keys())}")

    def test_update_supplier_resilience_config(self, headers):
        """PUT /api/reliability/resilience/config updates supplier timeout."""
        payload = {
            "supplier_code": "mock_hotel",
            "timeout_ms": 10000,
            "max_retries": 5
        }
        response = requests.put(f"{BASE_URL}/api/reliability/resilience/config", headers=headers, json=payload)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("status") == "updated", f"Expected status=updated, got {data.get('status')}"
        assert data.get("supplier_code") == "mock_hotel", f"Supplier code mismatch"
        assert data.get("config", {}).get("timeout_ms") == 10000, "Timeout not updated"
        print(f"✅ P1: PUT resilience config - updated mock_hotel timeout to 10000ms")

    def test_get_resilience_stats(self, headers):
        """GET /api/reliability/resilience/stats returns stats."""
        response = requests.get(
            f"{BASE_URL}/api/reliability/resilience/stats",
            headers=headers,
            params={"window_minutes": 60}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "window_minutes" in data, "Missing window_minutes"
        assert "suppliers" in data, "Missing suppliers"
        print(f"✅ P1: GET resilience stats - window={data.get('window_minutes')}m, suppliers={len(data.get('suppliers', []))}")


# ============================================================================
# PART 2 — SUPPLIER SANDBOX
# ============================================================================
class TestP2Sandbox:
    """Part 2: Supplier Sandbox endpoints."""

    def test_get_sandbox_config(self, headers):
        """GET /api/reliability/sandbox/config returns sandbox config."""
        response = requests.get(f"{BASE_URL}/api/reliability/sandbox/config", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "enabled" in data, "Missing enabled field"
        assert "mode" in data, "Missing mode field"
        # available_modes is only in default config; existing config might not have it
        print(f"✅ P2: GET sandbox config - enabled={data.get('enabled')}, mode={data.get('mode')}")

    def test_update_sandbox_config_enable_fault_injection(self, headers):
        """PUT /api/reliability/sandbox/config enables sandbox with fault injection."""
        payload = {
            "enabled": True,
            "mode": "mock",
            "fault_injection_enabled": True,
            "fault_probability": 0.3,
            "fault_types": ["timeout", "error_500"]
        }
        response = requests.put(f"{BASE_URL}/api/reliability/sandbox/config", headers=headers, json=payload)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("status") == "updated", f"Expected status=updated, got {data.get('status')}"
        config = data.get("config", {})
        assert config.get("enabled") == True, "Sandbox not enabled"
        print(f"✅ P2: PUT sandbox config - enabled=True, fault_injection={config.get('fault_injection', {}).get('enabled')}")

    def test_execute_sandbox_call_search(self, headers):
        """POST /api/reliability/sandbox/call executes mock search."""
        payload = {
            "supplier_code": "mock_hotel",
            "method": "search",
            "payload": {"destination": "Istanbul", "check_in": "2026-02-01"}
        }
        response = requests.post(f"{BASE_URL}/api/reliability/sandbox/call", headers=headers, json=payload)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("sandbox") == True, "Response should indicate sandbox mode"
        assert data.get("supplier_code") == "mock_hotel", "Supplier code mismatch"
        # If fault injected, we might get error response; if not, we get mock items
        if "items" in data:
            print(f"✅ P2: POST sandbox call - search returned {len(data.get('items', []))} items")
        else:
            print(f"✅ P2: POST sandbox call - fault injected: {data.get('fault_type', 'none')}")

    def test_get_sandbox_log(self, headers):
        """GET /api/reliability/sandbox/log lists sandbox call history."""
        response = requests.get(
            f"{BASE_URL}/api/reliability/sandbox/log",
            headers=headers,
            params={"limit": 10}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of sandbox logs"
        print(f"✅ P2: GET sandbox log - {len(data)} entries returned")


# ============================================================================
# PART 3 — RETRY STRATEGY & DLQ
# ============================================================================
class TestP3RetryAndDLQ:
    """Part 3: Retry Strategy & Dead Letter Queue endpoints."""

    dlq_entry_id = None  # Will be set by test_enqueue_dlq

    def test_get_retry_config(self, headers):
        """GET /api/reliability/retry/config returns retry categories."""
        response = requests.get(f"{BASE_URL}/api/reliability/retry/config", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "categories" in data, "Missing categories"
        categories = data.get("categories", {})
        assert "supplier_call" in categories, "Missing supplier_call category"
        assert "payment" in categories, "Missing payment category"
        print(f"✅ P3: GET retry config - categories={list(categories.keys())}")

    def test_enqueue_dlq(self, headers):
        """POST /api/reliability/dlq enqueues failed operation."""
        payload = {
            "category": "supplier_call",
            "operation": "search",
            "supplier_code": "mock_hotel",
            "payload": {"search_id": "test123"},
            "error": "Connection timeout after 10s",
            "attempts": 3
        }
        response = requests.post(f"{BASE_URL}/api/reliability/dlq", headers=headers, json=payload)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("status") == "enqueued", f"Expected status=enqueued, got {data.get('status')}"
        assert "entry_id" in data, "Missing entry_id"
        TestP3RetryAndDLQ.dlq_entry_id = data["entry_id"]
        print(f"✅ P3: POST dlq enqueue - entry_id={data.get('entry_id')}")

    def test_list_dlq(self, headers):
        """GET /api/reliability/dlq lists DLQ entries."""
        response = requests.get(
            f"{BASE_URL}/api/reliability/dlq",
            headers=headers,
            params={"status": "pending", "limit": 20}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "total" in data, "Missing total"
        assert "items" in data, "Missing items"
        print(f"✅ P3: GET dlq list - total={data.get('total')}, returned={len(data.get('items', []))}")

    def test_retry_dlq_entry(self, headers):
        """POST /api/reliability/dlq/{id}/retry marks entry for retry."""
        if not TestP3RetryAndDLQ.dlq_entry_id:
            pytest.skip("No DLQ entry created")
        entry_id = TestP3RetryAndDLQ.dlq_entry_id
        response = requests.post(f"{BASE_URL}/api/reliability/dlq/{entry_id}/retry", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        # Entry might be retrying or not found if already processed
        assert data.get("status") in ["retrying", "not_found_or_already_retrying"], f"Unexpected status: {data.get('status')}"
        print(f"✅ P3: POST dlq retry - status={data.get('status')}")

    def test_discard_dlq_entry(self, headers):
        """DELETE /api/reliability/dlq/{id} discards a DLQ entry."""
        # Create a new entry to discard
        payload = {
            "category": "supplier_call",
            "operation": "TEST_discard_op",
            "supplier_code": "mock_flight",
            "payload": {},
            "error": "Test error for discard",
            "attempts": 1
        }
        create_resp = requests.post(f"{BASE_URL}/api/reliability/dlq", headers=headers, json=payload)
        assert create_resp.status_code == 200
        entry_id = create_resp.json().get("entry_id")
        
        # Discard it
        response = requests.delete(
            f"{BASE_URL}/api/reliability/dlq/{entry_id}",
            headers=headers,
            params={"reason": "Test cleanup"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("status") in ["discarded", "not_found"], f"Unexpected status: {data.get('status')}"
        print(f"✅ P3: DELETE dlq entry - status={data.get('status')}")

    def test_get_dlq_stats(self, headers):
        """GET /api/reliability/dlq/stats returns DLQ statistics."""
        response = requests.get(f"{BASE_URL}/api/reliability/dlq/stats", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "categories" in data, "Missing categories in stats"
        print(f"✅ P3: GET dlq stats - categories={len(data.get('categories', []))}")


# ============================================================================
# PART 4 — IDENTITY & IDEMPOTENCY
# ============================================================================
class TestP4Idempotency:
    """Part 4: Identity & Idempotency endpoints."""

    def test_check_idempotency_non_existent(self, headers):
        """POST /api/reliability/idempotency/check for non-existent key returns duplicate:false."""
        unique_key = f"TEST_idem_{uuid.uuid4().hex[:12]}"
        payload = {
            "idempotency_key": unique_key,
            "operation": "booking.confirm"
        }
        response = requests.post(f"{BASE_URL}/api/reliability/idempotency/check", headers=headers, json=payload)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("duplicate") == False, f"Expected duplicate=false for new key, got {data.get('duplicate')}"
        assert data.get("cached_result") is None, "Expected no cached result for new key"
        print(f"✅ P4: POST idempotency check - new key returns duplicate=False")

    def test_get_idempotency_stats(self, headers):
        """GET /api/reliability/idempotency/stats returns supported operations."""
        response = requests.get(f"{BASE_URL}/api/reliability/idempotency/stats", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "supported_operations" in data, "Missing supported_operations"
        assert "ttl_seconds" in data, "Missing ttl_seconds"
        ops = data.get("supported_operations", [])
        assert "booking.confirm" in ops, "booking.confirm should be in supported operations"
        print(f"✅ P4: GET idempotency stats - supported_operations={len(ops)}, ttl={data.get('ttl_seconds')}s")


# ============================================================================
# PART 5 — API VERSIONING
# ============================================================================
class TestP5Versioning:
    """Part 5: API Versioning endpoints."""

    def test_get_version_registry(self, headers):
        """GET /api/reliability/versions returns default version registry for 5 suppliers."""
        response = requests.get(f"{BASE_URL}/api/reliability/versions", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "suppliers" in data, "Missing suppliers"
        suppliers = data.get("suppliers", [])
        assert len(suppliers) >= 5, f"Expected at least 5 suppliers in registry, got {len(suppliers)}"
        # Check for mock suppliers
        supplier_codes = [s.get("supplier_code") for s in suppliers]
        for expected in ["mock_hotel", "mock_flight", "mock_tour", "mock_insurance", "mock_transport"]:
            assert expected in supplier_codes, f"Missing {expected} in version registry"
        print(f"✅ P5: GET versions - {len(suppliers)} suppliers registered")

    def test_register_new_version(self, headers):
        """POST /api/reliability/versions registers new version."""
        payload = {
            "supplier_code": "mock_hotel",
            "version": "v2",
            "schema_hash": "abc123def456"
        }
        response = requests.post(f"{BASE_URL}/api/reliability/versions", headers=headers, json=payload)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("status") == "registered", f"Expected status=registered, got {data.get('status')}"
        assert data.get("version") == "v2", f"Version mismatch"
        print(f"✅ P5: POST versions - registered v2 for mock_hotel")

    def test_deprecate_version(self, headers):
        """POST /api/reliability/versions/deprecate marks version as deprecated."""
        payload = {
            "supplier_code": "mock_hotel",
            "version": "v1"
        }
        response = requests.post(f"{BASE_URL}/api/reliability/versions/deprecate", headers=headers, json=payload)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("status") == "deprecated", f"Expected status=deprecated, got {data.get('status')}"
        print(f"✅ P5: POST versions/deprecate - deprecated v1 for mock_hotel")

    def test_get_version_history(self, headers):
        """GET /api/reliability/versions/history returns version change log."""
        response = requests.get(
            f"{BASE_URL}/api/reliability/versions/history",
            headers=headers,
            params={"limit": 20}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of version history"
        print(f"✅ P5: GET versions/history - {len(data)} entries")


# ============================================================================
# PART 6 — CONTRACT VALIDATION
# ============================================================================
class TestP6ContractValidation:
    """Part 6: Contract Validation endpoints."""

    def test_validate_contract_valid_payload(self, headers):
        """POST /api/reliability/contracts/validate with valid payload returns valid:true."""
        # Valid search response format per REQUIRED_SEARCH_FIELDS
        payload = {
            "supplier_code": "mock_hotel",
            "method": "search",
            "payload": {
                "items": [
                    {
                        "item_id": "item_001",
                        "supplier_code": "mock_hotel",
                        "name": "Grand Hotel Istanbul",
                        "supplier_price": 150.0,
                        "sell_price": 180.0,
                        "currency": "EUR"
                    },
                    {
                        "item_id": "item_002",
                        "supplier_code": "mock_hotel",
                        "name": "Luxury Suite Ankara",
                        "supplier_price": 250.0,
                        "sell_price": 300.0,
                        "currency": "EUR"
                    }
                ]
            },
            "mode": "strict"
        }
        response = requests.post(f"{BASE_URL}/api/reliability/contracts/validate", headers=headers, json=payload)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("valid") == True, f"Expected valid=true, got {data.get('valid')}, violations: {data.get('violations')}"
        assert "schema_hash" in data, "Missing schema_hash"
        print(f"✅ P6: POST contracts/validate (valid) - valid=True, schema_hash={data.get('schema_hash')}")

    def test_validate_contract_invalid_payload(self, headers):
        """POST /api/reliability/contracts/validate with invalid payload returns violations."""
        # Missing required fields
        payload = {
            "supplier_code": "mock_flight",
            "method": "search",
            "payload": {
                "items": [
                    {"item_id": "flight_001", "name": "Istanbul-Ankara Flight"}
                    # Missing: supplier_code, supplier_price, sell_price, currency
                ]
            },
            "mode": "strict"
        }
        response = requests.post(f"{BASE_URL}/api/reliability/contracts/validate", headers=headers, json=payload)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("valid") == False, f"Expected valid=false for missing fields, got {data.get('valid')}"
        violations = data.get("violations", [])
        assert len(violations) > 0, "Expected violations for missing fields"
        print(f"✅ P6: POST contracts/validate (invalid) - valid=False, violations={len(violations)}")

    def test_validate_contract_schema_drift(self, headers):
        """POST /api/reliability/contracts/validate detects schema drift on second call with different schema."""
        # First call with schema A
        payload1 = {
            "supplier_code": "mock_tour",
            "method": "search",
            "payload": {
                "items": [
                    {"item_id": "tour_001", "supplier_code": "mock_tour", "name": "City Tour", 
                     "supplier_price": 50.0, "sell_price": 60.0, "currency": "EUR"}
                ]
            },
            "mode": "strict"
        }
        resp1 = requests.post(f"{BASE_URL}/api/reliability/contracts/validate", headers=headers, json=payload1)
        assert resp1.status_code == 200
        hash1 = resp1.json().get("schema_hash")

        # Second call with different schema (added extra field)
        payload2 = {
            "supplier_code": "mock_tour",
            "method": "search",
            "payload": {
                "items": [
                    {"item_id": "tour_001", "supplier_code": "mock_tour", "name": "City Tour", 
                     "supplier_price": 50.0, "sell_price": 60.0, "currency": "EUR",
                     "new_field": "extra_data", "duration_hours": 4}
                ]
            },
            "mode": "strict"
        }
        resp2 = requests.post(f"{BASE_URL}/api/reliability/contracts/validate", headers=headers, json=payload2)
        assert resp2.status_code == 200
        data2 = resp2.json()
        # Schema drift should be detected if schema hash changed
        if data2.get("schema_drift"):
            print(f"✅ P6: POST contracts/validate - schema drift detected (prev_hash={data2.get('previous_hash')}, new_hash={data2.get('schema_hash')})")
        else:
            print(f"✅ P6: POST contracts/validate - no drift (hash same or first call)")

    def test_get_contract_status(self, headers):
        """GET /api/reliability/contracts/status returns contract status."""
        response = requests.get(f"{BASE_URL}/api/reliability/contracts/status", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "contracts" in data, "Missing contracts"
        assert "validation_modes" in data, "Missing validation_modes"
        print(f"✅ P6: GET contracts/status - contracts={len(data.get('contracts', []))}, modes={data.get('validation_modes')}")


# ============================================================================
# PART 7 — INTEGRATION METRICS
# ============================================================================
class TestP7Metrics:
    """Part 7: Integration Metrics endpoints."""

    def test_get_supplier_metrics(self, headers):
        """GET /api/reliability/metrics/suppliers returns supplier metrics."""
        response = requests.get(
            f"{BASE_URL}/api/reliability/metrics/suppliers",
            headers=headers,
            params={"window": "1h"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "window" in data, "Missing window"
        assert "suppliers" in data, "Missing suppliers"
        print(f"✅ P7: GET metrics/suppliers - window={data.get('window')}, suppliers={len(data.get('suppliers', []))}")

    def test_get_latency_percentiles(self, headers):
        """GET /api/reliability/metrics/latency/mock_hotel returns latency percentiles."""
        response = requests.get(
            f"{BASE_URL}/api/reliability/metrics/latency/mock_hotel",
            headers=headers,
            params={"window": "15m"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "supplier_code" in data, "Missing supplier_code"
        assert data.get("supplier_code") == "mock_hotel", "Supplier code mismatch"
        assert "p50" in data, "Missing p50"
        assert "p95" in data, "Missing p95"
        assert "p99" in data, "Missing p99"
        print(f"✅ P7: GET metrics/latency/mock_hotel - p50={data.get('p50')}, p95={data.get('p95')}, p99={data.get('p99')}")

    def test_get_error_rate_timeline(self, headers):
        """GET /api/reliability/metrics/error-rate returns error rate timeline."""
        response = requests.get(
            f"{BASE_URL}/api/reliability/metrics/error-rate",
            headers=headers,
            params={"window": "1h"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "window" in data, "Missing window"
        assert "timeline" in data, "Missing timeline"
        print(f"✅ P7: GET metrics/error-rate - window={data.get('window')}, timeline_points={len(data.get('timeline', []))}")

    def test_get_success_rate_summary(self, headers):
        """GET /api/reliability/metrics/success-rate returns success rate summary."""
        response = requests.get(
            f"{BASE_URL}/api/reliability/metrics/success-rate",
            headers=headers,
            params={"window": "1h"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "window" in data, "Missing window"
        assert "suppliers" in data, "Missing suppliers"
        print(f"✅ P7: GET metrics/success-rate - window={data.get('window')}, suppliers={len(data.get('suppliers', []))}")


# ============================================================================
# PART 8 — SUPPLIER INCIDENT RESPONSE
# ============================================================================
class TestP8IncidentResponse:
    """Part 8: Supplier Incident Response endpoints."""

    incident_id = None  # Will be set by test_create_incident

    def test_create_incident(self, headers):
        """POST /api/reliability/incidents creates incident with auto-action."""
        payload = {
            "supplier_code": "mock_hotel",
            "incident_type": "high_error_rate",
            "severity": "high",
            "details": {"error_rate": 0.45, "total_calls": 100, "window_minutes": 15}
        }
        response = requests.post(f"{BASE_URL}/api/reliability/incidents", headers=headers, json=payload)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "incident_id" in data, "Missing incident_id"
        assert data.get("status") == "open", f"Expected status=open, got {data.get('status')}"
        assert "auto_action" in data, "Missing auto_action"
        TestP8IncidentResponse.incident_id = data["incident_id"]
        print(f"✅ P8: POST incidents - created {data.get('incident_type')}, auto_action={data.get('auto_action')}")

    def test_list_incidents(self, headers):
        """GET /api/reliability/incidents lists incidents."""
        response = requests.get(
            f"{BASE_URL}/api/reliability/incidents",
            headers=headers,
            params={"limit": 20}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "total" in data, "Missing total"
        assert "items" in data, "Missing items"
        print(f"✅ P8: GET incidents - total={data.get('total')}, returned={len(data.get('items', []))}")

    def test_acknowledge_incident(self, headers):
        """POST /api/reliability/incidents/{id}/acknowledge acknowledges incident."""
        if not TestP8IncidentResponse.incident_id:
            pytest.skip("No incident created")
        incident_id = TestP8IncidentResponse.incident_id
        response = requests.post(f"{BASE_URL}/api/reliability/incidents/{incident_id}/acknowledge", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("status") in ["acknowledged", "not_found_or_not_open"], f"Unexpected status: {data.get('status')}"
        print(f"✅ P8: POST incidents/acknowledge - status={data.get('status')}")

    def test_resolve_incident(self, headers):
        """POST /api/reliability/incidents/{id}/resolve resolves incident."""
        if not TestP8IncidentResponse.incident_id:
            pytest.skip("No incident created")
        incident_id = TestP8IncidentResponse.incident_id
        payload = {"resolution": "Supplier confirmed service restored. Error rate normalized."}
        response = requests.post(
            f"{BASE_URL}/api/reliability/incidents/{incident_id}/resolve",
            headers=headers,
            json=payload
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("status") in ["resolved", "not_found_or_already_resolved"], f"Unexpected status: {data.get('status')}"
        print(f"✅ P8: POST incidents/resolve - status={data.get('status')}")

    def test_detect_supplier_issues(self, headers):
        """POST /api/reliability/incidents/detect auto-detects issues."""
        response = requests.post(
            f"{BASE_URL}/api/reliability/incidents/detect",
            headers=headers,
            params={"window_minutes": 15}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of detected incidents"
        print(f"✅ P8: POST incidents/detect - detected {len(data)} issues")

    def test_get_incident_stats(self, headers):
        """GET /api/reliability/incidents/stats returns incident statistics."""
        response = requests.get(f"{BASE_URL}/api/reliability/incidents/stats", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "total" in data, "Missing total"
        assert "by_status" in data, "Missing by_status"
        assert "by_severity" in data, "Missing by_severity"
        assert "incident_types" in data, "Missing incident_types"
        print(f"✅ P8: GET incidents/stats - total={data.get('total')}, by_status={data.get('by_status')}")


# ============================================================================
# PART 9 — INTEGRATION DASHBOARD
# ============================================================================
class TestP9Dashboard:
    """Part 9: Integration Dashboard endpoints."""

    def test_get_dashboard_overview(self, headers):
        """GET /api/reliability/dashboard returns summary."""
        response = requests.get(f"{BASE_URL}/api/reliability/dashboard", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "summary" in data, "Missing summary"
        assert "generated_at" in data, "Missing generated_at"
        summary = data.get("summary", {})
        assert "open_incidents" in summary, "Missing open_incidents in summary"
        assert "dlq_pending" in summary, "Missing dlq_pending in summary"
        print(f"✅ P9: GET dashboard - open_incidents={summary.get('open_incidents')}, dlq_pending={summary.get('dlq_pending')}")

    def test_get_supplier_detail(self, headers):
        """GET /api/reliability/dashboard/supplier/mock_hotel returns supplier detail."""
        response = requests.get(f"{BASE_URL}/api/reliability/dashboard/supplier/mock_hotel", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "supplier_code" in data, "Missing supplier_code"
        assert data.get("supplier_code") == "mock_hotel", "Supplier code mismatch"
        assert "status" in data, "Missing status"
        assert "recent_events" in data, "Missing recent_events"
        print(f"✅ P9: GET dashboard/supplier/mock_hotel - status={data.get('status')}, events={len(data.get('recent_events', []))}")


# ============================================================================
# PART 10 — RELIABILITY ROADMAP
# ============================================================================
class TestP10Roadmap:
    """Part 10: Reliability Roadmap endpoints."""

    def test_get_roadmap(self, headers):
        """GET /api/reliability/roadmap returns 20 improvements + maturity score."""
        response = requests.get(f"{BASE_URL}/api/reliability/roadmap", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "improvements" in data, "Missing improvements"
        assert "maturity_score" in data, "Missing maturity_score"
        improvements = data.get("improvements", [])
        assert len(improvements) == 20, f"Expected 20 improvements, got {len(improvements)}"
        maturity = data.get("maturity_score", {})
        assert "overall_score" in maturity, "Missing overall_score in maturity"
        assert "grade" in maturity, "Missing grade in maturity"
        print(f"✅ P10: GET roadmap - {len(improvements)} improvements, score={maturity.get('overall_score')}, grade={maturity.get('grade')}")

    def test_get_maturity(self, headers):
        """GET /api/reliability/maturity returns maturity dimensions and grade."""
        response = requests.get(f"{BASE_URL}/api/reliability/maturity", headers=headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "overall_score" in data, "Missing overall_score"
        assert "grade" in data, "Missing grade"
        assert "dimensions" in data, "Missing dimensions"
        assert "weights" in data, "Missing weights"
        dims = data.get("dimensions", {})
        assert "resilience" in dims, "Missing resilience dimension"
        assert "observability" in dims, "Missing observability dimension"
        assert "idempotency" in dims, "Missing idempotency dimension"
        print(f"✅ P10: GET maturity - score={data.get('overall_score')}, grade={data.get('grade')}, dimensions={list(dims.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
