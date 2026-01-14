from __future__ import annotations

from datetime import datetime
from typing import List, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, constr

from app.auth import require_roles
from app.db import get_db
from app.services.crm_activities import create_activity, list_activities


router = APIRouter(prefix="/api/crm/activities", tags=["crm-activities"])


class ActivityOut(BaseModel):
    id: str
    organization_id: str
    created_by_user_id: str
    type: Literal["note", "call", "email", "meeting"]
    body: str
    related_type: Literal["customer", "deal", "booking"]
    related_id: str
    created_at: datetime


class ActivityCreate(BaseModel):
    type: Literal["note", "call", "email", "meeting"]
    body: constr(strip_whitespace=True, min_length=1)
    related_type: Literal["customer", "deal", "booking"]
    related_id: constr(strip_whitespace=True, min_length=1)


class ActivityListResponse(BaseModel):
    items: List[ActivityOut]
    total: int
    page: int
    page_size: int


@router.get("", response_model=ActivityListResponse)
async def http_list_activities(
    relatedType: Literal["customer", "deal", "booking"] = Query(...),
    relatedId: str = Query(..., min_length=1),
    page: int = 1,
    page_size: int = 50,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")

    items, total = await list_activities(
        db,
        org_id,
        related_type=relatedType,
        related_id=relatedId,
        page=page,
        page_size=page_size,
    )

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=ActivityOut)
async def http_create_activity(
    body: ActivityCreate,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")
    user_id = current_user.get("id")

    act = await create_activity(db, org_id, user_id, body.model_dump())

    # Fire-and-forget CRM event (activity created)
    from app.services.crm_events import log_crm_event

    await log_crm_event(
        db,
        org_id,
        entity_type="activity",
        entity_id=act["id"],
        action="created",
        payload={"fields": list(body.model_fields_set)},
        actor={"id": user_id, "roles": current_user.get("roles") or []},
        source="api",
    )

    return act
