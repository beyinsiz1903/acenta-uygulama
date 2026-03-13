"""
Test Production Activation Endpoints (Iteration 73)
Tests the 10-part production activation engine with REAL infrastructure checks.

Endpoints tested:
- GET /api/hardening/activation/infrastructure - Real Redis/Celery/MongoDB health
- GET /api/hardening/activation/secrets - Secret audit
- GET /api/hardening/activation/suppliers - Supplier adapter status
- GET /api/hardening/activation/performance - Performance baseline (latency tests)
- POST /api/hardening/activation/incident/{type} - Incident simulation
- GET /api/hardening/activation/tenant-isolation - Tenant isolation tests
- GET /api/hardening/activation/dry-run - Go-live dry run pipeline
- GET /api/hardening/activation/onboarding - Onboarding readiness
- GET /api/hardening/activation/certification - Full go-live certification
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_CREDS = {"email": "agent@acenta.test", "password": "agent123"}


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for super_admin user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=SUPER_ADMIN_CREDS
    )
    if response.status_code == 200:
        data = response.json()
        # Auth uses 'access_token' field
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with Bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}


class TestInfrastructureHealth:
    """Tests for /api/hardening/activation/infrastructure endpoint."""

    def test_infrastructure_requires_auth(self):
        """Infrastructure endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/hardening/activation/infrastructure")
        assert response.status_code == 401

    def test_infrastructure_returns_real_data(self, auth_headers):
        """Infrastructure endpoint returns real health data."""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/infrastructure",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "timestamp" in data
        assert "overall_status" in data
        assert "healthy_services" in data
        assert "total_services" in data
        assert "services" in data

        # Verify services structure
        services = data["services"]
        assert "redis" in services
        assert "celery" in services
        assert "mongodb" in services

        # Verify Redis details
        redis = services["redis"]
        assert redis["service"] == "redis"
        assert "status" in redis
        assert "latency_ms" in redis

        # Verify MongoDB details
        mongo = services["mongodb"]
        assert mongo["service"] == "mongodb"
        assert "status" in mongo

        # Verify Celery details
        celery = services["celery"]
        assert celery["service"] == "celery"
        assert "status" in celery

    def test_infrastructure_redis_healthy(self, auth_headers):
        """Redis should be healthy with queue depth info."""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/infrastructure",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        redis = data["services"]["redis"]
        assert redis["status"] == "healthy"
        assert redis["latency_ms"] is not None
        assert redis["latency_ms"] > 0

        # Check queue depths exist
        if redis["details"]:
            assert "queue_depths" in redis["details"]

    def test_infrastructure_mongodb_healthy(self, auth_headers):
        """MongoDB should be healthy with collection info."""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/infrastructure",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        mongo = data["services"]["mongodb"]
        assert mongo["status"] == "healthy"
        assert mongo["latency_ms"] is not None

        if mongo["details"]:
            assert "collections" in mongo["details"]


class TestSecretAudit:
    """Tests for /api/hardening/activation/secrets endpoint."""

    def test_secrets_requires_auth(self):
        """Secrets endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/hardening/activation/secrets")
        assert response.status_code == 401

    def test_secrets_returns_audit(self, auth_headers):
        """Secrets endpoint returns secret audit."""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/secrets",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "timestamp" in data
        assert "secrets" in data
        assert "summary" in data

        # Verify each secret has required fields
        for secret in data["secrets"]:
            assert "name" in secret
            assert "category" in secret
            assert "status" in secret
            assert "is_present" in secret
            assert "risk" in secret

        # Verify summary
        summary = data["summary"]
        assert "total" in summary
        assert "configured" in summary
        assert "missing" in summary
        assert "production_ready_pct" in summary


class TestSupplierStatus:
    """Tests for /api/hardening/activation/suppliers endpoint."""

    def test_suppliers_requires_auth(self):
        """Suppliers endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/hardening/activation/suppliers")
        assert response.status_code == 401

    def test_suppliers_returns_status(self, auth_headers):
        """Suppliers endpoint returns adapter status."""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/suppliers",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "timestamp" in data
        assert "suppliers" in data
        assert "summary" in data

        # Verify suppliers exist
        assert len(data["suppliers"]) > 0

        for supplier in data["suppliers"]:
            assert "name" in supplier
            assert "type" in supplier
            assert "status" in supplier

        # Verify summary
        summary = data["summary"]
        assert "total" in summary
        assert "active" in summary


class TestPerformanceBaseline:
    """Tests for /api/hardening/activation/performance endpoint."""

    def test_performance_requires_auth(self):
        """Performance endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/hardening/activation/performance")
        assert response.status_code == 401

    def test_performance_returns_baseline(self, auth_headers):
        """Performance endpoint returns real latency measurements."""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/performance",
            headers=auth_headers,
            timeout=30  # Longer timeout for performance tests
        )
        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "timestamp" in data
        assert "results" in data
        assert "sla_summary" in data

        # Verify SLA summary
        sla = data["sla_summary"]
        assert "total_tests" in sla
        assert "passing" in sla
        assert "pass_rate_pct" in sla

        # Verify results have latency measurements
        results = data["results"]
        assert len(results) > 0

    def test_performance_mongodb_latency(self, auth_headers):
        """Performance should measure MongoDB latency."""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/performance",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()

        # Check MongoDB read latency exists
        results = data["results"]
        if "mongodb_read_latency" in results:
            mongo_latency = results["mongodb_read_latency"]
            if "error" not in mongo_latency:
                assert "avg_ms" in mongo_latency
                assert "sla_target_ms" in mongo_latency
                assert "passes_sla" in mongo_latency


class TestIncidentSimulation:
    """Tests for /api/hardening/activation/incident/{type} endpoints."""

    def test_incident_requires_auth(self):
        """Incident endpoints require authentication."""
        response = requests.post(f"{BASE_URL}/api/hardening/activation/incident/supplier_outage")
        assert response.status_code == 401

    def test_supplier_outage_simulation(self, auth_headers):
        """Supplier outage incident simulation returns playbook."""
        response = requests.post(
            f"{BASE_URL}/api/hardening/activation/incident/supplier_outage",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert data["incident_type"] == "supplier_outage"
        assert "timestamp" in data
        assert "simulation" in data
        assert "playbook_executed" in data
        assert "verdict" in data

        # Verify simulation details
        sim = data["simulation"]
        assert "circuit_breaker_triggered" in sim
        assert "fallback_activated" in sim

    def test_queue_backlog_simulation(self, auth_headers):
        """Queue backlog incident simulation measures queue depths."""
        response = requests.post(
            f"{BASE_URL}/api/hardening/activation/incident/queue_backlog",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["incident_type"] == "queue_backlog"
        assert "simulation" in data
        assert "playbook_executed" in data

        # Verify queue depth info
        sim = data["simulation"]
        assert "current_depths" in sim or "error" in sim

    def test_payment_failure_simulation(self, auth_headers):
        """Payment failure incident simulation returns playbook."""
        response = requests.post(
            f"{BASE_URL}/api/hardening/activation/incident/payment_failure",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["incident_type"] == "payment_failure"
        assert "simulation" in data
        assert "playbook_executed" in data

        sim = data["simulation"]
        assert "retry_mechanism" in sim
        assert "idempotency_key" in sim


class TestTenantIsolation:
    """Tests for /api/hardening/activation/tenant-isolation endpoint."""

    def test_tenant_isolation_requires_auth(self):
        """Tenant isolation endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/hardening/activation/tenant-isolation")
        assert response.status_code == 401

    def test_tenant_isolation_returns_results(self, auth_headers):
        """Tenant isolation endpoint returns collection audit."""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/tenant-isolation",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "timestamp" in data
        assert "results" in data
        assert "summary" in data

        # Verify summary
        summary = data["summary"]
        assert "collections_checked" in summary
        assert "isolated" in summary
        assert "isolation_score_pct" in summary


class TestDryRun:
    """Tests for /api/hardening/activation/dry-run endpoint."""

    def test_dry_run_requires_auth(self):
        """Dry run endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/hardening/activation/dry-run")
        assert response.status_code == 401

    def test_dry_run_returns_pipeline_steps(self, auth_headers):
        """Dry run endpoint returns 5 pipeline step results."""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/dry-run",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "timestamp" in data
        assert "dry_run_result" in data
        assert "steps" in data
        assert "summary" in data

        # Verify 5 steps
        steps = data["steps"]
        assert len(steps) == 5

        # Verify each step has required fields
        for step in steps:
            assert "step" in step
            assert "name" in step
            assert "status" in step

        # Verify step names match expected pipeline
        step_names = [s["name"] for s in steps]
        assert "Hotel Search" in step_names
        assert "Pricing Calculation" in step_names
        assert "Booking Creation" in step_names
        assert "Voucher Generation" in step_names
        assert "Notification Delivery" in step_names


class TestOnboardingReadiness:
    """Tests for /api/hardening/activation/onboarding endpoint."""

    def test_onboarding_requires_auth(self):
        """Onboarding endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/hardening/activation/onboarding")
        assert response.status_code == 401

    def test_onboarding_returns_checks(self, auth_headers):
        """Onboarding endpoint returns readiness checks."""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/onboarding",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "timestamp" in data
        assert "checks" in data
        assert "summary" in data

        # Verify checks
        checks = data["checks"]
        assert len(checks) > 0

        for check in checks:
            assert "check" in check
            assert "status" in check

        # Verify summary
        summary = data["summary"]
        assert "total_checks" in summary
        assert "ready" in summary
        assert "onboarding_ready_pct" in summary


class TestGoLiveCertification:
    """Tests for /api/hardening/activation/certification endpoint."""

    def test_certification_requires_auth(self):
        """Certification endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/hardening/activation/certification")
        assert response.status_code == 401

    def test_certification_returns_full_report(self, auth_headers):
        """Certification endpoint returns comprehensive go-live report."""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/certification",
            headers=auth_headers,
            timeout=60  # Certification runs all checks
        )
        assert response.status_code == 200
        data = response.json()

        # Verify top-level structure
        assert "timestamp" in data
        assert "certification" in data
        assert "dimension_scores" in data
        assert "infrastructure" in data
        assert "security" in data
        assert "reliability" in data
        assert "risks" in data

        # Verify certification details
        cert = data["certification"]
        assert "production_readiness_score" in cert
        assert "target" in cert
        assert "gap" in cert
        assert "certified" in cert
        assert "decision" in cert

        # Verify dimension scores exist
        scores = data["dimension_scores"]
        assert "infrastructure" in scores
        assert "security" in scores
        assert "reliability" in scores
        assert "observability" in scores
        assert "operations" in scores

    def test_certification_decision_logic(self, auth_headers):
        """Certification decision is based on score >= 8.5."""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/certification",
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()

        cert = data["certification"]
        score = cert["production_readiness_score"]
        cert["certified"]
        decision = cert["decision"]

        # Verify decision logic
        if score >= 8.5:
            assert decision == "GO"
        else:
            assert decision == "NO-GO"


class TestEndpointAuthentication:
    """Verify all activation endpoints require proper authentication."""

    @pytest.mark.parametrize("endpoint,method", [
        ("/api/hardening/activation/infrastructure", "GET"),
        ("/api/hardening/activation/secrets", "GET"),
        ("/api/hardening/activation/suppliers", "GET"),
        ("/api/hardening/activation/performance", "GET"),
        ("/api/hardening/activation/tenant-isolation", "GET"),
        ("/api/hardening/activation/dry-run", "GET"),
        ("/api/hardening/activation/onboarding", "GET"),
        ("/api/hardening/activation/certification", "GET"),
        ("/api/hardening/activation/incident/supplier_outage", "POST"),
        ("/api/hardening/activation/incident/queue_backlog", "POST"),
        ("/api/hardening/activation/incident/payment_failure", "POST"),
    ])
    def test_endpoint_requires_auth(self, endpoint, method):
        """All activation endpoints should return 401 without auth."""
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}")
        else:
            response = requests.post(f"{BASE_URL}{endpoint}")
        assert response.status_code == 401, f"{endpoint} should require auth"
