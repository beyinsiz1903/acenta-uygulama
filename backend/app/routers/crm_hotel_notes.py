from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.crm_access import assert_hotel_access, assert_agency_access
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/crm", tags=["crm-hotel-notes"])


class HotelNoteCreateIn(BaseModel):
    hotel_id: str = Field(...)
    agency_id: str = Field(...)
    type: str = Field("note", pattern="^(note|call)$")
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field("", max_length=4000)
    call_outcome: Optional[str] = Field(None, max_length=100)


class HotelNoteOut(BaseModel):
    id: str
    hotel_id: str
    agency_id: str
    type: str
    subject: str
    body: str
    call_outcome: Optional[str]
    created_at: datetime
    created_by_user_id: str
    created_by_role: Optional[str]


@router.get(
    "/hotel-notes",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "hotel_admin", "hotel_staff", "super_admin"]))],
)
async def list_hotel_notes(
    hotel_id: str,
    agency_id: Optional[str] = None,
    days: int = 7,
    mine: int = 0,
    user=Depends(get_current_user),
):
    """List CRM notes between an agency and hotel for recent period.

    Rules:
      - agency roles: agency_id must equal user.agency_id
      - hotel roles: hotel_id must equal user.hotel_id
      - super_admin: org-wide within given params
    """
    db = await get_db()

    org_id = user["organization_id"]
    roles = set(user.get("roles") or [])

    # RBAC + ownership
    if {"agency_admin", "agency_agent"} & roles:
        if not agency_id or str(agency_id) != str(user.get("agency_id")):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
    if {"hotel_admin", "hotel_staff"} & roles:
        assert_hotel_access(hotel_id, user)

    # Build query
    q: dict[str, Any] = {"organization_id": org_id, "hotel_id": hotel_id}
    if agency_id:
        q["agency_id"] = agency_id

    # Time filter
    if days and days > 0:
        cutoff = now_utc() - timedelta(days=days)
        q["created_at"] = {"$gte": cutoff}

    # mine filter
    if mine:
        q["created_by_user_id"] = user.get("id")

    docs = await db.hotel_crm_notes.find(q).sort("created_at", -1).to_list(500)

    return [serialize_doc(d) for d in docs]


@router.post(
    "/hotel-notes",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "hotel_admin", "hotel_staff", "super_admin"]))],
)
async def create_hotel_note(payload: HotelNoteCreateIn, user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    roles = set(user.get("roles") or [])

    # Ownership checks
    if {"agency_admin", "agency_agent"} & roles:
        assert_agency_access(payload.agency_id, user)
    if {"hotel_admin", "hotel_staff"} & roles:
        assert_hotel_access(payload.hotel_id, user)

    now = now_utc()

    doc = {
        "_id": str(now.timestamp()).replace(".", ""),  # simple unique id
        "organization_id": org_id,
        "hotel_id": payload.hotel_id,
        "agency_id": payload.agency_id,
        "type": payload.type,
        "subject": payload.subject,
        "body": payload.body,
        "call_outcome": payload.call_outcome,
        "created_at": now,
        "created_by_user_id": user.get("id"),
        "created_by_role": (next(iter(roles)) if roles else None),
    }

    await db.hotel_crm_notes.insert_one(doc)

    return serialize_doc(doc)
