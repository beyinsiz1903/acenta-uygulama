from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/crm", tags=["crm-actions"])


# ---------- Helpers ----------


def _require_scope_agency(scope: str) -> None:
  scope_val = (scope or "").strip().lower()
  if scope_val != "agency":
      raise HTTPException(status_code=422, detail="SCOPE_NOT_SUPPORTED")


async def _assert_linked_hotel(db, user: dict, hotel_id: str) -> None:
    """Ensure agency user is linked to given hotel via agency_hotel_links."""
    organization_id = str(user.get("organization_id"))
    agency_id = user.get("agency_id")
    if not agency_id:
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    q = {
        "organization_id": organization_id,
        "agency_id": agency_id,
        "hotel_id": hotel_id,
        "active": True,
    }
    link = await db.agency_hotel_links.find_one(q, {"_id": 1})
    if not link:
        raise HTTPException(status_code=403, detail="FORBIDDEN")


async def _assert_own_task(db, user: dict, task_id: str) -> dict:
    organization_id = str(user.get("organization_id"))
    agency_id = user.get("agency_id")
    if not agency_id:
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    q = {
        "_id": task_id,
        "organization_id": organization_id,
        "agency_id": agency_id,
    }
    task = await db.hotel_crm_tasks.find_one(q)
    if not task:
        raise HTTPException(status_code=404, detail="TASK_NOT_FOUND")
    return task


# ---------- Models ----------


CallOutcome = Literal["reached", "no_answer", "callback", "not_interested", "interested"]


class CrmNoteCreateIn(BaseModel):
    scope: Literal["agency"] = "agency"
    hotel_id: str = Field(..., min_length=1)
    type: Literal["note", "call"]
    subject: str = Field(..., min_length=1, max_length=200)
    body: Optional[str] = Field(default=None, max_length=5000)
    call_outcome: Optional[CallOutcome] = None


class CrmTaskCreateIn(BaseModel):
    scope: Literal["agency"] = "agency"
    hotel_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    due_date: str = Field(..., min_length=10, max_length=10)  # YYYY-MM-DD
    assignee_user_id: Optional[str] = None


# ---------- Endpoints ----------


@router.post(
    "/notes",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "super_admin"]))],
)
async def create_crm_note(payload: CrmNoteCreateIn, user=Depends(get_current_user), db=Depends(get_db)):
    _require_scope_agency(payload.scope)

    role = user.get("role")
    roles = set(user.get("roles") or [])
    if role in {"hotel_admin", "hotel_staff"} or {"hotel_admin", "hotel_staff"} & roles:
        # v1.1: hotel roles cannot write CRM notes via this endpoint
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    await _assert_linked_hotel(db, user, payload.hotel_id)

    # Validate call_outcome usage
    if payload.type == "call" and not payload.call_outcome:
        raise HTTPException(status_code=422, detail="CALL_OUTCOME_REQUIRED")
    if payload.type == "note" and payload.call_outcome:
        payload.call_outcome = None

    now = now_utc()

    doc = {
        "organization_id": user["organization_id"],
        "agency_id": user.get("agency_id"),
        "hotel_id": payload.hotel_id,
        "type": payload.type,
        "subject": payload.subject.strip(),
        "body": (payload.body or None),
        "call_outcome": payload.call_outcome,
        "created_at": now,
        "created_by_user_id": str(user.get("id") or user.get("_id") or ""),
        "created_by_email": user.get("email"),
    }

    res = await db.hotel_crm_notes.insert_one(doc)
    if "_id" not in doc:
        doc["_id"] = res.inserted_id

    return {"ok": True, "note": serialize_doc(doc)}


@router.post(
    "/tasks",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "super_admin"]))],
)
async def create_crm_task(payload: CrmTaskCreateIn, user=Depends(get_current_user), db=Depends(get_db)):
    _require_scope_agency(payload.scope)

    role = user.get("role")
    roles = set(user.get("roles") or [])
    if role in {"hotel_admin", "hotel_staff"} or {"hotel_admin", "hotel_staff"} & roles:
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    await _assert_linked_hotel(db, user, payload.hotel_id)

    # Parse due_date safely
    try:
        _ = date.fromisoformat(payload.due_date)
    except Exception:
        raise HTTPException(status_code=422, detail="INVALID_DUE_DATE")

    now = now_utc()

    assignee_user_id = payload.assignee_user_id
    if "agency_agent" in roles and not assignee_user_id:
        assignee_user_id = str(user.get("id"))

    doc = {
        "organization_id": user["organization_id"],
        "agency_id": user.get("agency_id"),
        "hotel_id": payload.hotel_id,
        "title": payload.title.strip(),
        "status": "open",
        "due_date": payload.due_date,  # keep as string; follow-ups normalizes
        "assignee_user_id": assignee_user_id,
        "created_at": now,
        "updated_at": now,
        "created_by_user_id": str(user.get("id") or user.get("_id") or ""),
        "created_by_email": user.get("email"),
    }

    res = await db.hotel_crm_tasks.insert_one(doc)
    if "_id" not in doc:
        doc["_id"] = res.inserted_id

    return {"ok": True, "task": serialize_doc(doc)}


@router.post(
    "/tasks/{task_id}/complete",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "super_admin"]))],
)
async def complete_crm_task(task_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    roles = set(user.get("roles") or [])
    if {"hotel_admin", "hotel_staff"} & roles:
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    task = await _assert_own_task(db, user, task_id)

    if task.get("status") == "done":
        # idempotent
        return {"ok": True, "task": serialize_doc(task)}

    now = now_utc()
    await db.hotel_crm_tasks.update_one(
        {"_id": task_id, "organization_id": user["organization_id"], "agency_id": user.get("agency_id")},
        {"$set": {"status": "done", "completed_at": now, "updated_at": now}},
    )

    updated = await db.hotel_crm_tasks.find_one({"_id": task_id})
    return {"ok": True, "task": serialize_doc(updated)}
