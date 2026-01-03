from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.crm_access import assert_hotel_access, assert_agency_access
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/crm", tags=["crm-hotel-tasks"])


class HotelTaskCreateIn(BaseModel):
    hotel_id: str
    agency_id: str
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=4000)
    due_date: Optional[datetime] = None
    assignee_user_id: Optional[str] = None


class HotelTaskStatusUpdateIn(BaseModel):
    status: str = Field(..., pattern="^(open|done)$")


@router.get(
    "/hotel-tasks",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "hotel_admin", "hotel_staff", "super_admin"]))],
)
async def list_hotel_tasks(
    hotel_id: str,
    agency_id: Optional[str] = None,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    user=Depends(get_current_user),
):
    db = await get_db()
    org_id = user["organization_id"]
    roles = set(user.get("roles") or [])

    # Ownership / visibility
    if {"agency_admin", "agency_agent"} & roles:
        if agency_id and str(agency_id) != str(user.get("agency_id")):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
        agency_id = user.get("agency_id")
    if {"hotel_admin", "hotel_staff"} & roles:
        assert_hotel_access(hotel_id, user)

    q: dict[str, Any] = {"organization_id": org_id, "hotel_id": hotel_id}
    if agency_id:
        q["agency_id"] = agency_id
    if status in ("open", "done"):
        q["status"] = status

    if assignee == "me":
        q["assignee_user_id"] = user.get("id")
    elif assignee:
        q["assignee_user_id"] = assignee

    docs = await db.hotel_crm_tasks.find(q).sort("due_date", 1).to_list(500)
    return [serialize_doc(d) for d in docs]


@router.post(
    "/hotel-tasks",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "super_admin"]))],
)
async def create_hotel_task(payload: HotelTaskCreateIn, user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    roles = set(user.get("roles") or [])

    # Agency-only creation
    assert_agency_access(payload.agency_id, user)

    # Hotel access must exist via link
    link = await db.agency_hotel_links.find_one(
        {
            "organization_id": org_id,
            "agency_id": payload.agency_id,
            "hotel_id": payload.hotel_id,
            "active": True,
        }
    )
    if not link:
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    now = now_utc()

    assignee_user_id = payload.assignee_user_id
    if "agency_agent" in roles and not assignee_user_id:
        assignee_user_id = user.get("id")

    doc = {
        "organization_id": org_id,
        "hotel_id": payload.hotel_id,
        "agency_id": payload.agency_id,
        "title": payload.title,
        "description": payload.description,
        "due_date": payload.due_date,
        "status": "open",
        "assignee_user_id": assignee_user_id,
        "created_at": now,
        "updated_at": now,
        "created_by_user_id": user.get("id"),
    }

    res = await db.hotel_crm_tasks.insert_one(doc)
    saved = await db.hotel_crm_tasks.find_one({"_id": res.inserted_id})
    return serialize_doc(saved)


@router.patch(
    "/hotel-tasks/{task_id}/status",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "super_admin"]))],
)
async def update_hotel_task_status(task_id: str, payload: HotelTaskStatusUpdateIn, user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    roles = set(user.get("roles") or [])

    task = await db.hotel_crm_tasks.find_one({"_id": task_id, "organization_id": org_id})
    if not task:
        raise HTTPException(status_code=404, detail="TASK_NOT_FOUND")

    # Agency ownership: agent can only update own tasks; admin can update within agency
    if "agency_agent" in roles:
        if str(task.get("assignee_user_id")) != str(user.get("id")):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
    if "agency_admin" in roles:
        if str(task.get("agency_id")) != str(user.get("agency_id")):
            raise HTTPException(status_code=403, detail="FORBIDDEN")

    now = now_utc()

    update_doc: dict[str, Any] = {
        "status": payload.status,
        "updated_at": now,
    }
    if payload.status == "done":
        update_doc["completed_at"] = now

    await db.hotel_crm_tasks.update_one({"_id": task_id}, {"$set": update_doc})

    updated = await db.hotel_crm_tasks.find_one({"_id": task_id})
    return serialize_doc(updated)
