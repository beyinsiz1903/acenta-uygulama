"""Enterprise Governance Architecture — API Router.

Namespace: /api/governance/*

Covers all 10 parts of the Enterprise Governance Architecture:
  PART 1 — RBAC System
  PART 2 — Permission Model
  PART 3 — Audit Logging
  PART 4 — Secret Management
  PART 5 — Tenant Security
  PART 6 — Compliance Logging
  PART 7 — Data Access Policies
  PART 8 — Security Alerting
  PART 9 — Admin Governance Panel
  PART 10 — Governance Roadmap
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth import require_roles
from app.db import get_db

logger = logging.getLogger("routers.governance")

router = APIRouter(prefix="/api/governance", tags=["enterprise_governance"])

GOV_ADMIN_ROLES = ["super_admin"]
GOV_OPS_ROLES = ["super_admin", "ops_admin"]
GOV_FINANCE_ROLES = ["super_admin", "finance_admin"]
GOV_VIEW_ROLES = ["super_admin", "ops_admin", "finance_admin", "agency_admin"]


def _org_id(request: Request) -> str:
    user = getattr(request.state, "user", {}) or {}
    return user.get("organization_id", "")


def _user_email(request: Request) -> str:
    user = getattr(request.state, "user", {}) or {}
    return user.get("email", "system")


def _user_roles(request: Request) -> list[str]:
    user = getattr(request.state, "user", {}) or {}
    return user.get("roles", [])


# ============================================================================
# PART 1 & 2 — RBAC SYSTEM & PERMISSION MODEL
# ============================================================================

class RolePermissionUpdateIn(BaseModel):
    role: str
    permissions: list[str]


@router.post("/rbac/seed", summary="[P1] Seed governance RBAC roles & permissions")
async def seed_rbac(
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.rbac_service import seed_governance_rbac
    db = await get_db()
    org_id = user.get("organization_id", "")
    return await seed_governance_rbac(db, org_id, user.get("email", ""))


@router.get("/rbac/roles", summary="[P1] List all roles with hierarchy")
async def list_roles(
    request: Request,
    user=Depends(require_roles(GOV_VIEW_ROLES)),
):
    from app.domain.governance.rbac_service import list_roles as _list_roles
    db = await get_db()
    return await _list_roles(db, user.get("organization_id", ""))


@router.get("/rbac/hierarchy", summary="[P1] Get role hierarchy tree")
async def get_hierarchy(
    request: Request,
    user=Depends(require_roles(GOV_VIEW_ROLES)),
):
    from app.domain.governance.rbac_service import get_role_hierarchy
    db = await get_db()
    return await get_role_hierarchy(db, user.get("organization_id", ""))


@router.get("/rbac/permissions", summary="[P2] List all available permissions")
async def list_permissions(
    request: Request,
    user=Depends(require_roles(GOV_VIEW_ROLES)),
):
    from app.domain.governance.rbac_service import list_permissions as _list_perms
    db = await get_db()
    return await _list_perms(db, user.get("organization_id", ""))


@router.put("/rbac/roles", summary="[P1] Update role permissions")
async def update_role_permissions(
    payload: RolePermissionUpdateIn,
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.rbac_service import update_role_permissions as _update
    from app.domain.governance.audit_service import log_governance_action
    db = await get_db()
    org_id = user.get("organization_id", "")
    result = await _update(db, org_id, payload.role, payload.permissions, user.get("email", ""))
    await log_governance_action(
        db, org_id=org_id, actor_email=user.get("email", ""),
        actor_roles=user.get("roles", []), action="governance.rbac.update_role",
        resource_type="role", resource_id=payload.role,
        category="rbac", after_value={"role": payload.role, "permissions": payload.permissions},
    )
    return result


@router.get("/rbac/user-permissions", summary="[P2] Resolve user effective permissions")
async def resolve_user_perms(
    request: Request,
    user_email: str = Query(...),
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.rbac_service import resolve_user_permissions
    db = await get_db()
    org_id = user.get("organization_id", "")
    target_user = await db.users.find_one({"email": user_email, "organization_id": org_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    roles = target_user.get("roles", [])
    return await resolve_user_permissions(db, org_id, roles)


@router.get("/rbac/check-permission", summary="[P2] Check if user has specific permission")
async def check_permission(
    request: Request,
    user_email: str = Query(...),
    permission: str = Query(...),
    user=Depends(require_roles(GOV_VIEW_ROLES)),
):
    from app.domain.governance.rbac_service import check_permission as _check
    db = await get_db()
    org_id = user.get("organization_id", "")
    target_user = await db.users.find_one({"email": user_email, "organization_id": org_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    roles = target_user.get("roles", [])
    has_perm = await _check(db, org_id, roles, permission)
    return {"user_email": user_email, "permission": permission, "granted": has_perm}


# ============================================================================
# PART 3 — AUDIT LOGGING
# ============================================================================

@router.get("/audit/logs", summary="[P3] Search audit logs")
async def search_audit_logs(
    request: Request,
    actor_email: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user=Depends(require_roles(GOV_VIEW_ROLES)),
):
    from app.domain.governance.audit_service import search_audit_logs as _search
    db = await get_db()
    return await _search(
        db, user.get("organization_id", ""),
        actor_email=actor_email, action=action,
        resource_type=resource_type, category=category,
        limit=limit, skip=skip,
    )


@router.get("/audit/logs/{audit_id}", summary="[P3] Get single audit entry")
async def get_audit_entry(
    audit_id: str,
    request: Request,
    user=Depends(require_roles(GOV_VIEW_ROLES)),
):
    from app.domain.governance.audit_service import get_audit_entry as _get
    db = await get_db()
    entry = await _get(db, user.get("organization_id", ""), audit_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return entry


@router.get("/audit/stats", summary="[P3] Get audit log statistics")
async def get_audit_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    user=Depends(require_roles(GOV_VIEW_ROLES)),
):
    from app.domain.governance.audit_service import get_audit_stats as _stats
    db = await get_db()
    return await _stats(db, user.get("organization_id", ""), days)


# ============================================================================
# PART 4 — SECRET MANAGEMENT
# ============================================================================

class SecretStoreIn(BaseModel):
    name: str
    value: str
    secret_type: str = "api_key"
    description: str = ""
    rotation_days: int = 90


@router.post("/secrets", summary="[P4] Store or rotate a secret")
async def store_secret(
    payload: SecretStoreIn,
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.secret_service import store_secret as _store
    from app.domain.governance.audit_service import log_governance_action
    db = await get_db()
    org_id = user.get("organization_id", "")
    result = await _store(
        db, org_id,
        name=payload.name, value=payload.value,
        secret_type=payload.secret_type, description=payload.description,
        actor_email=user.get("email", ""), rotation_days=payload.rotation_days,
    )
    await log_governance_action(
        db, org_id=org_id, actor_email=user.get("email", ""),
        actor_roles=user.get("roles", []), action=f"secret.{result['action']}",
        resource_type="secret", resource_id=payload.name, category="secret",
    )
    return result


@router.get("/secrets", summary="[P4] List all secrets (masked)")
async def list_secrets(
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.secret_service import list_secrets as _list
    db = await get_db()
    return await _list(db, user.get("organization_id", ""))


@router.get("/secrets/{name}/value", summary="[P4] Retrieve secret value (logged)")
async def get_secret_value(
    name: str,
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.secret_service import get_secret_value as _get
    from app.domain.governance.audit_service import log_governance_action
    db = await get_db()
    org_id = user.get("organization_id", "")
    result = await _get(db, org_id, name, user.get("email", ""))
    if not result:
        raise HTTPException(status_code=404, detail="Secret not found")
    await log_governance_action(
        db, org_id=org_id, actor_email=user.get("email", ""),
        actor_roles=user.get("roles", []), action="secret.access",
        resource_type="secret", resource_id=name, category="secret",
    )
    return result


@router.delete("/secrets/{name}", summary="[P4] Delete a secret")
async def delete_secret(
    name: str,
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.secret_service import delete_secret as _delete
    from app.domain.governance.audit_service import log_governance_action
    db = await get_db()
    org_id = user.get("organization_id", "")
    result = await _delete(db, org_id, name, user.get("email", ""))
    await log_governance_action(
        db, org_id=org_id, actor_email=user.get("email", ""),
        actor_roles=user.get("roles", []), action="secret.delete",
        resource_type="secret", resource_id=name, category="secret",
    )
    return result


@router.get("/secrets/rotation/status", summary="[P4] Check secret rotation status")
async def check_rotation(
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.secret_service import check_rotation_status
    db = await get_db()
    return await check_rotation_status(db, user.get("organization_id", ""))


# ============================================================================
# PART 5 — TENANT SECURITY
# ============================================================================

@router.get("/tenant/isolation-report", summary="[P5] Tenant isolation health report")
async def tenant_isolation_report(
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.tenant_security_service import get_tenant_isolation_report
    db = await get_db()
    return await get_tenant_isolation_report(db, user.get("organization_id", ""))


@router.get("/tenant/violations", summary="[P5] List tenant isolation violations")
async def list_violations(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.tenant_security_service import list_tenant_violations
    db = await get_db()
    return await list_tenant_violations(db, user.get("organization_id", ""), limit, skip)


class TenantAccessValidateIn(BaseModel):
    target_org_id: str
    resource_type: str
    action: str


@router.post("/tenant/validate-access", summary="[P5] Validate tenant boundary access")
async def validate_tenant_access(
    payload: TenantAccessValidateIn,
    request: Request,
    user=Depends(require_roles(GOV_VIEW_ROLES)),
):
    from app.domain.governance.tenant_security_service import validate_tenant_access as _validate
    db = await get_db()
    return await _validate(
        db,
        requesting_org_id=user.get("organization_id", ""),
        target_org_id=payload.target_org_id,
        resource_type=payload.resource_type,
        action=payload.action,
        actor_email=user.get("email", ""),
    )


# ============================================================================
# PART 6 — COMPLIANCE LOGGING
# ============================================================================

class ComplianceLogIn(BaseModel):
    operation_type: str
    amount: float
    currency: str = "EUR"
    booking_id: str = ""
    payment_id: str = ""
    invoice_id: str = ""
    counterparty: str = ""
    tax_details: Optional[dict] = None
    metadata: Optional[dict] = None


@router.post("/compliance/log", summary="[P6] Log a financial operation")
async def log_financial_op(
    payload: ComplianceLogIn,
    request: Request,
    user=Depends(require_roles(GOV_FINANCE_ROLES)),
):
    from app.domain.governance.compliance_service import log_financial_operation
    db = await get_db()
    return await log_financial_operation(
        db, user.get("organization_id", ""),
        operation_type=payload.operation_type,
        amount=payload.amount, currency=payload.currency,
        booking_id=payload.booking_id, payment_id=payload.payment_id,
        invoice_id=payload.invoice_id, actor_email=user.get("email", ""),
        counterparty=payload.counterparty, tax_details=payload.tax_details,
        metadata=payload.metadata,
    )


@router.get("/compliance/logs", summary="[P6] Search compliance logs")
async def search_compliance_logs(
    request: Request,
    operation_type: Optional[str] = Query(None),
    booking_id: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user=Depends(require_roles(GOV_FINANCE_ROLES)),
):
    from app.domain.governance.compliance_service import search_compliance_logs as _search
    db = await get_db()
    return await _search(
        db, user.get("organization_id", ""),
        operation_type=operation_type, booking_id=booking_id,
        currency=currency, min_amount=min_amount, max_amount=max_amount,
        limit=limit, skip=skip,
    )


@router.get("/compliance/verify-chain", summary="[P6] Verify compliance log chain integrity")
async def verify_chain(
    request: Request,
    last_n: int = Query(100, ge=10, le=1000),
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.compliance_service import verify_compliance_chain
    db = await get_db()
    return await verify_compliance_chain(db, user.get("organization_id", ""), last_n)


@router.get("/compliance/summary", summary="[P6] Get compliance summary")
async def compliance_summary(
    request: Request,
    days: int = Query(90, ge=1, le=365),
    user=Depends(require_roles(GOV_FINANCE_ROLES)),
):
    from app.domain.governance.compliance_service import get_compliance_summary
    db = await get_db()
    return await get_compliance_summary(db, user.get("organization_id", ""), days)


# ============================================================================
# PART 7 — DATA ACCESS POLICIES
# ============================================================================

class DataPolicyCreateIn(BaseModel):
    name: str
    description: str = ""
    resource: str
    effect: str = "deny"
    conditions: dict = {}
    applies_to_roles: list[str] = []


class DataPolicyUpdateIn(BaseModel):
    description: Optional[str] = None
    effect: Optional[str] = None
    conditions: Optional[dict] = None
    applies_to_roles: Optional[list[str]] = None
    priority: Optional[int] = None


@router.post("/data-policies", summary="[P7] Create a data access policy")
async def create_data_policy(
    payload: DataPolicyCreateIn,
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.data_access_service import create_data_access_policy
    from app.domain.governance.audit_service import log_governance_action
    db = await get_db()
    org_id = user.get("organization_id", "")
    result = await create_data_access_policy(
        db, org_id,
        name=payload.name, description=payload.description,
        resource=payload.resource, effect=payload.effect,
        conditions=payload.conditions, applies_to_roles=payload.applies_to_roles,
        actor_email=user.get("email", ""),
    )
    await log_governance_action(
        db, org_id=org_id, actor_email=user.get("email", ""),
        actor_roles=user.get("roles", []), action="data_policy.create",
        resource_type="data_policy", resource_id=payload.name, category="data_access",
    )
    return result


@router.get("/data-policies", summary="[P7] List data access policies")
async def list_data_policies(
    request: Request,
    resource: Optional[str] = Query(None),
    user=Depends(require_roles(GOV_VIEW_ROLES)),
):
    from app.domain.governance.data_access_service import list_data_access_policies
    db = await get_db()
    return await list_data_access_policies(db, user.get("organization_id", ""), resource)


class DataAccessEvaluateIn(BaseModel):
    resource: str
    action: str
    context: Optional[dict] = None


@router.post("/data-policies/evaluate", summary="[P7] Evaluate data access request")
async def evaluate_data_access(
    payload: DataAccessEvaluateIn,
    request: Request,
    user=Depends(require_roles(GOV_VIEW_ROLES)),
):
    from app.domain.governance.data_access_service import evaluate_data_access as _eval
    db = await get_db()
    return await _eval(
        db, user.get("organization_id", ""),
        user_roles=user.get("roles", []),
        resource=payload.resource, action=payload.action,
        context=payload.context,
    )


@router.put("/data-policies/{policy_id}", summary="[P7] Update data access policy")
async def update_data_policy(
    policy_id: str,
    payload: DataPolicyUpdateIn,
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.data_access_service import update_data_access_policy
    db = await get_db()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    return await update_data_access_policy(
        db, user.get("organization_id", ""), policy_id,
        updates=updates, actor_email=user.get("email", ""),
    )


@router.delete("/data-policies/{policy_id}", summary="[P7] Delete data access policy")
async def delete_data_policy(
    policy_id: str,
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.data_access_service import delete_data_access_policy
    from app.domain.governance.audit_service import log_governance_action
    db = await get_db()
    org_id = user.get("organization_id", "")
    result = await delete_data_access_policy(
        db, org_id, policy_id, user.get("email", ""),
    )
    await log_governance_action(
        db, org_id=org_id, actor_email=user.get("email", ""),
        actor_roles=user.get("roles", []), action="data_policy.delete",
        resource_type="data_policy", resource_id=policy_id, category="data_access",
    )
    return result


@router.post("/data-policies/seed", summary="[P7] Seed default data access policies")
async def seed_default_policies(
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    from app.domain.governance.data_access_service import seed_default_policies as _seed
    db = await get_db()
    return await _seed(db, user.get("organization_id", ""), user.get("email", ""))


# ============================================================================
# PART 8 — SECURITY ALERTING
# ============================================================================

class SecurityAlertCreateIn(BaseModel):
    alert_type: str
    severity: str = "medium"
    title: str
    description: str = ""
    actor_email: str = ""
    source_ip: str = ""
    affected_resource: str = ""
    evidence: Optional[dict] = None


@router.post("/security/alerts", summary="[P8] Create a security alert")
async def create_security_alert(
    payload: SecurityAlertCreateIn,
    request: Request,
    user=Depends(require_roles(GOV_OPS_ROLES)),
):
    from app.domain.governance.security_alerting_service import create_security_alert as _create
    db = await get_db()
    return await _create(
        db, user.get("organization_id", ""),
        alert_type=payload.alert_type, severity=payload.severity,
        title=payload.title, description=payload.description,
        actor_email=payload.actor_email, source_ip=payload.source_ip,
        affected_resource=payload.affected_resource, evidence=payload.evidence,
    )


@router.get("/security/alerts", summary="[P8] List security alerts")
async def list_security_alerts(
    request: Request,
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user=Depends(require_roles(GOV_OPS_ROLES)),
):
    from app.domain.governance.security_alerting_service import list_security_alerts as _list
    db = await get_db()
    return await _list(
        db, user.get("organization_id", ""),
        status=status, severity=severity, alert_type=alert_type,
        limit=limit, skip=skip,
    )


@router.post("/security/alerts/{alert_id}/acknowledge", summary="[P8] Acknowledge security alert")
async def ack_security_alert(
    alert_id: str,
    request: Request,
    user=Depends(require_roles(GOV_OPS_ROLES)),
):
    from app.domain.governance.security_alerting_service import acknowledge_security_alert
    from app.domain.governance.audit_service import log_governance_action
    db = await get_db()
    org_id = user.get("organization_id", "")
    result = await acknowledge_security_alert(db, org_id, alert_id, user.get("email", ""))
    await log_governance_action(
        db, org_id=org_id, actor_email=user.get("email", ""),
        actor_roles=user.get("roles", []), action="security_alert.acknowledge",
        resource_type="security_alert", resource_id=alert_id, category="governance",
    )
    return result


@router.post("/security/alerts/{alert_id}/resolve", summary="[P8] Resolve security alert")
async def resolve_security_alert(
    alert_id: str,
    request: Request,
    resolution: str = Query(""),
    user=Depends(require_roles(GOV_OPS_ROLES)),
):
    from app.domain.governance.security_alerting_service import resolve_security_alert as _resolve
    from app.domain.governance.audit_service import log_governance_action
    db = await get_db()
    org_id = user.get("organization_id", "")
    result = await _resolve(db, org_id, alert_id, user.get("email", ""), resolution)
    await log_governance_action(
        db, org_id=org_id, actor_email=user.get("email", ""),
        actor_roles=user.get("roles", []), action="security_alert.resolve",
        resource_type="security_alert", resource_id=alert_id, category="governance",
    )
    return result


@router.get("/security/dashboard", summary="[P8] Security alerting dashboard")
async def security_dashboard(
    request: Request,
    user=Depends(require_roles(GOV_OPS_ROLES)),
):
    from app.domain.governance.security_alerting_service import get_security_dashboard
    db = await get_db()
    return await get_security_dashboard(db, user.get("organization_id", ""))


@router.post("/security/detect/suspicious-login", summary="[P8] Detect suspicious login")
async def detect_suspicious_login(
    request: Request,
    target_email: str = Query(...),
    ip_address: str = Query(""),
    user=Depends(require_roles(GOV_OPS_ROLES)),
):
    from app.domain.governance.security_alerting_service import detect_suspicious_login as _detect
    db = await get_db()
    result = await _detect(db, user.get("organization_id", ""), target_email, ip_address)
    return result or {"alert": None, "status": "no_suspicious_activity"}


# ============================================================================
# PART 9 — ADMIN GOVERNANCE PANEL (Aggregated views)
# ============================================================================

@router.get("/panel/overview", summary="[P9] Governance panel overview")
async def governance_overview(
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    """Aggregated governance dashboard for admin panel."""
    from app.domain.governance.audit_service import get_audit_stats
    from app.domain.governance.security_alerting_service import get_security_dashboard
    from app.domain.governance.secret_service import check_rotation_status
    from app.domain.governance.tenant_security_service import get_tenant_isolation_report
    from app.domain.governance.compliance_service import get_compliance_summary
    from app.domain.governance.rbac_service import list_roles as _list_roles

    db = await get_db()
    org_id = user.get("organization_id", "")

    roles = await _list_roles(db, org_id)
    audit_stats = await get_audit_stats(db, org_id, 30)
    security = await get_security_dashboard(db, org_id)
    secrets_rotation = await check_rotation_status(db, org_id)
    tenant_report = await get_tenant_isolation_report(db, org_id)
    compliance = await get_compliance_summary(db, org_id, 90)

    overdue_secrets = sum(1 for s in secrets_rotation if s.get("needs_rotation"))

    return {
        "rbac": {
            "total_roles": len(roles),
            "roles": [r.get("role") for r in roles],
        },
        "audit": audit_stats,
        "security": {
            "open_alerts": security.get("open_alerts", 0),
            "critical_alerts": security.get("open_critical", 0),
        },
        "secrets": {
            "total_secrets": len(secrets_rotation),
            "overdue_rotation": overdue_secrets,
        },
        "tenant_isolation": {
            "score": tenant_report.get("isolation_score", 0),
            "violations_30d": tenant_report.get("violations_detected", 0),
        },
        "compliance": {
            "total_entries_90d": compliance.get("total_entries", 0),
            "chain_integrity": compliance.get("chain_integrity", "unknown"),
        },
    }


@router.get("/panel/user/{user_email}", summary="[P9] Inspect user governance profile")
async def inspect_user(
    user_email: str,
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    """Full governance profile for a specific user."""
    from app.domain.governance.rbac_service import resolve_user_permissions
    from app.domain.governance.audit_service import search_audit_logs

    db = await get_db()
    org_id = user.get("organization_id", "")

    target = await db.users.find_one(
        {"email": user_email, "organization_id": org_id},
        {"_id": 0, "password_hash": 0, "hashed_password": 0},
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    perms = await resolve_user_permissions(db, org_id, target.get("roles", []))
    recent_audit = await search_audit_logs(
        db, org_id, actor_email=user_email, limit=10,
    )

    return {
        "user": {
            "email": target.get("email"),
            "name": target.get("name", ""),
            "roles": target.get("roles", []),
            "is_active": target.get("is_active", True),
        },
        "permissions": perms,
        "recent_activity": recent_audit.get("items", [])[:10],
    }


# ============================================================================
# PART 10 — GOVERNANCE ROADMAP
# ============================================================================

@router.get("/roadmap", summary="[P10] Governance roadmap & maturity score")
async def governance_roadmap(
    request: Request,
    user=Depends(require_roles(GOV_ADMIN_ROLES)),
):
    """Top 25 governance improvements and security maturity score."""
    db = await get_db()
    org_id = user.get("organization_id", "")

    # Compute maturity score based on actual state
    score_components = {}

    # RBAC maturity
    roles_count = await db.gov_roles.count_documents({"organization_id": org_id})
    score_components["rbac_configured"] = min(roles_count * 3, 15)

    # Audit logging
    audit_count = await db.gov_audit_log.count_documents({"organization_id": org_id})
    score_components["audit_active"] = 10 if audit_count > 0 else 0

    # Secret management
    secrets_count = await db.gov_secrets.count_documents({"organization_id": org_id, "is_active": True})
    score_components["secrets_managed"] = min(secrets_count * 2, 10)

    # Compliance logging
    compliance_count = await db.gov_compliance_log.count_documents({"organization_id": org_id})
    score_components["compliance_active"] = 10 if compliance_count > 0 else 0

    # Data policies
    policies_count = await db.gov_data_policies.count_documents({"organization_id": org_id, "is_active": True})
    score_components["data_policies"] = min(policies_count * 3, 10)

    # Security alerting
    alerts_configured = await db.gov_security_alerts.count_documents({"organization_id": org_id})
    score_components["security_alerting"] = 10 if alerts_configured > 0 else 5

    # Tenant isolation base score
    score_components["tenant_isolation_base"] = 10

    total_score = sum(score_components.values())
    max_score = 75

    improvements = [
        {"rank": 1, "category": "RBAC", "title": "Enforce permission checks on ALL endpoints", "impact": "critical", "effort": "high", "status": "in_progress"},
        {"rank": 2, "category": "Tenant", "title": "Add org_id compound indexes on ALL collections", "impact": "critical", "effort": "medium", "status": "partial"},
        {"rank": 3, "category": "Secret", "title": "Migrate from base64 to Vault/KMS encryption", "impact": "critical", "effort": "high", "status": "planned"},
        {"rank": 4, "category": "Audit", "title": "Enable audit logging middleware for ALL routes", "impact": "high", "effort": "medium", "status": "planned"},
        {"rank": 5, "category": "RBAC", "title": "Implement API-level permission middleware", "impact": "critical", "effort": "high", "status": "planned"},
        {"rank": 6, "category": "Compliance", "title": "Auto-log all payment and refund operations", "impact": "high", "effort": "medium", "status": "planned"},
        {"rank": 7, "category": "Security", "title": "Implement real-time brute-force detection", "impact": "high", "effort": "medium", "status": "in_progress"},
        {"rank": 8, "category": "Tenant", "title": "Row-level security for MongoDB queries", "impact": "critical", "effort": "high", "status": "planned"},
        {"rank": 9, "category": "Secret", "title": "Implement automatic secret rotation scheduler", "impact": "high", "effort": "medium", "status": "planned"},
        {"rank": 10, "category": "RBAC", "title": "Add session-based permission caching (Redis)", "impact": "medium", "effort": "low", "status": "planned"},
        {"rank": 11, "category": "Audit", "title": "Implement tamper-proof audit chain (hash-linked)", "impact": "high", "effort": "medium", "status": "done"},
        {"rank": 12, "category": "Security", "title": "Add anomaly detection for mass data exports", "impact": "high", "effort": "medium", "status": "in_progress"},
        {"rank": 13, "category": "Compliance", "title": "Integrate with external tax reporting APIs", "impact": "medium", "effort": "high", "status": "planned"},
        {"rank": 14, "category": "RBAC", "title": "Implement attribute-based access control (ABAC)", "impact": "medium", "effort": "high", "status": "future"},
        {"rank": 15, "category": "Tenant", "title": "Implement tenant data encryption at rest", "impact": "high", "effort": "high", "status": "planned"},
        {"rank": 16, "category": "Security", "title": "Add Slack/email notifications for critical alerts", "impact": "high", "effort": "low", "status": "planned"},
        {"rank": 17, "category": "Audit", "title": "Implement audit log export to S3/GCS", "impact": "medium", "effort": "low", "status": "planned"},
        {"rank": 18, "category": "Compliance", "title": "Add GDPR data retention automation", "impact": "high", "effort": "medium", "status": "planned"},
        {"rank": 19, "category": "Secret", "title": "Implement secret access approval workflow", "impact": "medium", "effort": "medium", "status": "future"},
        {"rank": 20, "category": "RBAC", "title": "Add time-based role elevation (break-glass)", "impact": "medium", "effort": "medium", "status": "future"},
        {"rank": 21, "category": "Security", "title": "Implement IP-based geo-blocking", "impact": "medium", "effort": "low", "status": "planned"},
        {"rank": 22, "category": "Tenant", "title": "Add cross-tenant query monitoring dashboard", "impact": "medium", "effort": "medium", "status": "planned"},
        {"rank": 23, "category": "Compliance", "title": "Automated PCI-DSS compliance checklist", "impact": "high", "effort": "high", "status": "future"},
        {"rank": 24, "category": "Audit", "title": "Real-time audit stream via WebSocket", "impact": "low", "effort": "medium", "status": "future"},
        {"rank": 25, "category": "Security", "title": "ML-based insider threat detection", "impact": "medium", "effort": "high", "status": "future"},
    ]

    return {
        "security_maturity_score": {
            "score": total_score,
            "max_score": max_score,
            "percentage": round((total_score / max_score) * 100, 1),
            "grade": _compute_grade(total_score, max_score),
            "components": score_components,
        },
        "top_25_improvements": improvements,
        "risk_analysis": {
            "critical_risks": [
                "Endpoints not enforcing fine-grained permission checks",
                "Secrets stored with base64 encoding (not production-grade encryption)",
                "No automatic secret rotation",
                "Cross-tenant queries possible without row-level enforcement on all collections",
            ],
            "high_risks": [
                "Audit logs not enabled on all sensitive routes",
                "No real-time alerting integration (Slack/PagerDuty)",
                "Compliance logs not auto-generated from payment flows",
                "Data access policies not enforced at query layer",
            ],
            "medium_risks": [
                "No ABAC (attribute-based access control)",
                "No session-based permission caching",
                "Audit logs not exported to external storage",
                "No geo-blocking for login attempts",
            ],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _compute_grade(score: int, max_score: int) -> str:
    pct = (score / max_score) * 100 if max_score > 0 else 0
    if pct >= 80:
        return "A"
    if pct >= 65:
        return "B"
    if pct >= 50:
        return "C"
    if pct >= 35:
        return "D"
    return "F"
