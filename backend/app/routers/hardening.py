"""Platform Hardening API Router.

Unified router for all 10 parts of the Platform Hardening Phase.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/hardening", tags=["platform_hardening"])


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
    """Get combined status of all hardening components."""
    from app.hardening.traffic_testing import traffic_gate
    from app.hardening.hardening_checklist import _calculate_maturity_score
    from app.hardening.secret_management import get_secret_management_status

    maturity = _calculate_maturity_score()
    secrets = get_secret_management_status()

    return {
        "platform_hardening_phase": "active",
        "maturity_score": maturity["maturity_score"],
        "maturity_label": maturity["maturity_label"],
        "go_live_ready": maturity["go_live_ready"],
        "components": {
            "traffic_testing": traffic_gate.get_status(),
            "checklist_completion": maturity["summary"]["completion_pct"],
            "secrets_configured": secrets["summary"]["configured"],
            "secrets_total": secrets["summary"]["total_secrets"],
            "critical_blockers": maturity["risk_analysis"]["critical_unresolved"],
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
