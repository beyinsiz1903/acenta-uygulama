"""Reconciliation & Finance Operations API Router.

Endpoints for:
- Reconciliation runs and items
- Finance ops queue management
- Financial alerts
- Aging KPI

RBAC:
- super_admin / finance_admin: full access
- agency_admin: view own tenant, add note, request retry/escalation
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import require_roles

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])

ALLOWED_ROLES = ["super_admin", "admin", "agency_admin", "finance_admin"]
WRITE_ROLES = ["super_admin", "admin", "finance_admin"]


def _extract_role(user: dict) -> str:
    """Extract the primary role from user dict (handles roles list)."""
    roles = user.get("roles") or []
    if isinstance(roles, list) and roles:
        return roles[0]
    return user.get("role", "")


# ── Request Models ────────────────────────────────────────────

class RunReconciliationIn(BaseModel):
    run_type: str = "manual"
    lookback_hours: Optional[int] = None


class ClaimOpsIn(BaseModel):
    ops_id: str


class ResolveOpsIn(BaseModel):
    ops_id: str
    resolution_note: str = ""


class EscalateOpsIn(BaseModel):
    ops_id: str
    reason: str = ""


class AddNoteIn(BaseModel):
    ops_id: str
    note_text: str


class RequestRetryIn(BaseModel):
    ops_id: str


class AcknowledgeAlertIn(BaseModel):
    alert_id: str


class ResolveAlertIn(BaseModel):
    alert_id: str


# ── Reconciliation ────────────────────────────────────────────

@router.post("/run")
async def run_reconciliation_endpoint(
    payload: RunReconciliationIn,
    user=Depends(require_roles(WRITE_ROLES)),
):
    """Trigger a reconciliation run (manual or specified type)."""
    from app.accounting.reconciliation_service import run_reconciliation
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await run_reconciliation(
        tenant_id=tenant_id,
        run_type=payload.run_type,
        triggered_by=user.get("email", ""),
        lookback_hours=payload.lookback_hours,
    )
    return result


@router.get("/runs")
async def list_runs_endpoint(
    run_type: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    skip: int = Query(0, ge=0),
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """List reconciliation runs."""
    from app.accounting.reconciliation_service import list_runs
    tenant_id = user.get("tenant_id", user["organization_id"])
    return await list_runs(tenant_id, run_type=run_type, limit=limit, skip=skip)


@router.get("/items")
async def list_items_endpoint(
    run_id: Optional[str] = Query(None),
    mismatch_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    resolution_state: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0, ge=0),
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """List reconciliation mismatch items."""
    from app.accounting.reconciliation_service import list_items
    tenant_id = user.get("tenant_id", user["organization_id"])
    return await list_items(
        tenant_id, run_id=run_id, mismatch_type=mismatch_type,
        severity=severity, resolution_state=resolution_state,
        limit=limit, skip=skip,
    )


@router.get("/aging")
async def aging_stats_endpoint(
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """Get unsynced invoice aging stats (CTO KPI)."""
    from app.accounting.reconciliation_service import get_aging_stats
    tenant_id = user.get("tenant_id", user["organization_id"])
    return await get_aging_stats(tenant_id)


@router.get("/summary")
async def reconciliation_summary_endpoint(
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """Get overall reconciliation summary for dashboard."""
    from app.accounting.reconciliation_service import get_reconciliation_summary
    tenant_id = user.get("tenant_id", user["organization_id"])
    return await get_reconciliation_summary(tenant_id)


# ── Finance Ops Queue ─────────────────────────────────────────

@router.get("/ops")
async def list_ops_endpoint(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0, ge=0),
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """List finance ops queue items."""
    from app.accounting.finance_ops_service import list_ops_items
    role = user.get("role", "")
    if not role:
        roles = user.get("roles") or []
        role = roles[0] if roles else ""
    if role in ("super_admin", "admin"):
        tenant_id = None
    else:
        tenant_id = user.get("tenant_id", user["organization_id"])
    return await list_ops_items(tenant_id=tenant_id, status=status, priority=priority, limit=limit, skip=skip)


@router.get("/ops/stats")
async def ops_stats_endpoint(
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """Get finance ops queue stats."""
    from app.accounting.finance_ops_service import get_ops_stats
    role = user.get("role", "")
    if not role:
        roles = user.get("roles") or []
        role = roles[0] if roles else ""
    if role in ("super_admin", "admin"):
        tenant_id = None
    else:
        tenant_id = user.get("tenant_id", user["organization_id"])
    return await get_ops_stats(tenant_id)


@router.post("/ops/claim")
async def claim_ops_endpoint(
    payload: ClaimOpsIn,
    user=Depends(require_roles(WRITE_ROLES)),
):
    """Claim a finance ops item."""
    from app.accounting.finance_ops_service import claim_ops_item
    tenant_id = user.get("tenant_id", user["organization_id"])
    role = user.get("role", "")
    if not role:
        roles = user.get("roles") or []
        role = roles[0] if roles else ""
    result = await claim_ops_item(
        payload.ops_id, user.get("email", ""), role,
        tenant_id=tenant_id if role not in ("super_admin", "admin") else None,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Ops kaydı bulunamadı")
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    return result


@router.post("/ops/resolve")
async def resolve_ops_endpoint(
    payload: ResolveOpsIn,
    user=Depends(require_roles(WRITE_ROLES)),
):
    """Resolve a finance ops item."""
    from app.accounting.finance_ops_service import resolve_ops_item
    tenant_id = user.get("tenant_id", user["organization_id"])
    role = user.get("role", "")
    if not role:
        roles = user.get("roles") or []
        role = roles[0] if roles else ""
    result = await resolve_ops_item(
        payload.ops_id, user.get("email", ""), role,
        resolution_note=payload.resolution_note,
        tenant_id=tenant_id if role not in ("super_admin", "admin") else None,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Ops kaydı bulunamadı")
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    return result


@router.post("/ops/escalate")
async def escalate_ops_endpoint(
    payload: EscalateOpsIn,
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """Escalate a finance ops item (agency_admin can also do this)."""
    from app.accounting.finance_ops_service import escalate_ops_item
    tenant_id = user.get("tenant_id", user["organization_id"])
    role = user.get("role", "")
    if not role:
        roles = user.get("roles") or []
        role = roles[0] if roles else ""
    result = await escalate_ops_item(
        payload.ops_id, user.get("email", ""), role,
        reason=payload.reason,
        tenant_id=tenant_id if role not in ("super_admin", "admin") else None,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Ops kaydı bulunamadı")
    return result


@router.post("/ops/note")
async def add_note_endpoint(
    payload: AddNoteIn,
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """Add a note to a finance ops item."""
    from app.accounting.finance_ops_service import add_note
    tenant_id = user.get("tenant_id", user["organization_id"])
    role = user.get("role", "")
    if not role:
        roles = user.get("roles") or []
        role = roles[0] if roles else ""
    result = await add_note(
        payload.ops_id, user.get("email", ""), role,
        note_text=payload.note_text,
        tenant_id=tenant_id if role not in ("super_admin", "admin") else None,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Ops kaydı bulunamadı")
    return result


@router.post("/ops/retry")
async def request_retry_endpoint(
    payload: RequestRetryIn,
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """Request retry on a finance ops item."""
    from app.accounting.finance_ops_service import request_retry
    tenant_id = user.get("tenant_id", user["organization_id"])
    role = user.get("role", "")
    if not role:
        roles = user.get("roles") or []
        role = roles[0] if roles else ""
    result = await request_retry(
        payload.ops_id, user.get("email", ""), role,
        tenant_id=tenant_id if role not in ("super_admin", "admin") else None,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Ops kaydı bulunamadı")
    return result


# ── Financial Alerts ──────────────────────────────────────────

@router.get("/alerts")
async def list_alerts_endpoint(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0, ge=0),
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """List financial alerts."""
    from app.accounting.financial_alerts_service import list_alerts
    tenant_id = user.get("tenant_id", user["organization_id"])
    return await list_alerts(tenant_id=tenant_id, status=status, severity=severity, limit=limit, skip=skip)


@router.get("/alerts/stats")
async def alert_stats_endpoint(
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """Get alert stats."""
    from app.accounting.financial_alerts_service import get_alert_stats
    tenant_id = user.get("tenant_id", user["organization_id"])
    return await get_alert_stats(tenant_id)


@router.post("/alerts/acknowledge")
async def acknowledge_alert_endpoint(
    payload: AcknowledgeAlertIn,
    user=Depends(require_roles(WRITE_ROLES)),
):
    """Acknowledge an alert."""
    from app.accounting.financial_alerts_service import acknowledge_alert
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await acknowledge_alert(payload.alert_id, user.get("email", ""), tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Alert bulunamadı")
    return result


@router.post("/alerts/resolve")
async def resolve_alert_endpoint(
    payload: ResolveAlertIn,
    user=Depends(require_roles(WRITE_ROLES)),
):
    """Resolve an alert."""
    from app.accounting.financial_alerts_service import resolve_alert
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await resolve_alert(payload.alert_id, user.get("email", ""), tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Alert bulunamadı")
    return result
