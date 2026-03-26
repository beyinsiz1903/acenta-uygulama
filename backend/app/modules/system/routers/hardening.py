"""Platform Hardening API Router.

Unified router for all 10 parts of the Platform Hardening Phase.
Includes execution tracking and production activation endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/hardening", tags=["platform_hardening"])


# ============================================================================
# EXECUTION TRACKER — Phases, Blockers, Certification
# ============================================================================

@router.get("/execution/status")
async def get_execution_status(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    from app.hardening.execution_tracker import get_execution_status
    return get_execution_status()


@router.get("/execution/phase/{phase_id}")
async def get_phase_detail(
    phase_id: int,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    from app.hardening.execution_tracker import get_phase_detail
    result = get_phase_detail(phase_id)
    if result is None:
        return {"error": f"Phase {phase_id} not found"}
    return result


@router.post("/execution/phase/{phase_id}/start")
async def start_phase(
    phase_id: int,
    current_user=Depends(require_roles(["admin", "super_admin"])),
):
    from app.hardening.execution_tracker import start_phase
    return start_phase(phase_id)


@router.post("/execution/phase/{phase_id}/task/{task_id}/complete")
async def complete_task(
    phase_id: int,
    task_id: str,
    current_user=Depends(require_roles(["admin", "super_admin"])),
):
    from app.hardening.execution_tracker import complete_task
    return complete_task(phase_id, task_id)


@router.post("/execution/blocker/{blocker_id}/resolve")
async def resolve_blocker(
    blocker_id: str,
    current_user=Depends(require_roles(["admin", "super_admin"])),
):
    from app.hardening.execution_tracker import resolve_blocker
    return resolve_blocker(blocker_id)


@router.get("/execution/certification")
async def get_certification(
    current_user=Depends(require_roles(["admin", "super_admin"])),
):
    from app.hardening.execution_tracker import get_go_live_certification
    return get_go_live_certification()


# ============================================================================
# PRODUCTION ACTIVATION — Real Infrastructure Checks
# ============================================================================

@router.get("/activation/infrastructure")
async def get_infrastructure_health(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Real infrastructure health: Redis, Celery, MongoDB."""
    from app.hardening.production_activation import run_full_infrastructure_check
    return await run_full_infrastructure_check(db)


@router.get("/activation/secrets")
async def get_secret_audit(
    current_user=Depends(require_roles(["admin", "super_admin"])),
):
    """Enhanced secret management audit (v2)."""
    from app.hardening.security_engine import audit_secrets_v2
    return audit_secrets_v2()


@router.get("/activation/suppliers")
async def get_supplier_status(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Real supplier adapter status."""
    from app.hardening.production_activation import verify_supplier_adapters
    return await verify_supplier_adapters(db)


@router.get("/activation/performance")
async def get_performance_baseline(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Real performance baseline tests."""
    from app.hardening.production_activation import run_performance_baseline
    return await run_performance_baseline(db)


@router.post("/activation/incident/{incident_type}")
async def simulate_incident_endpoint(
    incident_type: str,
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
):
    """Simulate an incident: supplier_outage, queue_backlog, payment_failure."""
    from app.hardening.production_activation import simulate_incident
    return await simulate_incident(db, incident_type)


@router.get("/activation/tenant-isolation")
async def get_tenant_isolation(
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
):
    """Enhanced tenant isolation verification (v2)."""
    from app.hardening.security_engine import audit_tenant_isolation
    return await audit_tenant_isolation(db)


@router.get("/activation/metrics")
async def get_realtime_metrics(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Real-time aggregated metrics."""
    from app.hardening.production_activation import get_realtime_metrics
    return await get_realtime_metrics(db)


@router.get("/activation/dry-run")
async def run_dry_run(
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
):
    """Go-live dry run: search -> price -> book -> voucher -> notify."""
    from app.hardening.production_activation import run_go_live_dry_run
    return await run_go_live_dry_run(db)


@router.get("/activation/onboarding")
async def get_onboarding_readiness(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Agency onboarding readiness check."""
    from app.hardening.production_activation import check_onboarding_readiness
    return await check_onboarding_readiness(db)


@router.get("/activation/certification")
async def get_go_live_certification(
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
):
    """Full go-live certification with real data from all systems."""
    from app.hardening.production_activation import generate_go_live_certification
    return await generate_go_live_certification(db)


# ============================================================================
# SECURITY HARDENING — 10-Part Security Sprint
# ============================================================================

@router.get("/security/secrets")
async def security_secrets_audit(
    current_user=Depends(require_roles(["admin", "super_admin"])),
):
    """Part 1 & 2: Secret rotation & storage hardening audit."""
    from app.hardening.security_engine import audit_secrets_v2, get_secret_storage_status
    secrets = audit_secrets_v2()
    storage = get_secret_storage_status()
    return {**secrets, "storage": storage}


@router.get("/security/jwt")
async def security_jwt_audit(
    current_user=Depends(require_roles(["admin", "super_admin"])),
):
    """Part 3: JWT security verification."""
    from app.hardening.security_engine import verify_jwt_security
    return verify_jwt_security()


@router.get("/security/tenant-isolation")
async def security_tenant_audit(
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
):
    """Part 4: Tenant isolation enforcement audit."""
    from app.hardening.security_engine import audit_tenant_isolation
    return await audit_tenant_isolation(db)


@router.get("/security/rbac")
async def security_rbac_audit(
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
):
    """Part 5: RBAC permission audit."""
    from app.hardening.security_engine import audit_rbac
    return await audit_rbac(db)


@router.get("/security/api-keys")
async def security_api_keys_audit(
    current_user=Depends(require_roles(["admin", "super_admin"])),
):
    """Part 6: API key management audit."""
    from app.hardening.security_engine import audit_api_keys
    return audit_api_keys()


@router.get("/security/monitoring")
async def security_monitoring(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Part 7: Security monitoring dashboard."""
    from app.hardening.security_engine import get_security_monitoring_status
    return await get_security_monitoring_status(db)


@router.get("/security/tests")
async def security_tests(
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
):
    """Part 8: Automated security testing."""
    from app.hardening.security_engine import run_security_tests
    return await run_security_tests(db)


@router.get("/security/metrics")
async def security_metrics(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Part 9: Security metrics."""
    from app.hardening.security_engine import get_security_metrics
    return await get_security_metrics(db)


@router.get("/security/readiness")
async def security_readiness(
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
):
    """Part 10: Security readiness score."""
    from app.hardening.security_engine import calculate_security_readiness
    return await calculate_security_readiness(db)


# ============================================================================
# PART 1 — Supplier Traffic Testing
# ============================================================================

class TrafficModeRequest(BaseModel):
    supplier: str
    mode: str  # sandbox, shadow, canary, production
    ratio: float = 0.0


@router.get("/traffic/status")
async def get_traffic_status(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    from app.hardening.traffic_testing import get_traffic_testing_summary
    return await get_traffic_testing_summary(db)


@router.post("/traffic/mode")
async def set_traffic_mode(
    payload: TrafficModeRequest,
    current_user=Depends(require_roles(["admin", "super_admin"])),
):
    from app.hardening.traffic_testing import traffic_gate
    traffic_gate.set_mode(payload.supplier, payload.mode, payload.ratio)
    return {"status": "updated", "supplier": payload.supplier, "mode": payload.mode, "ratio": payload.ratio}


@router.post("/traffic/sandbox-test")
async def run_sandbox_test_endpoint(
    supplier: str = Query(...),
    scenario: Optional[str] = Query(None),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    from app.hardening.traffic_testing import run_sandbox_test
    return await run_sandbox_test(db, supplier, scenario)


# ============================================================================
# PART 2 — Worker Strategy
# ============================================================================

@router.get("/workers/status")
async def get_worker_status(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    from app.hardening.worker_strategy import get_worker_strategy_status
    return await get_worker_strategy_status(db)


# ============================================================================
# PART 3 — Observability Stack
# ============================================================================

@router.get("/observability/status")
async def get_observability_status(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    from app.hardening.observability_stack import get_observability_status as obs_status
    return await obs_status(db)


@router.get("/observability/dashboards")
async def get_grafana_dashboards(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    from app.hardening.observability_stack import GRAFANA_DASHBOARDS, ALERT_RULES
    return {"dashboards": GRAFANA_DASHBOARDS, "alert_rules": ALERT_RULES}


# ============================================================================
# PART 4 — Performance Testing
# ============================================================================

@router.get("/performance/assessment")
async def get_performance_assessment(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    from app.hardening.performance_testing import run_performance_assessment
    return await run_performance_assessment(db)


@router.get("/performance/profiles")
async def get_load_profiles(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    from app.hardening.performance_testing import LOAD_TEST_PROFILES, LOAD_TEST_SCENARIOS, SLA_TARGETS
    return {
        "profiles": LOAD_TEST_PROFILES,
        "scenarios": [{"name": s["name"], "weight": s["weight"], "steps": len(s["steps"])} for s in LOAD_TEST_SCENARIOS],
        "sla_targets": SLA_TARGETS,
    }


# ============================================================================
# PART 5 — Tenant Safety
# ============================================================================

@router.get("/tenant-safety/audit")
async def run_tenant_audit(
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
):
    from app.hardening.tenant_safety import run_tenant_isolation_audit
    return await run_tenant_isolation_audit(db)


# ============================================================================
# PART 6 — Secret Management
# ============================================================================

@router.get("/secrets/status")
async def get_secret_status(
    current_user=Depends(require_roles(["admin", "super_admin"])),
):
    from app.hardening.secret_management import get_secret_management_status
    return get_secret_management_status()


# ============================================================================
# PART 7 — Incident Playbooks
# ============================================================================

@router.get("/incidents/playbooks")
async def get_playbooks(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    from app.hardening.incident_playbooks import get_incident_playbooks
    return await get_incident_playbooks()


@router.post("/incidents/simulate")
async def simulate_incident(
    incident_type: str = Query(...),
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
):
    from app.hardening.incident_playbooks import simulate_incident_response
    return await simulate_incident_response(db, incident_type)


# ============================================================================
# PART 8 — Auto-Scaling
# ============================================================================

@router.get("/scaling/status")
async def get_scaling_status(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    from app.hardening.autoscaling_strategy import get_autoscaling_status
    return get_autoscaling_status()


# ============================================================================
# PART 9 — Disaster Recovery
# ============================================================================

@router.get("/dr/plan")
async def get_dr_plan(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    from app.hardening.disaster_recovery import get_disaster_recovery_plan
    return get_disaster_recovery_plan()


# ============================================================================
# PART 10 — Hardening Checklist
# ============================================================================

@router.get("/checklist")
async def get_checklist(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    from app.hardening.hardening_checklist import get_hardening_checklist
    return get_hardening_checklist()


# ============================================================================
# COMBINED — Full Hardening Status
# ============================================================================

@router.get("/status")
async def get_full_hardening_status(
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Get combined status of all hardening components with dual scoring."""
    from app.hardening.traffic_testing import traffic_gate
    from app.hardening.hardening_checklist import _calculate_maturity_score
    from app.hardening.secret_management import get_secret_management_status
    from app.hardening.execution_tracker import (
        _calculate_production_readiness,
        ARCHITECTURE_MATURITY,
        ARCHITECTURE_SCORES,
        GO_LIVE_BLOCKERS,
    )

    checklist = _calculate_maturity_score()
    secrets = get_secret_management_status()
    readiness = _calculate_production_readiness()

    open_blockers = [b for b in GO_LIVE_BLOCKERS if b["status"] == "open"]

    return {
        "platform_hardening_phase": "execution",
        "architecture_maturity": ARCHITECTURE_MATURITY,
        "architecture_breakdown": ARCHITECTURE_SCORES,
        "production_readiness": readiness["production_readiness_score"],
        "target_readiness": 8.5,
        "go_live_ready": readiness["go_live_ready"],
        "blockers": {
            "total": len(GO_LIVE_BLOCKERS),
            "open": len(open_blockers),
            "resolved": len(GO_LIVE_BLOCKERS) - len(open_blockers),
            "critical_items": [b["blocker"] for b in open_blockers],
        },
        "components": {
            "traffic_testing": traffic_gate.get_status(),
            "checklist_completion": checklist["summary"]["completion_pct"],
            "secrets_configured": secrets["summary"]["configured"],
            "secrets_total": secrets["summary"]["total_secrets"],
        },
        "execution_progress": {
            "total_tasks": readiness["total_tasks"],
            "completed_tasks": readiness["completed_tasks"],
            "completion_pct": readiness["completion_pct"],
        },
        "parts": [
            {"part": 1, "name": "Supplier Traffic Testing", "status": "active"},
            {"part": 2, "name": "Worker Deployment Strategy", "status": "active"},
            {"part": 3, "name": "Observability Stack", "status": "active"},
            {"part": 4, "name": "Performance Testing", "status": "active"},
            {"part": 5, "name": "Multi-Tenant Safety", "status": "active"},
            {"part": 6, "name": "Secret Management Migration", "status": "active"},
            {"part": 7, "name": "Incident Response Playbooks", "status": "active"},
            {"part": 8, "name": "Auto-Scaling Strategy", "status": "active"},
            {"part": 9, "name": "Disaster Recovery", "status": "active"},
            {"part": 10, "name": "Hardening Checklist", "status": "active"},
        ],
    }
