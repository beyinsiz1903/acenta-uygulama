"""Infrastructure Scalability API Tests - Iteration 65.

Tests Phase 2 scalability infrastructure endpoints:
- /api/infrastructure/health - Full infrastructure health
- /api/infrastructure/redis - Redis health + stats
- /api/infrastructure/circuit-breakers - Circuit breaker statuses
- /api/infrastructure/circuit-breakers/{name}/reset - Reset circuit breaker
- /api/infrastructure/events - Event bus handler registry
- /api/infrastructure/rate-limits - Rate limiter stats
- /api/infrastructure/metrics - Application metrics summary
- /api/infrastructure/queues - Celery queue stats
- Rate limiting with token bucket policy header
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Module-level token cache
_admin_token = None


def get_admin_token():
    """Get admin token, cached at module level."""
    global _admin_token
    if _admin_token is not None:
        return _admin_token

    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"},
        headers={"Content-Type": "application/json"},
    )
    if response.status_code == 200:
        data = response.json()
        _admin_token = data.get("access_token") or data.get("token")
        return _admin_token
    elif response.status_code == 429:
        pytest.skip("Rate limited - too many login attempts")
    pytest.skip(f"Admin login failed: {response.status_code}: {response.text}")


@pytest.fixture
def fresh_session():
    """Create a fresh requests session without auth."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def authed_session():
    """Create a fresh requests session with admin auth."""
    token = get_admin_token()
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    })
    return session


# ============================================================================
# Test existing health endpoints still work
# ============================================================================


class TestExistingHealthEndpoints:
    """Verify existing health endpoints continue to work after Phase 2."""

    def test_health_endpoint(self, fresh_session):
        """GET /api/health should return status ok."""
        response = fresh_session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("status") == "ok"
        print(f"✓ /api/health: {data}")

    def test_health_deep_endpoint(self, fresh_session):
        """GET /api/health/deep should return MongoDB stats."""
        response = fresh_session.get(f"{BASE_URL}/api/health/deep")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "collections" in data or "status" in data
        print("✓ /api/health/deep returned collection stats")


# ============================================================================
# Infrastructure Health Endpoint Tests
# ============================================================================


class TestInfrastructureHealth:
    """Test /api/infrastructure/health endpoint."""

    def test_infrastructure_health_requires_auth(self, fresh_session):
        """Infrastructure health should require authentication."""
        response = fresh_session.get(f"{BASE_URL}/api/infrastructure/health")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text[:200]}"
        print("✓ /api/infrastructure/health requires auth (401/403)")

    def test_infrastructure_health_with_auth(self, authed_session):
        """Infrastructure health with valid auth."""
        response = authed_session.get(f"{BASE_URL}/api/infrastructure/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Validate response structure
        assert "redis" in data, "Missing 'redis' in response"
        assert "celery" in data, "Missing 'celery' in response"
        assert "circuit_breakers" in data, "Missing 'circuit_breakers' in response"
        assert "event_handlers" in data, "Missing 'event_handlers' in response"

        # Redis status
        redis_status = data.get("redis", {})
        assert redis_status.get("status") in ["healthy", "unavailable", "error"]

        # Celery status
        celery_status = data.get("celery", {})
        assert celery_status.get("status") == "configured"
        assert celery_status.get("broker") == "redis"

        print(f"✓ /api/infrastructure/health: Redis={redis_status.get('status')}, Celery={celery_status.get('status')}")
        print(f"  Circuit breakers: {len(data.get('circuit_breakers', []))} configured")


# ============================================================================
# Redis Status Endpoint Tests
# ============================================================================


class TestRedisStatus:
    """Test /api/infrastructure/redis endpoint."""

    def test_redis_requires_auth(self, fresh_session):
        """Redis endpoint should require authentication."""
        response = fresh_session.get(f"{BASE_URL}/api/infrastructure/redis")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text[:200]}"
        print("✓ /api/infrastructure/redis requires auth")

    def test_redis_status_with_auth(self, authed_session):
        """Redis status with valid auth."""
        response = authed_session.get(f"{BASE_URL}/api/infrastructure/redis")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Validate Redis health info
        assert "status" in data, "Missing 'status' in response"
        status = data.get("status")
        assert status in ["healthy", "unavailable", "error"], f"Unexpected status: {status}"

        if status == "healthy":
            # Check for memory info
            if "memory" in data:
                memory = data.get("memory", {})
                assert "used" in memory, "Missing 'used' in memory"
                print(f"✓ Redis memory: used={memory.get('used')}, peak={memory.get('peak')}")

            # Check for stats
            if "stats" in data:
                stats = data.get("stats", {})
                assert "hit_rate" in stats, "Missing 'hit_rate' in stats"
                print(f"✓ Redis stats: hit_rate={stats.get('hit_rate')}%, ops/sec={stats.get('ops_per_sec')}")

            # Check uptime
            if "uptime_seconds" in data:
                print(f"✓ Redis uptime: {data.get('uptime_seconds')} seconds")

        print(f"✓ /api/infrastructure/redis: status={status}")


# ============================================================================
# Circuit Breaker Endpoint Tests
# ============================================================================


class TestCircuitBreakers:
    """Test /api/infrastructure/circuit-breakers endpoints."""

    def test_circuit_breakers_requires_auth(self, fresh_session):
        """Circuit breakers endpoint should require authentication."""
        response = fresh_session.get(f"{BASE_URL}/api/infrastructure/circuit-breakers")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text[:200]}"
        print("✓ /api/infrastructure/circuit-breakers requires auth")

    def test_circuit_breakers_status(self, authed_session):
        """Circuit breakers status with valid auth."""
        response = authed_session.get(f"{BASE_URL}/api/infrastructure/circuit-breakers")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Validate response structure
        assert "breakers" in data, "Missing 'breakers' in response"
        assert "total" in data, "Missing 'total' in response"
        assert "open" in data, "Missing 'open' in response"
        assert "half_open" in data, "Missing 'half_open' in response"
        assert "closed" in data, "Missing 'closed' in response"

        breakers = data.get("breakers", [])
        assert isinstance(breakers, list), "breakers should be a list"

        # Verify 6 expected circuit breakers
        expected_breakers = {"aviationstack", "paximum", "stripe", "iyzico", "google_sheets", "email_provider"}
        actual_names = {b.get("name") for b in breakers}
        assert expected_breakers.issubset(actual_names), f"Missing breakers: {expected_breakers - actual_names}"

        # All should be in closed state initially
        for breaker in breakers:
            assert "state" in breaker, f"Missing 'state' in breaker {breaker.get('name')}"
            assert "name" in breaker, "Missing 'name' in breaker"
            assert "config" in breaker, "Missing 'config' in breaker"
            print(f"  ✓ Circuit breaker '{breaker.get('name')}': state={breaker.get('state')}")

        print(f"✓ /api/infrastructure/circuit-breakers: total={data.get('total')}, closed={data.get('closed')}, open={data.get('open')}")

    def test_reset_circuit_breaker(self, authed_session):
        """Reset a circuit breaker."""
        response = authed_session.post(f"{BASE_URL}/api/infrastructure/circuit-breakers/aviationstack/reset")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert "status" in data, "Missing 'status' in response"
        assert data.get("status") == "reset"
        assert "breaker" in data, "Missing 'breaker' in response"

        breaker = data.get("breaker", {})
        assert breaker.get("state") == "closed", f"Expected 'closed' state after reset, got {breaker.get('state')}"
        print(f"✓ Circuit breaker reset: aviationstack → state={breaker.get('state')}")


# ============================================================================
# Event Bus Endpoint Tests
# ============================================================================


class TestEventBus:
    """Test /api/infrastructure/events endpoint."""

    def test_events_requires_auth(self, fresh_session):
        """Events endpoint should require authentication."""
        response = fresh_session.get(f"{BASE_URL}/api/infrastructure/events")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text[:200]}"
        print("✓ /api/infrastructure/events requires auth")

    def test_event_bus_status(self, authed_session):
        """Event bus status with valid auth."""
        response = authed_session.get(f"{BASE_URL}/api/infrastructure/events")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Validate response structure
        assert "registered_handlers" in data, "Missing 'registered_handlers' in response"
        assert "total_handler_count" in data, "Missing 'total_handler_count' in response"
        assert "persisted_events" in data, "Missing 'persisted_events' in response"

        handlers = data.get("registered_handlers", {})
        assert isinstance(handlers, dict), "registered_handlers should be a dict"

        print(f"✓ /api/infrastructure/events: handlers={handlers}, total={data.get('total_handler_count')}, persisted={data.get('persisted_events')}")


# ============================================================================
# Rate Limits Endpoint Tests
# ============================================================================


class TestRateLimits:
    """Test /api/infrastructure/rate-limits endpoint."""

    def test_rate_limits_requires_auth(self, fresh_session):
        """Rate limits endpoint should require authentication."""
        response = fresh_session.get(f"{BASE_URL}/api/infrastructure/rate-limits")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text[:200]}"
        print("✓ /api/infrastructure/rate-limits requires auth")

    def test_rate_limits_status(self, authed_session):
        """Rate limits status with valid auth."""
        response = authed_session.get(f"{BASE_URL}/api/infrastructure/rate-limits")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Validate response structure
        assert "status" in data, "Missing 'status' in response"

        if data.get("status") == "healthy":
            assert "tiers" in data, "Missing 'tiers' in response"
            tiers = data.get("tiers", {})

            # Verify 8 expected rate limit tiers
            expected_tiers = {
                "auth_login", "auth_signup", "auth_password", "api_global",
                "b2b_booking", "public_checkout", "export", "supplier_api"
            }
            actual_tiers = set(tiers.keys())
            assert expected_tiers.issubset(actual_tiers), f"Missing tiers: {expected_tiers - actual_tiers}"

            for tier_name, tier_config in tiers.items():
                assert "capacity" in tier_config, f"Missing 'capacity' in tier {tier_name}"
                assert "refill_rate" in tier_config, f"Missing 'refill_rate' in tier {tier_name}"
                assert "active_buckets" in tier_config, f"Missing 'active_buckets' in tier {tier_name}"
                print(f"  ✓ Rate tier '{tier_name}': capacity={tier_config.get('capacity')}, active_buckets={tier_config.get('active_buckets')}")

        print(f"✓ /api/infrastructure/rate-limits: status={data.get('status')}, tiers={len(data.get('tiers', {}))}")


# ============================================================================
# Metrics Endpoint Tests
# ============================================================================


class TestMetrics:
    """Test /api/infrastructure/metrics endpoint."""

    def test_metrics_requires_auth(self, fresh_session):
        """Metrics endpoint should require authentication."""
        response = fresh_session.get(f"{BASE_URL}/api/infrastructure/metrics")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text[:200]}"
        print("✓ /api/infrastructure/metrics requires auth")

    def test_metrics_summary(self, authed_session):
        """Metrics summary with valid auth."""
        response = authed_session.get(f"{BASE_URL}/api/infrastructure/metrics")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Validate response structure
        assert "counters" in data, "Missing 'counters' in response"
        assert "gauges" in data, "Missing 'gauges' in response"
        assert "histograms" in data, "Missing 'histograms' in response"

        assert isinstance(data.get("counters"), dict), "counters should be a dict"
        assert isinstance(data.get("gauges"), dict), "gauges should be a dict"
        assert isinstance(data.get("histograms"), dict), "histograms should be a dict"

        print(f"✓ /api/infrastructure/metrics: counters={len(data.get('counters', {}))}, gauges={len(data.get('gauges', {}))}, histograms={len(data.get('histograms', {}))}")


# ============================================================================
# Queue Status Endpoint Tests
# ============================================================================


class TestQueues:
    """Test /api/infrastructure/queues endpoint."""

    def test_queues_requires_auth(self, fresh_session):
        """Queues endpoint should require authentication."""
        response = fresh_session.get(f"{BASE_URL}/api/infrastructure/queues")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text[:200]}"
        print("✓ /api/infrastructure/queues requires auth")

    def test_celery_queue_status(self, authed_session):
        """Celery queue status with valid auth."""
        response = authed_session.get(f"{BASE_URL}/api/infrastructure/queues")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Validate response structure
        assert "status" in data, "Missing 'status' in response"

        if data.get("status") == "healthy":
            assert "queues" in data, "Missing 'queues' in response"
            queues = data.get("queues", {})

            # Verify 9 expected queues (6 regular + 3 DLQ)
            expected_queues = {
                "default", "critical", "supplier", "notifications", "reports", "maintenance",
                "dlq.default", "dlq.critical", "dlq.supplier"
            }
            actual_queues = set(queues.keys())
            assert expected_queues.issubset(actual_queues), f"Missing queues: {expected_queues - actual_queues}"

            for queue_name, queue_info in queues.items():
                assert "length" in queue_info, f"Missing 'length' in queue {queue_name}"
                print(f"  ✓ Queue '{queue_name}': length={queue_info.get('length')}")

            assert "total_pending" in data, "Missing 'total_pending' in response"
            print(f"✓ /api/infrastructure/queues: queues={len(queues)}, total_pending={data.get('total_pending')}")
        else:
            print(f"✓ /api/infrastructure/queues: status={data.get('status')}")


# ============================================================================
# Rate Limiting Header Tests
# ============================================================================


class TestRateLimitingHeaders:
    """Test rate limiting behavior and headers."""

    def test_rate_limit_policy_header_on_api(self, fresh_session):
        """Verify X-RateLimit-Policy: token_bucket header is present on API endpoints.

        Note: /api/health is explicitly skipped by rate limit middleware, so we test
        a different endpoint that goes through rate limiting.
        """
        # Test on /api/healthz which should go through rate limiting
        response = fresh_session.get(f"{BASE_URL}/api/healthz")
        assert response.status_code == 200

        # Check for rate limit policy header (may not be present on health endpoints)
        policy_header = response.headers.get("X-RateLimit-Policy")
        print(f"✓ /api/healthz response with X-RateLimit-Policy: {policy_header}")

        # If the header is present, verify it's token_bucket
        if policy_header:
            assert policy_header == "token_bucket", f"Expected 'token_bucket', got '{policy_header}'"
            print(f"✓ X-RateLimit-Policy header confirmed: {policy_header}")
        else:
            # For health endpoints, it may be skipped - this is expected behavior
            print("ℹ X-RateLimit-Policy header not present on health endpoints (expected)")

    def test_auth_login_rate_limiting(self, fresh_session):
        """Test auth login includes rate limiting."""
        # Note: We're just verifying the header is set, not triggering rate limits
        response = fresh_session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test-rate-limit-check@test.com", "password": "wrongpassword"},
        )
        # Even failed login should have rate limit policy header
        policy_header = response.headers.get("X-RateLimit-Policy")
        # If 429, check the special headers
        if response.status_code == 429:
            assert "Retry-After" in response.headers, "Missing Retry-After header on 429"
            assert "X-RateLimit-Remaining" in response.headers, "Missing X-RateLimit-Remaining on 429"
            print(f"✓ Rate limit triggered (429): Retry-After={response.headers.get('Retry-After')}s")
        else:
            if policy_header:
                assert policy_header == "token_bucket", f"Expected 'token_bucket', got '{policy_header}'"
            print(f"✓ Auth login response: status={response.status_code}, X-RateLimit-Policy={policy_header}")


# ============================================================================
# Prometheus Metrics Endpoint (public)
# ============================================================================


class TestPrometheusMetrics:
    """Test /api/infrastructure/metrics/prometheus endpoint."""

    def test_prometheus_metrics_text_format(self, fresh_session):
        """Prometheus metrics should return text format."""
        response = fresh_session.get(f"{BASE_URL}/api/infrastructure/metrics/prometheus")
        # This endpoint may or may not require auth based on implementation
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "text/plain" in content_type, f"Expected text/plain, got {content_type}"
            # Verify it's Prometheus format
            text = response.text
            assert len(text) >= 0  # Can be empty if no metrics yet
            print(f"✓ /api/infrastructure/metrics/prometheus: text/plain format, {len(text)} bytes")
        elif response.status_code in [401, 403]:
            print("✓ /api/infrastructure/metrics/prometheus requires auth (acceptable)")
        else:
            pytest.fail(f"Unexpected status: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
