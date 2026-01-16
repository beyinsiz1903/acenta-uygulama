from __future__ import annotations

from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.services.ops_cases import list_cases, get_case, close_case, create_case, update_case
from app.schemas_ops_cases import OpsCaseCreate, OpsCaseUpdate, OpsCaseOut


router = APIRouter(prefix="/api/ops-cases", tags=["ops_cases"])


OpsUserDep = Depends(require_roles(["admin", "ops", "super_admin"]))


class OpsCaseListResponse(BaseModel):
  
    class Config:
        arbitrary_types_allowed = True


class OpsCaseCloseBody(BaseModel):
    note: Optional[str] = None


@router.get("/")
async def list_ops_cases(
    status: Optional[str] = Query("open"),
    type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    booking_id: Optional[str] = Query(None),
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
        booking_id=booking_id,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.get("/counters")
async def ops_cases_counters(
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Return simple counters for ops_cases by status for current organization.

    - open
    - waiting
    - in_progress
    """
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    pipeline = [
        {"$match": {"organization_id": str(org_id), "status": {"$in": ["open", "waiting", "in_progress"]}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]

    results = await db.ops_cases.aggregate(pipeline).to_list(length=10)

    counters = {"open": 0, "waiting": 0, "in_progress": 0}
    for row in results:
        status = row.get("_id")
        if status in counters:
            counters[status] = int(row.get("count") or 0)

    return counters



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


@router.post("/", response_model=OpsCaseOut)
async def create_ops_case(
    payload: OpsCaseCreate,
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    doc = await create_case(
        db,
        organization_id=str(org_id),
        booking_id=payload.booking_id,
        type=payload.type,
        source=payload.source,
        status=payload.status,
        waiting_on=payload.waiting_on,
        note=payload.note,
    )

    return OpsCaseOut(**doc)


@router.patch("/{case_id}", response_model=OpsCaseOut)
async def patch_ops_case(
    case_id: str,
    payload: OpsCaseUpdate,
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    data = payload.model_dump(exclude_unset=True)

    updated = await update_case(
        db,
        organization_id=str(org_id),
        case_id=case_id,
        status=data.get("status"),
        waiting_on=data.get("waiting_on"),
        note=data.get("note"),
    )

    return OpsCaseOut(**updated)
