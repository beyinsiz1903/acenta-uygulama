"""Enterprise Approval Workflow router (E1.2).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.approval_service import (
    approve_request,
    create_approval_request,
    get_approval,
    list_approvals,
    reject_request,
)
from app.services.audit_hash_chain import write_chained_audit_log

router = APIRouter(prefix="/api/approvals", tags=["enterprise_approvals"])


class ApprovalCreateIn(BaseModel):
    entity_type: str
    entity_id: str
    action: str
    payload: Dict[str, Any] = {}


class ApprovalResolveIn(BaseModel):
    note: Optional[str] = None


@router.get("")
async def get_approvals(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
):
    """List approval requests for user's org."""
    org_id = user["organization_id"]
    items = await list_approvals(
        organization_id=org_id,
        status=status,
        limit=limit,
    )
    return {"items": items, "count": len(items)}


@router.post("")
async def create_approval(
    payload: ApprovalCreateIn,
    user=Depends(get_current_user),
):
    """Create a new approval request."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", "")

    result = await create_approval_request(
        tenant_id=tenant_id,
        organization_id=org_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        action=payload.action,
        payload=payload.payload,
        requested_by=user.get("email", ""),
    )
    return result


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: str,
    payload: ApprovalResolveIn = ApprovalResolveIn(),
    user=Depends(require_roles(["super_admin", "admin"])),
    request: Request = None,
):
    """Approve a pending request. Admin only."""
    # Check current state first
    existing = await get_approval(approval_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if existing.get("status") != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve: current status is '{existing.get('status')}'",
        )

    # Verify org isolation
    if existing.get("organization_id") != user["organization_id"]:
        raise HTTPException(status_code=403, detail="Cross-tenant access forbidden")

    result = await approve_request(
        approval_id=approval_id,
        approved_by=user.get("email", ""),
        note=payload.note,
    )
    if not result:
        raise HTTPException(status_code=409, detail="Already resolved or not found")

    # Write audit log
    try:
        db = await get_db()
        await write_chained_audit_log(
            db,
            organization_id=user["organization_id"],
            tenant_id=existing.get("tenant_id", ""),
            actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
            action="APPROVAL_APPROVED",
            target_type="approval_request",
            target_id=approval_id,
            after={"status": "approved", "approved_by": user.get("email")},
            meta={"entity_type": existing.get("entity_type"), "entity_id": existing.get("entity_id")},
        )
    except Exception:
        pass

    return result


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: str,
    payload: ApprovalResolveIn = ApprovalResolveIn(),
    user=Depends(require_roles(["super_admin", "admin"])),
    request: Request = None,
):
    """Reject a pending request. Admin only."""
    existing = await get_approval(approval_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if existing.get("status") != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject: current status is '{existing.get('status')}'",
        )

    if existing.get("organization_id") != user["organization_id"]:
        raise HTTPException(status_code=403, detail="Cross-tenant access forbidden")

    result = await reject_request(
        approval_id=approval_id,
        rejected_by=user.get("email", ""),
        note=payload.note,
    )
    if not result:
        raise HTTPException(status_code=409, detail="Already resolved or not found")

    # Write audit log
    try:
        db = await get_db()
        await write_chained_audit_log(
            db,
            organization_id=user["organization_id"],
            tenant_id=existing.get("tenant_id", ""),
            actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
            action="APPROVAL_REJECTED",
            target_type="approval_request",
            target_id=approval_id,
            after={"status": "rejected", "rejected_by": user.get("email")},
            meta={"entity_type": existing.get("entity_type"), "entity_id": existing.get("entity_id")},
        )
    except Exception:
        pass

    return result
