"""Enterprise domain — audit, approvals, health, schedules, governance, risk, policies.

Owner: Enterprise Domain
Boundary: All enterprise governance — audit trails, approval workflows,
          risk snapshots, action policies, IP whitelist, schedules.

Phase 2, Dalga 5 additions: risk_snapshots, action_policies, approval_tasks.
"""
from fastapi import APIRouter

from app.modules.enterprise.routers.enterprise_approvals import router as enterprise_approvals_router
from app.modules.enterprise.routers.enterprise_audit import router as enterprise_audit_router
from app.modules.enterprise.routers.enterprise_health import router as enterprise_health_router
from app.modules.enterprise.routers.enterprise_schedules import router as enterprise_schedules_router
from app.modules.enterprise.routers.audit import router as audit_router
from app.modules.enterprise.routers.governance import router as governance_router

# --- Phase 2, Dalga 5 additions ---
from app.modules.enterprise.routers.risk_snapshots import router as risk_snapshots_router
from app.modules.enterprise.routers.action_policies import router as action_policies_router
from app.modules.enterprise.routers.approval_tasks import router as approval_tasks_router

domain_router = APIRouter()
domain_router.include_router(enterprise_approvals_router)
domain_router.include_router(enterprise_audit_router)
domain_router.include_router(enterprise_health_router)
domain_router.include_router(enterprise_schedules_router)
domain_router.include_router(audit_router)
domain_router.include_router(governance_router)
domain_router.include_router(risk_snapshots_router)
domain_router.include_router(action_policies_router)
domain_router.include_router(approval_tasks_router)
