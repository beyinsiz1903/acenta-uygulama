from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.services.ops_cases import list_cases, get_case, close_case


router = APIRouter(prefix="/api/ops/guest-cases", tags=["ops_guest_cases"])


OpsUserDep = Depends(require_roles(["admin", "ops", "super_admin"]))


class OpsCaseListResponse(BaseModel):
  
    class Config:
        arbitrary_types_allowed = True


class OpsCaseCloseBody(BaseModel):
    note: Optional[str] = None


@router.get("/")
async def list_ops_cases(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    return await list_cases(
        db,
        organization_id=str(org_id),
        status=status,
        type=type,
        source=source,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.get("/{case_id}")
async def get_ops_case(
    case_id: str,
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    doc = await get_case(db, organization_id=str(org_id), case_id=case_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Ops case not found")

    return doc


@router.post("/{case_id}/close")
async def close_ops_case(
    case_id: str,
    payload: OpsCaseCloseBody,
    request: Request,
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    request_context = {"ip": client_ip, "user_agent": user_agent}

    updated = await close_case(
        db,
        organization_id=str(org_id),
        case_id=case_id,
        actor=user,
        note=payload.note,
        request_context=request_context,
    )

    return {"ok": True, "case_id": updated.get("case_id", case_id), "status": updated.get("status")}
