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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/guides", tags=["admin-guides"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


class GuideCreate(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    languages: List[str] = []
    specialties: List[str] = []
    license_number: str = ""
    license_expiry: str = ""
    daily_rate: float = 0.0
    currency: str = "TRY"
    status: str = "active"
    notes: str = ""
    photo_url: str = ""


class GuidePatch(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    languages: Optional[List[str]] = None
    specialties: Optional[List[str]] = None
    license_number: Optional[str] = None
    license_expiry: Optional[str] = None
    daily_rate: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None


def _doc_to_dict(doc: dict) -> dict:
    return {
        "id": doc.get("id") or str(doc.get("_id")),
        "name": doc.get("name", ""),
        "phone": doc.get("phone", ""),
        "email": doc.get("email", ""),
        "languages": doc.get("languages", []),
        "specialties": doc.get("specialties", []),
        "license_number": doc.get("license_number", ""),
        "license_expiry": doc.get("license_expiry", ""),
        "daily_rate": float(doc.get("daily_rate", 0)),
        "currency": doc.get("currency", "TRY"),
        "status": doc.get("status", "active"),
        "notes": doc.get("notes", ""),
        "photo_url": doc.get("photo_url", ""),
        "rating": doc.get("rating", 0),
        "total_tours": doc.get("total_tours", 0),
        "organization_id": doc.get("organization_id"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


async def _audit(db, org_id: str, user: dict, action: str, target_id: str, meta: dict = None):
    try:
        from app.services.audit import write_audit_log
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles") or []},
            request=None,
            action=action,
            target_type="guide",
            target_id=target_id,
            before=None,
            after=None,
            meta=meta or {},
        )
    except Exception:
        logger.exception("Audit log failed for %s: %s", action, target_id)


@router.get("", dependencies=[AdminDep])
async def list_guides(
    status: Optional[str] = None,
    language: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    filt: Dict[str, Any] = {"organization_id": org_id}
    if status:
        filt["status"] = status
    if language:
        filt["languages"] = language
    if search:
        filt["name"] = {"$regex": search, "$options": "i"}
    total = await db.guides.count_documents(filt)
    skip = (page - 1) * page_size
    cursor = db.guides.find(filt, {"_id": 0}).sort("name", 1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)
    return {"items": [_doc_to_dict(d) for d in docs], "total": total, "page": page, "page_size": page_size}


@router.get("/{guide_id}", dependencies=[AdminDep])
async def get_guide(guide_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.guides.find_one({"id": guide_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        raise AppError(404, "NOT_FOUND", "Rehber bulunamadi")
    return _doc_to_dict(doc)


@router.post("", dependencies=[AdminDep])
async def create_guide(body: GuideCreate, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        **body.model_dump(),
        "rating": 0,
        "total_tours": 0,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("id"),
    }
    await db.guides.insert_one(doc)
    result = _doc_to_dict(doc)
    await _audit(db, org_id, user, "GUIDE_CREATED", result["id"], {"name": body.name})
    return result


@router.patch("/{guide_id}", dependencies=[AdminDep])
async def patch_guide(guide_id: str, body: GuidePatch, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise AppError(400, "NO_CHANGES", "Guncelleme verisi yok")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.guides.update_one({"id": guide_id, "organization_id": org_id}, {"$set": updates})
    if result.matched_count == 0:
        raise AppError(404, "NOT_FOUND", "Rehber bulunamadi")
    doc = await db.guides.find_one({"id": guide_id, "organization_id": org_id}, {"_id": 0})
    await _audit(db, org_id, user, "GUIDE_UPDATED", guide_id, {"fields": list(updates.keys())})
    return _doc_to_dict(doc)


@router.delete("/{guide_id}", dependencies=[AdminDep])
async def delete_guide(guide_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    result = await db.guides.delete_one({"id": guide_id, "organization_id": org_id})
    if result.deleted_count == 0:
        raise AppError(404, "NOT_FOUND", "Rehber bulunamadi")
    await _audit(db, org_id, user, "GUIDE_DELETED", guide_id)
    return {"ok": True}


@router.get("/{guide_id}/calendar", dependencies=[AdminDep])
async def get_guide_calendar(
    guide_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    doc = await db.guides.find_one({"id": guide_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        raise AppError(404, "NOT_FOUND", "Rehber bulunamadi")

    filt: Dict[str, Any] = {"organization_id": org_id, "guide_id": guide_id}
    if start_date and end_date:
        filt["date"] = {"$gte": start_date, "$lte": end_date}
    cursor = db.transfers.find(filt, {"_id": 0}).sort("date", 1)
    assignments = await cursor.to_list(length=500)
    return {"guide": _doc_to_dict(doc), "assignments": assignments}


@router.post("/{guide_id}/rate", dependencies=[AdminDep])
async def rate_guide(guide_id: str, payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    rating = payload.get("rating", 0)
    if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
        raise AppError(400, "INVALID", "Puan 1-5 arasi olmali")
    now = datetime.now(timezone.utc).isoformat()
    result = await db.guides.update_one(
        {"id": guide_id, "organization_id": org_id},
        {"$set": {"rating": rating, "updated_at": now}},
    )
    if result.matched_count == 0:
        raise AppError(404, "NOT_FOUND", "Rehber bulunamadi")
    await _audit(db, org_id, user, "GUIDE_RATED", guide_id, {"rating": rating})
    return {"ok": True}
