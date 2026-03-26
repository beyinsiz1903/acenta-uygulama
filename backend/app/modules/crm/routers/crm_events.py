from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth import require_roles
from app.db import get_db
from app.services.crm_events import list_crm_events


router = APIRouter(prefix="/api/crm/events", tags=["crm-events"])


class CrmEventOut(BaseModel):
    id: str
    organization_id: str
    entity_type: str
    entity_id: str
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    actor_user_id: Optional[str] = None
    actor_roles: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    created_at: datetime


class CrmEventListResponse(BaseModel):
    items: List[CrmEventOut]
    total: int
    page: int
    page_size: int


@router.get("", response_model=CrmEventListResponse)
async def http_list_crm_events(
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    from_dt: Optional[datetime] = Query(default=None, alias="from"),
    to_dt: Optional[datetime] = Query(default=None, alias="to"),
    page: int = 1,
    page_size: int = 50,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["admin", "super_admin"])),
):
    """List CRM events for audit / debugging.

    - Auth: admin | super_admin
    - Filters: entity_type, entity_id, action, date range (from/to)
    - Sort: created_at desc
    """

    org_id = current_user.get("organization_id")

    items, total = await list_crm_events(
        db,
        org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        from_dt=from_dt,
        to_dt=to_dt,
        page=page,
        page_size=page_size,
    )

    return {"items": items, "total": total, "page": page, "page_size": page_size}
