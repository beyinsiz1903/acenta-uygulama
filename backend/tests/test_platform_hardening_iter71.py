"""
Platform Hardening Layer Tests (Iteration 71)

Tests all 16 backend hardening endpoints + combined status endpoint.
10-part hardening implementation:
1) Supplier Traffic Testing
2) Worker Deployment Strategy
3) Observability Stack
4) Performance Testing
5) Multi-Tenant Safety
6) Secret Management Migration
7) Incident Response Playbooks
8) Auto-Scaling Strategy
9) Disaster Recovery
10) Hardening Checklist
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://cache-bug-fixed.preview.emergentagent.com"


class TestPlatformHardeningAuth:
    """Test authentication for hardening endpoints."""

    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session with super_admin credentials."""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})

        # Login with super_admin credentials
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"

        # Extract token and set authorization header
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})

        # Also store cookies for cookie-based auth
        return session

    def test_login_super_admin(self, auth_session):
        """Verify super_admin login works."""
        response = auth_session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data.get("email") == "agent@acenta.test"
        print(f"✓ Login successful for: {data.get('email')}, role: {data.get('role')}")


class TestHardeningCombinedStatus:
    """Test combined hardening status endpoint."""

    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session."""
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert login_response.status_code == 200
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session

    def test_hardening_status(self, auth_session):
        """GET /api/hardening/status - combined hardening status with maturity score."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/status")
        assert response.status_code == 200

        data = response.json()
        # Validate structure
        assert "platform_hardening_phase" in data
        assert data["platform_hardening_phase"] == "active"
        assert "maturity_score" in data
        assert "maturity_label" in data
        assert "go_live_ready" in data
        assert "components" in data
        assert "parts" in data

        # Validate components
        components = data["components"]
        assert "traffic_testing" in components
        assert "checklist_completion" in components
        assert "secrets_configured" in components
        assert "secrets_total" in components
        assert "critical_blockers" in components

        # Validate parts - should have 10 parts
        parts = data["parts"]
        assert len(parts) == 10
        for part in parts:
            assert "part" in part
            assert "name" in part
            assert "status" in part

        print(f"✓ Hardening status: maturity={data['maturity_score']}/10, label={data['maturity_label']}, go_live_ready={data['go_live_ready']}")


class TestTrafficTesting:
    """Part 1: Supplier Traffic Testing endpoints."""

    @pytest.fixture(scope="class")
    def auth_session(self):
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert login_response.status_code == 200
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session

    def test_traffic_status(self, auth_session):
        """GET /api/hardening/traffic/status - supplier traffic testing status."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/traffic/status")
        assert response.status_code == 200

        data = response.json()
        assert "traffic_gate" in data
        assert "sandbox_environments" in data

        # Validate traffic gate modes
        traffic_gate = data["traffic_gate"]
        assert "modes" in traffic_gate

        # Validate sandbox environments (paximum, aviationstack, amadeus)
        sandbox_envs = data["sandbox_environments"]
        expected_suppliers = ["paximum", "aviationstack", "amadeus"]
        for supplier in expected_suppliers:
            assert supplier in sandbox_envs, f"Missing supplier: {supplier}"
            assert "url" in sandbox_envs[supplier]
            assert "scenarios" in sandbox_envs[supplier]

        print(f"✓ Traffic status: {len(traffic_gate['modes'])} suppliers configured, environments: {list(sandbox_envs.keys())}")

    def test_set_traffic_mode(self, auth_session):
        """POST /api/hardening/traffic/mode - set traffic mode for supplier."""
        payload = {
            "supplier": "paximum",
            "mode": "sandbox",
            "ratio": 0.0
        }
        response = auth_session.post(
            f"{BASE_URL}/api/hardening/traffic/mode",
            json=payload
        )
        assert response.status_code == 200

        data = response.json()
        assert data.get("status") == "updated"
        assert data.get("supplier") == "paximum"
        assert data.get("mode") == "sandbox"

        print(f"✓ Traffic mode set: supplier={data['supplier']}, mode={data['mode']}")

    def test_sandbox_test_paximum(self, auth_session):
        """POST /api/hardening/traffic/sandbox-test?supplier=paximum - run sandbox test."""
        response = auth_session.post(f"{BASE_URL}/api/hardening/traffic/sandbox-test?supplier=paximum")
        assert response.status_code == 200

        data = response.json()
        assert data.get("supplier") == "paximum"
        assert "tests_run" in data
        assert "results" in data
        assert data["tests_run"] > 0

        # Validate results structure
        for result in data["results"]:
            assert "scenario" in result
            assert "type" in result
            assert "status" in result
            assert result["status"] == "simulated_pass"

        print(f"✓ Sandbox test: supplier={data['supplier']}, tests_run={data['tests_run']}")


class TestWorkerStrategy:
    """Part 2: Worker Deployment Strategy endpoints."""

    @pytest.fixture(scope="class")
    def auth_session(self):
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert login_response.status_code == 200
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session

    def test_workers_status(self, auth_session):
        """GET /api/hardening/workers/status - worker pools, queue depths, DLQ."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/workers/status")
        assert response.status_code == 200

        data = response.json()
        assert "redis_status" in data
        assert "worker_pools" in data
        assert "dlq_config" in data
        assert "autoscale_rules" in data
        assert "status" in data

        # Validate worker pools
        worker_pools = data["worker_pools"]
        expected_pools = ["critical", "supplier", "notifications", "reports", "maintenance"]
        for pool in expected_pools:
            assert pool in worker_pools, f"Missing pool: {pool}"
            assert "queues" in worker_pools[pool]
            assert "concurrency" in worker_pools[pool]
            assert "autoscale" in worker_pools[pool]

        print(f"✓ Workers status: redis={data['redis_status']}, pools={len(worker_pools)}, status={data['status']}")


class TestObservabilityStack:
    """Part 3: Observability Stack endpoints."""

    @pytest.fixture(scope="class")
    def auth_session(self):
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert login_response.status_code == 200
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session

    def test_observability_status(self, auth_session):
        """GET /api/hardening/observability/status - Prometheus metrics, OpenTelemetry, Grafana."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/observability/status")
        assert response.status_code == 200

        data = response.json()
        assert "prometheus" in data
        assert "opentelemetry" in data
        assert "grafana_dashboards" in data
        assert "alert_rules" in data

        # Validate Prometheus
        prometheus = data["prometheus"]
        assert "metrics_defined" in prometheus
        assert prometheus["metrics_defined"] > 0

        # Validate OpenTelemetry
        otel = data["opentelemetry"]
        assert "service_name" in otel
        assert otel["service_name"] == "syroce-api"

        print(f"✓ Observability: prometheus_metrics={prometheus['metrics_defined']}, dashboards={len(data['grafana_dashboards'])}, alerts={len(data['alert_rules'])}")

    def test_grafana_dashboards(self, auth_session):
        """GET /api/hardening/observability/dashboards - Grafana dashboard configs."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/observability/dashboards")
        assert response.status_code == 200

        data = response.json()
        assert "dashboards" in data
        assert "alert_rules" in data

        dashboards = data["dashboards"]
        expected_dashboards = ["platform_overview", "supplier_health", "booking_conversion", "queue_monitoring"]
        for dashboard in expected_dashboards:
            assert dashboard in dashboards, f"Missing dashboard: {dashboard}"
            assert "title" in dashboards[dashboard]
            assert "panels" in dashboards[dashboard]

        print(f"✓ Grafana dashboards: {len(dashboards)} defined, alerts: {len(data['alert_rules'])}")


class TestPerformanceTesting:
    """Part 4: Performance Testing endpoints."""

    @pytest.fixture(scope="class")
    def auth_session(self):
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert login_response.status_code == 200
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session

    def test_performance_assessment(self, auth_session):
        """GET /api/hardening/performance/assessment - run performance assessment."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/performance/assessment")
        assert response.status_code == 200

        data = response.json()
        assert "timestamp" in data
        assert "current_metrics" in data
        assert "sla_compliance" in data
        assert "bottleneck_analysis" in data
        assert "load_profiles" in data

        # Validate metrics
        metrics = data["current_metrics"]
        expected_metrics = ["api_latency_p95_ms", "db_query_p95_ms", "error_rate_percent"]
        for metric in expected_metrics:
            assert metric in metrics, f"Missing metric: {metric}"

        print(f"✓ Performance assessment: {len(data['current_metrics'])} metrics, {len(data['load_profiles'])} profiles")

    def test_performance_profiles(self, auth_session):
        """GET /api/hardening/performance/profiles - load test profiles and SLA targets."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/performance/profiles")
        assert response.status_code == 200

        data = response.json()
        assert "profiles" in data
        assert "scenarios" in data
        assert "sla_targets" in data

        # Validate profiles
        profiles = data["profiles"]
        expected_profiles = ["standard", "peak", "stress"]
        for profile in expected_profiles:
            assert profile in profiles, f"Missing profile: {profile}"
            assert "agencies" in profiles[profile]
            assert "searches_per_hour" in profiles[profile]
            assert "bookings_per_hour" in profiles[profile]

        print(f"✓ Performance profiles: {len(profiles)} profiles, {len(data['scenarios'])} scenarios, {len(data['sla_targets'])} SLA targets")


class TestTenantSafety:
    """Part 5: Multi-Tenant Safety endpoints."""

    @pytest.fixture(scope="class")
    def auth_session(self):
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert login_response.status_code == 200
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session

    def test_tenant_isolation_audit(self, auth_session):
        """GET /api/hardening/tenant-safety/audit - tenant isolation audit."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/tenant-safety/audit")
        assert response.status_code == 200

        data = response.json()
        assert "timestamp" in data
        assert "total_collections" in data
        assert "passed" in data
        assert "failed" in data
        assert "collection_results" in data
        assert "isolation_scenarios" in data
        assert "score" in data

        # Validate collection results
        assert data["total_collections"] > 0

        print(f"✓ Tenant audit: score={data['score']}%, passed={data['passed']}, failed={data['failed']}, collections={data['total_collections']}")


class TestSecretManagement:
    """Part 6: Secret Management Migration endpoints."""

    @pytest.fixture(scope="class")
    def auth_session(self):
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert login_response.status_code == 200
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session

    def test_secrets_status(self, auth_session):
        """GET /api/hardening/secrets/status - secret management inventory."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/secrets/status")
        assert response.status_code == 200

        data = response.json()
        assert "inventory" in data
        assert "summary" in data
        assert "migration_phases" in data

        # Validate summary
        summary = data["summary"]
        assert "total_secrets" in summary
        assert "configured" in summary
        assert "missing" in summary
        assert summary["total_secrets"] > 0

        # Validate inventory has expected secrets
        inventory = data["inventory"]
        expected_secrets = ["JWT_SECRET", "MONGO_URL", "REDIS_URL"]
        secret_names = [s["name"] for s in inventory]
        for secret in expected_secrets:
            assert secret in secret_names, f"Missing secret: {secret}"

        print(f"✓ Secrets status: total={summary['total_secrets']}, configured={summary['configured']}, phases={len(data['migration_phases'])}")


class TestIncidentPlaybooks:
    """Part 7: Incident Response Playbooks endpoints."""

    @pytest.fixture(scope="class")
    def auth_session(self):
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert login_response.status_code == 200
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session

    def test_incident_playbooks(self, auth_session):
        """GET /api/hardening/incidents/playbooks - incident response playbooks."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/incidents/playbooks")
        assert response.status_code == 200

        data = response.json()
        assert "playbooks" in data
        assert "total" in data
        assert "severities" in data

        # Validate playbooks
        playbooks = data["playbooks"]
        expected_playbooks = ["supplier_outage", "queue_backlog", "payment_failure"]
        for playbook in expected_playbooks:
            assert playbook in playbooks, f"Missing playbook: {playbook}"
            assert "name" in playbooks[playbook]
            assert "severity" in playbooks[playbook]
            assert "detection" in playbooks[playbook]
            assert "triage" in playbooks[playbook]
            assert "escalation" in playbooks[playbook]
            assert "resolution" in playbooks[playbook]

        print(f"✓ Incident playbooks: {data['total']} playbooks defined")

    def test_simulate_incident(self, auth_session):
        """POST /api/hardening/incidents/simulate?incident_type=supplier_outage - simulate incident."""
        response = auth_session.post(f"{BASE_URL}/api/hardening/incidents/simulate?incident_type=supplier_outage")
        assert response.status_code == 200

        data = response.json()
        assert data.get("incident_type") == "supplier_outage"
        assert "playbook_name" in data
        assert "severity" in data
        assert "simulation_steps" in data
        assert "total_steps" in data
        assert data["total_steps"] > 0

        print(f"✓ Incident simulation: type={data['incident_type']}, steps={data['total_steps']}")


class TestAutoScaling:
    """Part 8: Auto-Scaling Strategy endpoints."""

    @pytest.fixture(scope="class")
    def auth_session(self):
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert login_response.status_code == 200
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session

    def test_scaling_status(self, auth_session):
        """GET /api/hardening/scaling/status - auto-scaling configs."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/scaling/status")
        assert response.status_code == 200

        data = response.json()
        assert "scaling_configs" in data
        assert "capacity_thresholds" in data
        assert "recommendations" in data

        # Validate scaling configs
        scaling_configs = data["scaling_configs"]
        expected_configs = ["api_servers", "worker_nodes", "redis_cluster", "mongodb_replicas"]
        for config in expected_configs:
            assert config in scaling_configs, f"Missing config: {config}"
            assert "min_replicas" in scaling_configs[config]
            assert "max_replicas" in scaling_configs[config]
            assert "scaling_metrics" in scaling_configs[config]

        print(f"✓ Scaling status: {len(scaling_configs)} configs, {len(data['recommendations'])} recommendations")


class TestDisasterRecovery:
    """Part 9: Disaster Recovery endpoints."""

    @pytest.fixture(scope="class")
    def auth_session(self):
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert login_response.status_code == 200
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session

    def test_dr_plan(self, auth_session):
        """GET /api/hardening/dr/plan - disaster recovery plan."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/dr/plan")
        assert response.status_code == 200

        data = response.json()
        assert "rto_rpo_targets" in data
        assert "scenarios" in data
        assert "drill_schedule" in data
        assert "backup_strategy" in data

        # Validate RTO/RPO targets
        rto_rpo = data["rto_rpo_targets"]
        expected_tiers = ["tier_1_critical", "tier_2_important", "tier_3_standard"]
        for tier in expected_tiers:
            assert tier in rto_rpo, f"Missing tier: {tier}"
            assert "rto_minutes" in rto_rpo[tier]
            assert "rpo_minutes" in rto_rpo[tier]

        # Validate scenarios
        scenarios = data["scenarios"]
        expected_scenarios = ["region_outage", "database_corruption", "queue_loss"]
        for scenario in expected_scenarios:
            assert scenario in scenarios, f"Missing scenario: {scenario}"
            assert "name" in scenarios[scenario]
            assert "severity" in scenarios[scenario]
            assert "response_plan" in scenarios[scenario]

        print(f"✓ DR plan: {len(rto_rpo)} tiers, {len(scenarios)} scenarios, {len(data['drill_schedule'])} drills")


class TestHardeningChecklist:
    """Part 10: Hardening Checklist endpoints."""

    @pytest.fixture(scope="class")
    def auth_session(self):
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"}
        )
        assert login_response.status_code == 200
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session

    def test_hardening_checklist(self, auth_session):
        """GET /api/hardening/checklist - top 50 hardening tasks with maturity score."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/checklist")
        assert response.status_code == 200

        data = response.json()
        assert "tasks" in data
        assert "maturity" in data
        assert "generated_at" in data

        # Validate tasks
        tasks = data["tasks"]
        assert len(tasks) == 50, f"Expected 50 tasks, got {len(tasks)}"

        # Validate each task structure
        for task in tasks:
            assert "id" in task
            assert "priority" in task
            assert "category" in task
            assert "task" in task
            assert "status" in task
            assert "risk" in task
            assert "effort_days" in task

        # Validate maturity
        maturity = data["maturity"]
        assert "maturity_score" in maturity
        assert "maturity_label" in maturity
        assert "summary" in maturity
        assert "priority_breakdown" in maturity
        assert "go_live_ready" in maturity

        print(f"✓ Checklist: {len(tasks)} tasks, maturity={maturity['maturity_score']}/10, go_live_ready={maturity['go_live_ready']}")


class TestUnauthorizedAccess:
    """Test that hardening endpoints require authentication."""

    def test_hardening_status_requires_auth(self):
        """Verify /api/hardening/status requires authentication."""
        response = requests.get(f"{BASE_URL}/api/hardening/status")
        assert response.status_code == 401
        print("✓ /api/hardening/status correctly requires authentication")

    def test_traffic_status_requires_auth(self):
        """Verify /api/hardening/traffic/status requires authentication."""
        response = requests.get(f"{BASE_URL}/api/hardening/traffic/status")
        assert response.status_code == 401
        print("✓ /api/hardening/traffic/status correctly requires authentication")

    def test_checklist_requires_auth(self):
        """Verify /api/hardening/checklist requires authentication."""
        response = requests.get(f"{BASE_URL}/api/hardening/checklist")
        assert response.status_code == 401
        print("✓ /api/hardening/checklist correctly requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
