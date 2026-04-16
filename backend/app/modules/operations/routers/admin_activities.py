from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.security.module_guard import require_org_module

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/activities",
    tags=["admin-activities"],
    dependencies=[require_org_module("activities")],
)

AdminDep = Depends(require_roles(["super_admin", "admin"]))


class ActivityCreate(BaseModel):
    name: str = Field(..., min_length=1)
    activity_type: str = Field(..., description="tour | excursion | experience | transfer_activity | water_sport | adventure")
    destination: str = ""
    city: str = ""
    description: str = ""
    duration_hours: float = 0
    capacity: int = 20
    min_participants: int = 1
    price_per_person: float = 0.0
    child_price: float = 0.0
    currency: str = "TRY"
    includes: List[str] = []
    excludes: List[str] = []
    requirements: List[str] = []
    meeting_point: str = ""
    meeting_time: str = ""
    languages: List[str] = ["tr"]
    images: List[str] = []
    guide_required: bool = False
    vehicle_required: bool = False
    supplier_id: str = ""
    supplier_name: str = ""
    status: str = "active"


class ActivityUpdate(BaseModel):
    name: Optional[str] = None
    activity_type: Optional[str] = None
    destination: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    duration_hours: Optional[float] = None
    capacity: Optional[int] = None
    min_participants: Optional[int] = None
    price_per_person: Optional[float] = None
    child_price: Optional[float] = None
    currency: Optional[str] = None
    includes: Optional[List[str]] = None
    excludes: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    meeting_point: Optional[str] = None
    meeting_time: Optional[str] = None
    languages: Optional[List[str]] = None
    images: Optional[List[str]] = None
    guide_required: Optional[bool] = None
    vehicle_required: Optional[bool] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    status: Optional[str] = None


class ActivitySession(BaseModel):
    date: str
    time: str = ""
    guide_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    max_participants: Optional[int] = None
    notes: str = ""


class SessionParticipant(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    booking_id: Optional[str] = None
    pax_count: int = 1
    notes: str = ""


ALLOWED_STATUSES = ["active", "inactive", "seasonal", "draft"]
ALLOWED_TYPES = ["tour", "excursion", "experience", "transfer_activity", "water_sport", "adventure"]


async def _audit(db, org_id: str, user: dict, action: str, target_id: str, meta: dict | None = None):
    try:
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "user_id": user.get("user_id", ""),
            "user_email": user.get("email", ""),
            "action": action,
            "module": "activities",
            "target_id": target_id,
            "meta": meta or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        logger.exception("Activity audit log failed")


@router.get("")
async def list_activities(
    search: str = Query("", description="İsim/destinasyon arama"),
    activity_type: str = Query("", description="Tür filtresi"),
    status: str = Query("", description="Durum filtresi"),
    city: str = Query("", description="Şehir filtresi"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user: dict = AdminDep,
):
    org_id = user["organization_id"]
    query: Dict[str, Any] = {"organization_id": org_id}
    if activity_type:
        query["activity_type"] = activity_type
    if status:
        query["status"] = status
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"destination": {"$regex": search, "$options": "i"}},
        ]
    total = await db.activities.count_documents(query)
    items = await db.activities.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"items": items, "total": total}


@router.post("", status_code=201)
async def create_activity(body: ActivityCreate, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    if body.activity_type not in ALLOWED_TYPES:
        raise AppError(400, "invalid_type", f"Geçersiz aktivite türü. İzin verilenler: {', '.join(ALLOWED_TYPES)}")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        **body.model_dump(),
        "sessions": [],
        "created_by": user.get("user_id", ""),
        "created_at": now,
        "updated_at": now,
    }
    await db.activities.insert_one(doc)
    await _audit(db, org_id, user, "activity_created", doc["id"], {"name": body.name, "type": body.activity_type})
    doc.pop("_id", None)
    return doc


@router.get("/{activity_id}")
async def get_activity(activity_id: str, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    doc = await db.activities.find_one({"organization_id": org_id, "id": activity_id}, {"_id": 0})
    if not doc:
        raise AppError(404, "activity_not_found", "Aktivite bulunamadı.")
    return doc


@router.patch("/{activity_id}")
async def update_activity(activity_id: str, body: ActivityUpdate, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        raise AppError(400, "no_fields", "Güncellenecek alan belirtilmedi.")
    if "status" in updates and updates["status"] not in ALLOWED_STATUSES:
        raise AppError(400, "invalid_status", f"Geçersiz durum. İzin verilenler: {', '.join(ALLOWED_STATUSES)}")
    if "activity_type" in updates and updates["activity_type"] not in ALLOWED_TYPES:
        raise AppError(400, "invalid_type", f"Geçersiz aktivite türü. İzin verilenler: {', '.join(ALLOWED_TYPES)}")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.activities.update_one({"organization_id": org_id, "id": activity_id}, {"$set": updates})
    if result.matched_count == 0:
        raise AppError(404, "activity_not_found", "Aktivite bulunamadı.")
    await _audit(db, org_id, user, "activity_updated", activity_id, {"fields": list(updates.keys())})
    return await db.activities.find_one({"organization_id": org_id, "id": activity_id}, {"_id": 0})


@router.delete("/{activity_id}", status_code=204)
async def delete_activity(activity_id: str, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    result = await db.activities.delete_one({"organization_id": org_id, "id": activity_id})
    if result.deleted_count == 0:
        raise AppError(404, "activity_not_found", "Aktivite bulunamadı.")
    await _audit(db, org_id, user, "activity_deleted", activity_id)


@router.post("/{activity_id}/sessions", status_code=201)
async def create_session(activity_id: str, body: ActivitySession, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    activity = await db.activities.find_one({"organization_id": org_id, "id": activity_id})
    if not activity:
        raise AppError(404, "activity_not_found", "Aktivite bulunamadı.")

    session = {
        "id": str(uuid.uuid4()),
        **body.model_dump(),
        "participants": [],
        "current_pax": 0,
        "max_participants": body.max_participants or activity.get("capacity", 20),
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.activities.update_one(
        {"organization_id": org_id, "id": activity_id},
        {"$push": {"sessions": session}},
    )
    await _audit(db, org_id, user, "activity_session_created", activity_id, {"session_id": session["id"], "date": body.date})
    return session


@router.get("/{activity_id}/sessions")
async def list_sessions(activity_id: str, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    doc = await db.activities.find_one({"organization_id": org_id, "id": activity_id}, {"_id": 0, "sessions": 1})
    if not doc:
        raise AppError(404, "activity_not_found", "Aktivite bulunamadı.")
    return {"sessions": doc.get("sessions", [])}


@router.post("/{activity_id}/sessions/{session_id}/participants", status_code=201)
async def add_participant(
    activity_id: str,
    session_id: str,
    body: SessionParticipant,
    db=Depends(get_db),
    user: dict = AdminDep,
):
    org_id = user["organization_id"]
    activity = await db.activities.find_one({"organization_id": org_id, "id": activity_id})
    if not activity:
        raise AppError(404, "activity_not_found", "Aktivite bulunamadı.")

    target_session = None
    for s in activity.get("sessions", []):
        if s["id"] == session_id:
            target_session = s
            break
    if not target_session:
        raise AppError(404, "session_not_found", "Seans bulunamadı.")

    max_pax = target_session.get("max_participants", 20)
    current_pax = target_session.get("current_pax", 0)
    if current_pax + body.pax_count > max_pax:
        raise AppError(400, "session_full", f"Seans kapasitesi dolu. Mevcut: {current_pax}/{max_pax}")

    participant = {
        "id": str(uuid.uuid4()),
        **body.model_dump(),
        "added_at": datetime.now(timezone.utc).isoformat(),
    }

    result = await db.activities.update_one(
        {
            "organization_id": org_id,
            "id": activity_id,
            "sessions.id": session_id,
            "sessions.current_pax": {"$lte": max_pax - body.pax_count},
        },
        {
            "$push": {"sessions.$.participants": participant},
            "$inc": {"sessions.$.current_pax": body.pax_count},
        },
    )
    if result.modified_count == 0:
        raise AppError(409, "capacity_exceeded", "Kapasite aşıldı veya seans bulunamadı.")

    await _audit(db, org_id, user, "activity_participant_added", activity_id, {
        "session_id": session_id,
        "participant_name": body.name,
        "pax_count": body.pax_count,
    })
    return participant


@router.delete("/{activity_id}/sessions/{session_id}/participants/{participant_id}")
async def remove_participant(
    activity_id: str,
    session_id: str,
    participant_id: str,
    db=Depends(get_db),
    user: dict = AdminDep,
):
    org_id = user["organization_id"]
    activity = await db.activities.find_one({"organization_id": org_id, "id": activity_id})
    if not activity:
        raise AppError(404, "activity_not_found", "Aktivite bulunamadı.")

    pax_count = 0
    found = False
    for s in activity.get("sessions", []):
        if s["id"] == session_id:
            for p in s.get("participants", []):
                if p["id"] == participant_id:
                    pax_count = p.get("pax_count", 1)
                    found = True
                    break
            break

    if not found:
        raise AppError(404, "participant_not_found", "Katılımcı bulunamadı.")

    result = await db.activities.update_one(
        {"organization_id": org_id, "id": activity_id, "sessions.id": session_id},
        {
            "$pull": {"sessions.$.participants": {"id": participant_id}},
            "$inc": {"sessions.$.current_pax": -pax_count},
        },
    )
    if result.modified_count == 0:
        raise AppError(404, "participant_not_found", "Katılımcı silinemedi.")
    await _audit(db, org_id, user, "activity_participant_removed", activity_id, {
        "session_id": session_id,
        "participant_id": participant_id,
    })
    return {"ok": True}


@router.patch("/{activity_id}/sessions/{session_id}/status")
async def update_session_status(
    activity_id: str,
    session_id: str,
    status: str = Query(...),
    db=Depends(get_db),
    user: dict = AdminDep,
):
    allowed = ["open", "closed", "cancelled", "completed"]
    if status not in allowed:
        raise AppError(400, "invalid_status", f"Geçersiz durum. İzin verilenler: {', '.join(allowed)}")

    org_id = user["organization_id"]
    result = await db.activities.update_one(
        {"organization_id": org_id, "id": activity_id, "sessions.id": session_id},
        {"$set": {"sessions.$.status": status}},
    )
    if result.matched_count == 0:
        raise AppError(404, "session_not_found", "Seans bulunamadı.")
    await _audit(db, org_id, user, "activity_session_status_changed", activity_id, {"session_id": session_id, "status": status})
    return {"ok": True, "status": status}
