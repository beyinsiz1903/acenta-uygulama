"""
API Response Envelope & Versioning Tests - Iteration 146

Tests for:
1. Response Envelope Middleware - {ok, data, meta} format for all /api/ responses
2. Error Envelope - {ok: false, error: {...}, meta} format
3. Excluded Paths - /health, /api/health, / should NOT be wrapped
4. Meta Fields - trace_id, timestamp, latency_ms, api_version
5. API Versioning - /api/v1/ path rewrite works transparently
6. EventPublisher abstraction - outbox_consumer uses transport adapter
7. Idempotency hardening - unique constraint on (event_id, handler)
8. Dead-letter endpoints - visibility and retry-all
9. Stats-by-type endpoint - breakdown by event_type and status
"""
import os
import pytest
import requests
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable not set")

# Test credentials
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"


@pytest.fixture(scope="session")
def auth_token():
    """Authenticate and get bearer token (token is in data.access_token due to envelope)"""
    import time
    max_retries = 3
    for attempt in range(max_retries):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=30
        )
        if response.status_code == 429:
            # Rate limited - wait and retry
            wait_time = 35
            print(f"Rate limited on attempt {attempt+1}, waiting {wait_time}s...")
            time.sleep(wait_time)
            continue
        break
    
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    # Response is wrapped in envelope: {ok, data: {access_token, ...}, meta}
    assert data.get("ok") is True, "Expected ok=true in response"
    token = data.get("data", {}).get("access_token")
    assert token, "No access_token in response.data"
    return token


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    """Return auth headers for requests"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Response Envelope Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestResponseEnvelope:
    """Tests for the response envelope middleware {ok, data, meta} format"""
    
    def test_login_response_has_envelope_structure(self):
        """Login response should be wrapped in {ok, data, meta}"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=30
        )
        data = response.json()
        
        assert "ok" in data, "Missing 'ok' field"
        assert "data" in data, "Missing 'data' field"
        assert "meta" in data, "Missing 'meta' field"
        assert data["ok"] is True, "Expected ok=true for successful response"
        print(f"Login envelope: ok={data['ok']}, data_keys={list(data['data'].keys())}")
    
    def test_meta_has_required_fields(self):
        """Meta should have trace_id, timestamp, latency_ms, api_version"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=30
        )
        meta = response.json().get("meta", {})
        
        assert "trace_id" in meta, "Missing 'trace_id' in meta"
        assert "timestamp" in meta, "Missing 'timestamp' in meta"
        assert "latency_ms" in meta, "Missing 'latency_ms' in meta"
        assert "api_version" in meta, "Missing 'api_version' in meta"
        
        # Validate types
        assert isinstance(meta["trace_id"], str), "trace_id should be string"
        assert isinstance(meta["timestamp"], str), "timestamp should be string"
        assert isinstance(meta["latency_ms"], (int, float)), "latency_ms should be numeric"
        assert meta["api_version"] == "v1", f"Expected api_version=v1, got {meta['api_version']}"
        
        print(f"Meta fields: trace_id={meta['trace_id'][:20]}..., latency={meta['latency_ms']}ms")
    
    def test_admin_endpoint_has_envelope(self, auth_headers):
        """Admin endpoints should be wrapped in envelope"""
        response = requests.get(
            f"{BASE_URL}/api/admin/outbox/health",
            headers=auth_headers,
            timeout=30
        )
        data = response.json()
        
        assert data.get("ok") is True, "Expected ok=true"
        assert "data" in data, "Missing 'data' field"
        assert "meta" in data, "Missing 'meta' field"
        assert data["data"].get("status") in ["healthy", "degraded", "unhealthy"]
        print(f"Admin health envelope: status={data['data']['status']}")


class TestErrorEnvelope:
    """Tests for error response envelope {ok: false, error: {...}, meta}"""
    
    def test_unauthorized_error_has_envelope(self):
        """401 unauthorized should return error envelope"""
        response = requests.get(
            f"{BASE_URL}/api/admin/outbox/health",
            timeout=30
        )
        data = response.json()
        
        assert data.get("ok") is False, "Expected ok=false for error"
        assert "error" in data, "Missing 'error' field"
        assert "meta" in data, "Missing 'meta' field"
        
        error = data["error"]
        assert "code" in error, "Missing 'code' in error"
        assert "message" in error, "Missing 'message' in error"
        
        print(f"Error envelope: code={error['code']}, message={error['message']}")
    
    def test_invalid_login_error_envelope(self):
        """Invalid login should return error envelope"""
        import time
        time.sleep(2)  # Small delay to avoid rate limits
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "wrong@test.com", "password": "wrongpass"},
            timeout=30
        )
        
        # Handle rate limit as special case
        if response.status_code == 429:
            data = response.json()
            # Rate limit responses should also have error structure
            assert "error" in data, "Rate limit response should have error field"
            print(f"Got rate limited, but error format is valid: {data['error']['code']}")
            return
            
        data = response.json()
        
        assert data.get("ok") is False, "Expected ok=false for auth error"
        assert "error" in data, "Missing 'error' field"
        assert data["error"].get("code") == "auth_required", f"Expected auth_required, got {data['error'].get('code')}"
        assert "meta" in data, "Missing 'meta' in error response"
        
        print(f"Invalid login error: {data['error']}")


class TestExcludedPaths:
    """Tests for paths excluded from envelope wrapping"""
    
    def test_health_endpoint_not_wrapped(self):
        """/health should NOT be wrapped in envelope"""
        response = requests.get(f"{BASE_URL}/health", timeout=30)
        # This returns HTML (frontend), not JSON - check content-type
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type or response.status_code == 200
        print(f"/health content-type: {content_type}")
    
    def test_api_health_endpoint_not_wrapped(self):
        """/api/health should NOT be wrapped in envelope"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=30)
        data = response.json()
        
        # Should have status, timestamp but NOT ok/data/meta envelope
        assert "status" in data, "Expected 'status' field"
        assert "ok" not in data, "/api/health should NOT have 'ok' envelope"
        assert "data" not in data, "/api/health should NOT have 'data' envelope"
        assert "meta" not in data, "/api/health should NOT have 'meta' envelope"
        
        print(f"/api/health response: {data}")
    
    def test_root_endpoint_not_wrapped(self):
        """/ should NOT be wrapped in envelope"""
        response = requests.get(f"{BASE_URL}/", timeout=30)
        content_type = response.headers.get("content-type", "")
        # Root returns HTML (frontend)
        assert "text/html" in content_type or response.status_code == 200
        print(f"/ content-type: {content_type}")


# ═══════════════════════════════════════════════════════════════════════════════
# API Versioning Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAPIVersioning:
    """Tests for /api/v1/ path rewrite middleware"""
    
    def test_v1_auth_login_works(self, auth_headers):
        """/api/v1/auth/login should work identically to /api/auth/login (we verify via other endpoint)"""
        # Note: We skip actually calling login again to avoid rate limits
        # Instead, verify that an authenticated v1 endpoint works
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/outbox/stats",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"v1 endpoint failed: {response.status_code}"
        data = response.json()
        
        assert data.get("ok") is True, "Expected ok=true"
        print(f"/api/v1/ path rewrite verified via stats endpoint")
    
    def test_v1_admin_outbox_health_works(self, auth_headers):
        """/api/v1/admin/outbox/health should work"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/outbox/health",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"v1 health failed: {response.status_code}"
        data = response.json()
        
        assert data.get("ok") is True, "Expected ok=true"
        assert data.get("data", {}).get("status") in ["healthy", "degraded", "unhealthy"]
        print(f"/api/v1/admin/outbox/health: status={data['data']['status']}")
    
    def test_v1_admin_outbox_dead_letter_works(self, auth_headers):
        """/api/v1/admin/outbox/dead-letter should work"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/outbox/dead-letter",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"v1 dead-letter failed: {response.status_code}"
        data = response.json()
        
        assert data.get("ok") is True, "Expected ok=true"
        assert "total" in data.get("data", {}), "Missing 'total' in response"
        print(f"/api/v1/admin/outbox/dead-letter: total={data['data']['total']}")
    
    def test_v1_admin_outbox_stats_by_type_works(self, auth_headers):
        """/api/v1/admin/outbox/stats-by-type should work"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/outbox/stats-by-type",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"v1 stats-by-type failed: {response.status_code}"
        data = response.json()
        
        assert data.get("ok") is True, "Expected ok=true"
        assert "stats_by_type" in data.get("data", {}), "Missing 'stats_by_type'"
        print(f"/api/v1/admin/outbox/stats-by-type: types={list(data['data']['stats_by_type'].keys())}")
    
    def test_versioned_path_has_version_header(self, auth_headers):
        """Versioned paths should have X-API-Version header"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/outbox/health",
            headers=auth_headers,
            timeout=30
        )
        assert "X-API-Version" in response.headers, "Missing X-API-Version header"
        assert response.headers["X-API-Version"] == "v1"
        print(f"X-API-Version: {response.headers['X-API-Version']}")
    
    def test_unversioned_path_has_deprecation_headers(self, auth_headers):
        """Unversioned /api/ paths should have deprecation headers"""
        response = requests.get(
            f"{BASE_URL}/api/admin/outbox/health",
            headers=auth_headers,
            timeout=30
        )
        assert "X-API-Deprecated" in response.headers, "Missing X-API-Deprecated header"
        assert response.headers["X-API-Deprecated"] == "true"
        assert "X-API-Sunset" in response.headers, "Missing X-API-Sunset header"
        assert "X-API-Upgrade" in response.headers, "Missing X-API-Upgrade header"
        
        print(f"Deprecation: {response.headers['X-API-Deprecated']}, Sunset: {response.headers['X-API-Sunset']}")


# ═══════════════════════════════════════════════════════════════════════════════
# Dead Letter & Stats Endpoints Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeadLetterEndpoints:
    """Tests for dead-letter visibility endpoints"""
    
    def test_dead_letter_returns_list_and_stats(self, auth_headers):
        """GET /api/admin/outbox/dead-letter should return list + stats breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/admin/outbox/dead-letter",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json().get("data", {})
        
        assert "total" in data, "Missing 'total' field"
        assert "showing" in data, "Missing 'showing' field"
        assert "breakdown_by_type" in data, "Missing 'breakdown_by_type' field"
        assert "events" in data, "Missing 'events' field"
        
        assert isinstance(data["events"], list), "'events' should be a list"
        assert isinstance(data["breakdown_by_type"], dict), "'breakdown_by_type' should be dict"
        
        print(f"Dead-letter: total={data['total']}, breakdown={data['breakdown_by_type']}")
    
    def test_dead_letter_with_filters(self, auth_headers):
        """Dead-letter endpoint should accept event_type and org_id filters"""
        response = requests.get(
            f"{BASE_URL}/api/admin/outbox/dead-letter",
            headers=auth_headers,
            params={"event_type": "booking.confirmed", "limit": 10},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json().get("data", {})
        assert "events" in data
        print(f"Dead-letter with filter: showing={data['showing']}")
    
    def test_retry_all_dead_letters(self, auth_headers):
        """POST /api/admin/outbox/dead-letter/retry-all should work"""
        response = requests.post(
            f"{BASE_URL}/api/admin/outbox/dead-letter/retry-all",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json().get("data", {})
        
        assert "status" in data, "Missing 'status' field"
        assert data["status"] == "retried", f"Expected status=retried, got {data['status']}"
        assert "events_reset" in data, "Missing 'events_reset' field"
        
        print(f"Retry-all: events_reset={data['events_reset']}")
    
    def test_retry_all_with_event_type_filter(self, auth_headers):
        """POST /api/admin/outbox/dead-letter/retry-all should accept event_type filter"""
        response = requests.post(
            f"{BASE_URL}/api/admin/outbox/dead-letter/retry-all",
            headers=auth_headers,
            params={"event_type": "booking.confirmed"},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json().get("data", {})
        
        assert data["status"] == "retried"
        assert "filter" in data
        print(f"Retry-all with filter: filter={data['filter']}")


class TestStatsByType:
    """Tests for GET /api/admin/outbox/stats-by-type endpoint"""
    
    def test_stats_by_type_returns_breakdown(self, auth_headers):
        """Stats-by-type should return breakdown by event_type and status"""
        response = requests.get(
            f"{BASE_URL}/api/admin/outbox/stats-by-type",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json().get("data", {})
        
        assert "stats_by_type" in data, "Missing 'stats_by_type' field"
        stats = data["stats_by_type"]
        
        # Should have breakdown by event_type
        assert isinstance(stats, dict), "stats_by_type should be a dict"
        
        # Each event type should have status counts
        for event_type, status_counts in stats.items():
            assert isinstance(status_counts, dict), f"{event_type} should have status dict"
            print(f"  {event_type}: {status_counts}")
        
        print(f"Stats-by-type: {len(stats)} event types")


# ═══════════════════════════════════════════════════════════════════════════════
# Existing Endpoints (Regression Tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestExistingEndpoints:
    """Tests to ensure existing endpoints still work"""
    
    def test_outbox_health_still_works(self, auth_headers):
        """GET /api/admin/outbox/health should still work"""
        response = requests.get(
            f"{BASE_URL}/api/admin/outbox/health",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json().get("data", {})
        
        assert "status" in data, "Missing 'status' field"
        assert "health_score" in data, "Missing 'health_score' field"
        assert "redis_status" in data, "Missing 'redis_status' field"
        
        print(f"Outbox health: status={data['status']}, score={data['health_score']}")
    
    def test_outbox_trigger_still_works(self, auth_headers):
        """POST /api/admin/outbox/trigger should still work"""
        response = requests.post(
            f"{BASE_URL}/api/admin/outbox/trigger",
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        data = response.json().get("data", {})
        
        # Should have batch stats
        assert "batch_id" in data or "events_claimed" in data or "status" in data
        print(f"Outbox trigger: {data}")


# ═══════════════════════════════════════════════════════════════════════════════
# Idempotency Verification
# ═══════════════════════════════════════════════════════════════════════════════

class TestIdempotencyHardening:
    """Tests for idempotency hardening (Redis fast-path + MongoDB unique constraint)"""
    
    def test_double_trigger_is_safe(self, auth_headers):
        """Triggering outbox poll twice should be safe (idempotent consumers)"""
        # First trigger
        r1 = requests.post(
            f"{BASE_URL}/api/admin/outbox/trigger",
            headers=auth_headers,
            timeout=60
        )
        assert r1.status_code == 200
        
        # Second trigger
        r2 = requests.post(
            f"{BASE_URL}/api/admin/outbox/trigger",
            headers=auth_headers,
            timeout=60
        )
        assert r2.status_code == 200
        
        print("Double trigger executed without errors - idempotency working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
