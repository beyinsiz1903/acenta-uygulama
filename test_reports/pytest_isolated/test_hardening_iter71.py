"""
Platform Hardening Layer Tests (Iteration 71) - ISOLATED

Tests all 16 backend hardening endpoints for the 10-part hardening implementation.
Runs in isolation to avoid conftest.py conflicts.
"""

import os
import requests
import sys

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://travel-infra-1.preview.emergentagent.com"


def get_auth_session():
    """Get authenticated session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    login_response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"}
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    
    data = login_response.json()
    token = data.get("access_token") or data.get("token")
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    
    return session


def test_hardening_status(session):
    """GET /api/hardening/status"""
    r = session.get(f"{BASE_URL}/api/hardening/status")
    assert r.status_code == 200
    d = r.json()
    assert d["platform_hardening_phase"] == "active"
    assert len(d["parts"]) == 10
    return f"✓ status: maturity={d['maturity_score']}/10, go_live={d['go_live_ready']}"


def test_traffic_status(session):
    """GET /api/hardening/traffic/status"""
    r = session.get(f"{BASE_URL}/api/hardening/traffic/status")
    assert r.status_code == 200
    d = r.json()
    assert "traffic_gate" in d
    return f"✓ traffic_status: suppliers={list(d['sandbox_environments'].keys())}"


def test_set_traffic_mode(session):
    """POST /api/hardening/traffic/mode"""
    r = session.post(f"{BASE_URL}/api/hardening/traffic/mode", json={"supplier": "paximum", "mode": "sandbox", "ratio": 0.0})
    assert r.status_code == 200
    return f"✓ set_traffic_mode: {r.json()['supplier']}={r.json()['mode']}"


def test_sandbox_test(session):
    """POST /api/hardening/traffic/sandbox-test"""
    r = session.post(f"{BASE_URL}/api/hardening/traffic/sandbox-test?supplier=paximum")
    assert r.status_code == 200
    d = r.json()
    return f"✓ sandbox_test: {d['tests_run']} tests (SIMULATED)"


def test_workers_status(session):
    """GET /api/hardening/workers/status"""
    r = session.get(f"{BASE_URL}/api/hardening/workers/status")
    assert r.status_code == 200
    d = r.json()
    return f"✓ workers: redis={d['redis_status']}, pools={len(d['worker_pools'])}"


def test_observability_status(session):
    """GET /api/hardening/observability/status"""
    r = session.get(f"{BASE_URL}/api/hardening/observability/status")
    assert r.status_code == 200
    d = r.json()
    return f"✓ observability: metrics={d['prometheus']['metrics_defined']}"


def test_grafana_dashboards(session):
    """GET /api/hardening/observability/dashboards"""
    r = session.get(f"{BASE_URL}/api/hardening/observability/dashboards")
    assert r.status_code == 200
    d = r.json()
    return f"✓ dashboards: {len(d['dashboards'])} configs, {len(d['alert_rules'])} alerts"


def test_performance_assessment(session):
    """GET /api/hardening/performance/assessment"""
    r = session.get(f"{BASE_URL}/api/hardening/performance/assessment")
    assert r.status_code == 200
    d = r.json()
    return f"✓ performance: {len(d['current_metrics'])} metrics (SIMULATED)"


def test_performance_profiles(session):
    """GET /api/hardening/performance/profiles"""
    r = session.get(f"{BASE_URL}/api/hardening/performance/profiles")
    assert r.status_code == 200
    d = r.json()
    return f"✓ profiles: {len(d['profiles'])} profiles, {len(d['sla_targets'])} SLAs"


def test_tenant_audit(session):
    """GET /api/hardening/tenant-safety/audit"""
    r = session.get(f"{BASE_URL}/api/hardening/tenant-safety/audit")
    assert r.status_code == 200
    d = r.json()
    return f"✓ tenant_audit: score={d['score']}%, passed={d['passed']}"


def test_secrets_status(session):
    """GET /api/hardening/secrets/status"""
    r = session.get(f"{BASE_URL}/api/hardening/secrets/status")
    assert r.status_code == 200
    d = r.json()
    return f"✓ secrets: total={d['summary']['total_secrets']}, configured={d['summary']['configured']}"


def test_incident_playbooks(session):
    """GET /api/hardening/incidents/playbooks"""
    r = session.get(f"{BASE_URL}/api/hardening/incidents/playbooks")
    assert r.status_code == 200
    d = r.json()
    return f"✓ playbooks: {d['total']} defined"


def test_simulate_incident(session):
    """POST /api/hardening/incidents/simulate"""
    r = session.post(f"{BASE_URL}/api/hardening/incidents/simulate?incident_type=supplier_outage")
    assert r.status_code == 200
    d = r.json()
    return f"✓ simulation: {d['total_steps']} steps for {d['incident_type']}"


def test_scaling_status(session):
    """GET /api/hardening/scaling/status"""
    r = session.get(f"{BASE_URL}/api/hardening/scaling/status")
    assert r.status_code == 200
    d = r.json()
    return f"✓ scaling: {len(d['scaling_configs'])} configs"


def test_dr_plan(session):
    """GET /api/hardening/dr/plan"""
    r = session.get(f"{BASE_URL}/api/hardening/dr/plan")
    assert r.status_code == 200
    d = r.json()
    return f"✓ dr_plan: {len(d['scenarios'])} scenarios"


def test_hardening_checklist(session):
    """GET /api/hardening/checklist"""
    r = session.get(f"{BASE_URL}/api/hardening/checklist")
    assert r.status_code == 200
    d = r.json()
    return f"✓ checklist: {len(d['tasks'])} tasks, maturity={d['maturity']['maturity_score']}/10"


def test_auth_required():
    """Test that endpoints require authentication."""
    r1 = requests.get(f"{BASE_URL}/api/hardening/status")
    r2 = requests.get(f"{BASE_URL}/api/hardening/checklist")
    assert r1.status_code == 401, f"Expected 401, got {r1.status_code}"
    assert r2.status_code == 401, f"Expected 401, got {r2.status_code}"
    return "✓ auth_required: endpoints correctly require auth"


def main():
    print("=" * 60)
    print("Platform Hardening API Tests - Iteration 71")
    print("=" * 60)
    
    tests = [
        ("Auth Required", test_auth_required, False),
    ]
    
    # Get session first
    session = get_auth_session()
    print("✓ Login successful")
    
    # Add authenticated tests
    auth_tests = [
        ("Combined Status", test_hardening_status),
        ("Traffic Status", test_traffic_status),
        ("Set Traffic Mode", test_set_traffic_mode),
        ("Sandbox Test", test_sandbox_test),
        ("Workers Status", test_workers_status),
        ("Observability Status", test_observability_status),
        ("Grafana Dashboards", test_grafana_dashboards),
        ("Performance Assessment", test_performance_assessment),
        ("Performance Profiles", test_performance_profiles),
        ("Tenant Audit", test_tenant_audit),
        ("Secrets Status", test_secrets_status),
        ("Incident Playbooks", test_incident_playbooks),
        ("Simulate Incident", test_simulate_incident),
        ("Scaling Status", test_scaling_status),
        ("DR Plan", test_dr_plan),
        ("Hardening Checklist", test_hardening_checklist),
    ]
    
    passed = 0
    failed = 0
    results = []
    
    # Run auth test first
    try:
        result = test_auth_required()
        print(result)
        passed += 1
        results.append(("Auth Required", "PASS", result))
    except Exception as e:
        print(f"✗ Auth Required: {e}")
        failed += 1
        results.append(("Auth Required", "FAIL", str(e)))
    
    # Run authenticated tests
    for name, test_fn in auth_tests:
        try:
            result = test_fn(session)
            print(result)
            passed += 1
            results.append((name, "PASS", result))
        except Exception as e:
            print(f"✗ {name}: {e}")
            failed += 1
            results.append((name, "FAIL", str(e)))
    
    print("=" * 60)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
