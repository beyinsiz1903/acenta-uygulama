"""
Platform Hardening Layer Tests (Iteration 71) - All 16 endpoints

Tests all backend hardening endpoints for the 10-part hardening implementation.
Uses session-scoped auth to avoid rate limiting.
"""

import os
import pytest
import requests
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://unified-booking-flow.preview.emergentagent.com"


@pytest.fixture(scope="module")
def auth_session():
    """Module-scoped authenticated session to avoid rate limiting."""
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
    
    return session


# ============================================================================
# Combined Hardening Status
# ============================================================================

def test_hardening_status(auth_session):
    """GET /api/hardening/status - combined hardening status with maturity score."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/status")
    assert response.status_code == 200
    
    data = response.json()
    assert data["platform_hardening_phase"] == "active"
    assert "maturity_score" in data
    assert "maturity_label" in data
    assert "go_live_ready" in data
    assert "components" in data
    assert len(data["parts"]) == 10
    
    print(f"✓ Hardening status: maturity={data['maturity_score']}/10, go_live_ready={data['go_live_ready']}")


# ============================================================================
# Part 1: Traffic Testing
# ============================================================================

def test_traffic_status(auth_session):
    """GET /api/hardening/traffic/status - supplier traffic testing status."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/traffic/status")
    assert response.status_code == 200
    
    data = response.json()
    assert "traffic_gate" in data
    assert "sandbox_environments" in data
    
    # Check all 3 suppliers
    for supplier in ["paximum", "aviationstack", "amadeus"]:
        assert supplier in data["sandbox_environments"]
    
    print(f"✓ Traffic status: suppliers={list(data['sandbox_environments'].keys())}")


def test_set_traffic_mode(auth_session):
    """POST /api/hardening/traffic/mode - set traffic mode for supplier."""
    payload = {"supplier": "paximum", "mode": "sandbox", "ratio": 0.0}
    response = auth_session.post(f"{BASE_URL}/api/hardening/traffic/mode", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "updated"
    assert data["supplier"] == "paximum"
    
    print(f"✓ Traffic mode set: {data['supplier']}={data['mode']}")


def test_sandbox_test(auth_session):
    """POST /api/hardening/traffic/sandbox-test - run sandbox test (SIMULATED)."""
    response = auth_session.post(f"{BASE_URL}/api/hardening/traffic/sandbox-test?supplier=paximum")
    assert response.status_code == 200
    
    data = response.json()
    assert data["supplier"] == "paximum"
    assert data["tests_run"] > 0
    assert all(r["status"] == "simulated_pass" for r in data["results"])
    
    print(f"✓ Sandbox test: {data['tests_run']} tests run (SIMULATED)")


# ============================================================================
# Part 2: Worker Strategy
# ============================================================================

def test_workers_status(auth_session):
    """GET /api/hardening/workers/status - worker pools, queue depths, DLQ."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/workers/status")
    assert response.status_code == 200
    
    data = response.json()
    assert "redis_status" in data
    assert "worker_pools" in data
    assert "dlq_config" in data
    
    # Check expected pools
    for pool in ["critical", "supplier", "notifications", "reports", "maintenance"]:
        assert pool in data["worker_pools"]
    
    print(f"✓ Workers: redis={data['redis_status']}, pools={len(data['worker_pools'])}")


# ============================================================================
# Part 3: Observability Stack
# ============================================================================

def test_observability_status(auth_session):
    """GET /api/hardening/observability/status - Prometheus, OpenTelemetry, Grafana."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/observability/status")
    assert response.status_code == 200
    
    data = response.json()
    assert "prometheus" in data
    assert "opentelemetry" in data
    assert "grafana_dashboards" in data
    assert "alert_rules" in data
    
    assert data["prometheus"]["metrics_defined"] > 0
    assert data["opentelemetry"]["service_name"] == "syroce-api"
    
    print(f"✓ Observability: metrics={data['prometheus']['metrics_defined']}, dashboards={len(data['grafana_dashboards'])}")


def test_grafana_dashboards(auth_session):
    """GET /api/hardening/observability/dashboards - Grafana dashboard configs."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/observability/dashboards")
    assert response.status_code == 200
    
    data = response.json()
    assert "dashboards" in data
    assert "alert_rules" in data
    
    for dashboard in ["platform_overview", "supplier_health", "booking_conversion", "queue_monitoring"]:
        assert dashboard in data["dashboards"]
    
    print(f"✓ Dashboards: {len(data['dashboards'])} configured, {len(data['alert_rules'])} alerts")


# ============================================================================
# Part 4: Performance Testing
# ============================================================================

def test_performance_assessment(auth_session):
    """GET /api/hardening/performance/assessment - run performance assessment (SIMULATED)."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/performance/assessment")
    assert response.status_code == 200
    
    data = response.json()
    assert "current_metrics" in data
    assert "sla_compliance" in data
    assert "bottleneck_analysis" in data
    
    print(f"✓ Performance: {len(data['current_metrics'])} metrics assessed (SIMULATED)")


def test_performance_profiles(auth_session):
    """GET /api/hardening/performance/profiles - load test profiles and SLA targets."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/performance/profiles")
    assert response.status_code == 200
    
    data = response.json()
    assert "profiles" in data
    assert "scenarios" in data
    assert "sla_targets" in data
    
    for profile in ["standard", "peak", "stress"]:
        assert profile in data["profiles"]
    
    print(f"✓ Profiles: {len(data['profiles'])} profiles, {len(data['sla_targets'])} SLAs")


# ============================================================================
# Part 5: Tenant Safety
# ============================================================================

def test_tenant_isolation_audit(auth_session):
    """GET /api/hardening/tenant-safety/audit - tenant isolation audit."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/tenant-safety/audit")
    assert response.status_code == 200
    
    data = response.json()
    assert "total_collections" in data
    assert "passed" in data
    assert "failed" in data
    assert "collection_results" in data
    assert "score" in data
    
    print(f"✓ Tenant audit: score={data['score']}%, passed={data['passed']}, failed={data['failed']}")


# ============================================================================
# Part 6: Secret Management
# ============================================================================

def test_secrets_status(auth_session):
    """GET /api/hardening/secrets/status - secret management inventory."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/secrets/status")
    assert response.status_code == 200
    
    data = response.json()
    assert "inventory" in data
    assert "summary" in data
    assert "migration_phases" in data
    
    summary = data["summary"]
    assert summary["total_secrets"] > 0
    
    print(f"✓ Secrets: total={summary['total_secrets']}, configured={summary['configured']}")


# ============================================================================
# Part 7: Incident Playbooks
# ============================================================================

def test_incident_playbooks(auth_session):
    """GET /api/hardening/incidents/playbooks - incident response playbooks."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/incidents/playbooks")
    assert response.status_code == 200
    
    data = response.json()
    assert "playbooks" in data
    assert "total" in data
    
    for playbook in ["supplier_outage", "queue_backlog", "payment_failure"]:
        assert playbook in data["playbooks"]
    
    print(f"✓ Playbooks: {data['total']} defined")


def test_simulate_incident(auth_session):
    """POST /api/hardening/incidents/simulate - simulate incident response."""
    response = auth_session.post(f"{BASE_URL}/api/hardening/incidents/simulate?incident_type=supplier_outage")
    assert response.status_code == 200
    
    data = response.json()
    assert data["incident_type"] == "supplier_outage"
    assert data["total_steps"] > 0
    
    print(f"✓ Incident simulation: {data['total_steps']} steps")


# ============================================================================
# Part 8: Auto-Scaling
# ============================================================================

def test_scaling_status(auth_session):
    """GET /api/hardening/scaling/status - auto-scaling configs."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/scaling/status")
    assert response.status_code == 200
    
    data = response.json()
    assert "scaling_configs" in data
    assert "capacity_thresholds" in data
    assert "recommendations" in data
    
    for config in ["api_servers", "worker_nodes", "redis_cluster", "mongodb_replicas"]:
        assert config in data["scaling_configs"]
    
    print(f"✓ Scaling: {len(data['scaling_configs'])} configs, {len(data['recommendations'])} recommendations")


# ============================================================================
# Part 9: Disaster Recovery
# ============================================================================

def test_dr_plan(auth_session):
    """GET /api/hardening/dr/plan - disaster recovery plan."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/dr/plan")
    assert response.status_code == 200
    
    data = response.json()
    assert "rto_rpo_targets" in data
    assert "scenarios" in data
    assert "drill_schedule" in data
    assert "backup_strategy" in data
    
    for scenario in ["region_outage", "database_corruption", "queue_loss"]:
        assert scenario in data["scenarios"]
    
    print(f"✓ DR Plan: {len(data['scenarios'])} scenarios, {len(data['drill_schedule'])} drills")


# ============================================================================
# Part 10: Hardening Checklist
# ============================================================================

def test_hardening_checklist(auth_session):
    """GET /api/hardening/checklist - top 50 hardening tasks with maturity score."""
    response = auth_session.get(f"{BASE_URL}/api/hardening/checklist")
    assert response.status_code == 200
    
    data = response.json()
    assert "tasks" in data
    assert "maturity" in data
    assert len(data["tasks"]) == 50
    
    maturity = data["maturity"]
    assert "maturity_score" in maturity
    assert "go_live_ready" in maturity
    
    print(f"✓ Checklist: {len(data['tasks'])} tasks, maturity={maturity['maturity_score']}/10")


# ============================================================================
# Auth Tests (no login needed)
# ============================================================================

def test_hardening_status_requires_auth():
    """Verify /api/hardening/status requires authentication."""
    response = requests.get(f"{BASE_URL}/api/hardening/status")
    assert response.status_code == 401
    print("✓ Auth required for /api/hardening/status")


def test_checklist_requires_auth():
    """Verify /api/hardening/checklist requires authentication."""
    response = requests.get(f"{BASE_URL}/api/hardening/checklist")
    assert response.status_code == 401
    print("✓ Auth required for /api/hardening/checklist")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
