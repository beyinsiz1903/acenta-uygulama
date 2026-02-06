from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth import require_roles
from app.db import get_db
from app.schemas_crm import DealCreate, DealOut, DealPatch
from app.services.crm_deals import create_deal, get_deal, link_deal_booking, list_deals, patch_deal
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crm/deals", tags=["crm-deals"])

VALID_STAGES = ["lead", "contacted", "proposal", "won", "lost", "new", "qualified", "quoted"]


class DealListResponse(BaseModel):
    items: List[DealOut]
    total: int
    page: int
    page_size: int


@router.get("", response_model=DealListResponse)
async def http_list_deals(
    status: Optional[str] = Query(default="open"),
    stage: Optional[str] = None,
    owner: Optional[str] = None,
    customer_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")

    items, total = await list_deals(
        db,
        org_id,
        status=status,
        stage=stage,
        owner_user_id=owner,
        customer_id=customer_id,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=DealOut)
async def http_create_deal(
    body: DealCreate,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")
    user_id = current_user.get("id")

    deal = await create_deal(db, org_id, user_id, body.model_dump())

    # Fire-and-forget CRM event (deal created)
    from app.services.crm_events import log_crm_event

    await log_crm_event(
        db,
        org_id,
        entity_type="deal",
        entity_id=deal["id"],
        action="created",
        payload={"fields": list(body.model_fields_set)},
        actor={"id": user_id, "roles": current_user.get("roles") or []},
        source="api",
    )

    return deal


@router.patch("/{deal_id}", response_model=DealOut)
async def http_patch_deal(
    deal_id: str,
    body: DealPatch,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")

    patch_dict = body.model_dump(exclude_unset=True)
    if not any(v is not None for v in patch_dict.values()):
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = await patch_deal(db, org_id, deal_id, patch_dict)
    if not updated:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Fire-and-forget CRM event (deal updated)
    from app.services.crm_events import log_crm_event

    await log_crm_event(
        db,
        org_id,
        entity_type="deal",
        entity_id=deal_id,
        action="updated",
        payload={"changed_fields": list(patch_dict.keys())},
        actor={"id": current_user.get("id"), "roles": current_user.get("roles") or []},
        source="api",
    )

    return updated


class LinkBookingIn(BaseModel):
    booking_id: str


@router.post("/{deal_id}/link-booking", response_model=DealOut)
async def http_link_booking(
    deal_id: str,
    body: LinkBookingIn,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")

    updated = await link_deal_booking(db, org_id, deal_id, body.booking_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Deal not found")

    return updated
