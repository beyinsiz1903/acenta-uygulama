"""Enterprise domain — audit, approvals, health, schedules, governance."""
from fastapi import APIRouter

from app.routers.enterprise_approvals import router as enterprise_approvals_router
from app.routers.enterprise_audit import router as enterprise_audit_router
from app.routers.enterprise_health import router as enterprise_health_router
from app.routers.enterprise_schedules import router as enterprise_schedules_router
from app.routers.audit import router as audit_router
from app.routers.governance import router as governance_router

domain_router = APIRouter()
domain_router.include_router(enterprise_approvals_router)
domain_router.include_router(enterprise_audit_router)
domain_router.include_router(enterprise_health_router)
domain_router.include_router(enterprise_schedules_router)
domain_router.include_router(audit_router)
domain_router.include_router(governance_router)
