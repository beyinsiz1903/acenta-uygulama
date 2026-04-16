from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.security.module_guard import require_org_module

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/villas",
    tags=["admin-villas"],
    dependencies=[require_org_module("villas")],
)

AdminDep = Depends(require_roles(["super_admin", "admin"]))


class VillaCreate(BaseModel):
    name: str = Field(..., min_length=1)
    location: str = ""
    city: str = ""
    district: str = ""
    address: str = ""
    description: str = ""
    capacity: int = 1
    bedrooms: int = 1
    bathrooms: int = 1
    pool: bool = False
    pool_type: str = ""
    area_sqm: float = 0
    features: List[str] = []
    images: List[str] = []
    price_per_night: float = 0.0
    currency: str = "TRY"
    min_stay_nights: int = 1
    owner_name: str = ""
    owner_phone: str = ""
    owner_email: str = ""
    commission_rate: float = 0.0
    ical_url: str = ""
    status: str = "active"


class VillaUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    pool: Optional[bool] = None
    pool_type: Optional[str] = None
    area_sqm: Optional[float] = None
    features: Optional[List[str]] = None
    images: Optional[List[str]] = None
    price_per_night: Optional[float] = None
    currency: Optional[str] = None
    min_stay_nights: Optional[int] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    commission_rate: Optional[float] = None
    ical_url: Optional[str] = None
    status: Optional[str] = None


class VillaBlockDate(BaseModel):
    start_date: str
    end_date: str
    reason: str = ""
    guest_name: str = ""
    booking_id: Optional[str] = None


class VillaPriceOverride(BaseModel):
    start_date: str
    end_date: str
    price_per_night: float
    label: str = ""


ALLOWED_STATUSES = ["active", "inactive", "maintenance", "seasonal"]


async def _audit(db, org_id: str, user: dict, action: str, target_id: str, meta: dict | None = None):
    try:
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "user_id": user.get("user_id", ""),
            "user_email": user.get("email", ""),
            "action": action,
            "module": "villas",
            "target_id": target_id,
            "meta": meta or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        logger.exception("Villa audit log failed")


@router.get("")
async def list_villas(
    search: str = Query("", description="İsim/konum arama"),
    status: str = Query("", description="Durum filtresi"),
    city: str = Query("", description="Şehir filtresi"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user: dict = AdminDep,
):
    org_id = user["organization_id"]
    query: Dict[str, Any] = {"organization_id": org_id}
    if status:
        query["status"] = status
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"location": {"$regex": search, "$options": "i"}},
            {"district": {"$regex": search, "$options": "i"}},
        ]
    total = await db.villas.count_documents(query)
    items = await db.villas.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"items": items, "total": total}


@router.post("", status_code=201)
async def create_villa(body: VillaCreate, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    existing = await db.villas.find_one({"organization_id": org_id, "name": body.name, "location": body.location})
    if existing:
        raise AppError(409, "villa_duplicate", "Bu isim ve konumda villa zaten mevcut.")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        **body.model_dump(),
        "blocked_dates": [],
        "price_overrides": [],
        "created_by": user.get("user_id", ""),
        "created_at": now,
        "updated_at": now,
    }
    await db.villas.insert_one(doc)
    await _audit(db, org_id, user, "villa_created", doc["id"], {"name": body.name})
    doc.pop("_id", None)
    return doc


@router.get("/{villa_id}")
async def get_villa(villa_id: str, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    doc = await db.villas.find_one({"organization_id": org_id, "id": villa_id}, {"_id": 0})
    if not doc:
        raise AppError(404, "villa_not_found", "Villa bulunamadı.")
    return doc


@router.patch("/{villa_id}")
async def update_villa(villa_id: str, body: VillaUpdate, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        raise AppError(400, "no_fields", "Güncellenecek alan belirtilmedi.")
    if "status" in updates and updates["status"] not in ALLOWED_STATUSES:
        raise AppError(400, "invalid_status", f"Geçersiz durum. İzin verilenler: {', '.join(ALLOWED_STATUSES)}")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.villas.update_one({"organization_id": org_id, "id": villa_id}, {"$set": updates})
    if result.matched_count == 0:
        raise AppError(404, "villa_not_found", "Villa bulunamadı.")
    await _audit(db, org_id, user, "villa_updated", villa_id, {"fields": list(updates.keys())})
    return await db.villas.find_one({"organization_id": org_id, "id": villa_id}, {"_id": 0})


@router.delete("/{villa_id}", status_code=204)
async def delete_villa(villa_id: str, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    result = await db.villas.delete_one({"organization_id": org_id, "id": villa_id})
    if result.deleted_count == 0:
        raise AppError(404, "villa_not_found", "Villa bulunamadı.")
    await _audit(db, org_id, user, "villa_deleted", villa_id)


@router.post("/{villa_id}/block-dates", status_code=201)
async def add_blocked_dates(villa_id: str, body: VillaBlockDate, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    block = {
        "id": str(uuid.uuid4()),
        "start_date": body.start_date,
        "end_date": body.end_date,
        "reason": body.reason,
        "guest_name": body.guest_name,
        "booking_id": body.booking_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.villas.update_one(
        {"organization_id": org_id, "id": villa_id},
        {"$push": {"blocked_dates": block}},
    )
    if result.matched_count == 0:
        raise AppError(404, "villa_not_found", "Villa bulunamadı.")
    await _audit(db, org_id, user, "villa_dates_blocked", villa_id, {"block_id": block["id"]})
    return block


@router.delete("/{villa_id}/block-dates/{block_id}")
async def remove_blocked_date(villa_id: str, block_id: str, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    result = await db.villas.update_one(
        {"organization_id": org_id, "id": villa_id},
        {"$pull": {"blocked_dates": {"id": block_id}}},
    )
    if result.matched_count == 0:
        raise AppError(404, "villa_not_found", "Villa bulunamadı.")
    await _audit(db, org_id, user, "villa_dates_unblocked", villa_id, {"block_id": block_id})
    return {"ok": True}


@router.post("/{villa_id}/price-overrides", status_code=201)
async def add_price_override(villa_id: str, body: VillaPriceOverride, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    override = {
        "id": str(uuid.uuid4()),
        **body.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.villas.update_one(
        {"organization_id": org_id, "id": villa_id},
        {"$push": {"price_overrides": override}},
    )
    if result.matched_count == 0:
        raise AppError(404, "villa_not_found", "Villa bulunamadı.")
    await _audit(db, org_id, user, "villa_price_override_added", villa_id, {"override_id": override["id"]})
    return override


@router.delete("/{villa_id}/price-overrides/{override_id}")
async def remove_price_override(villa_id: str, override_id: str, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    result = await db.villas.update_one(
        {"organization_id": org_id, "id": villa_id},
        {"$pull": {"price_overrides": {"id": override_id}}},
    )
    if result.matched_count == 0:
        raise AppError(404, "villa_not_found", "Villa bulunamadı.")
    await _audit(db, org_id, user, "villa_price_override_removed", villa_id, {"override_id": override_id})
    return {"ok": True}


@router.get("/{villa_id}/availability")
async def check_availability(
    villa_id: str,
    start_date: str = Query(...),
    end_date: str = Query(...),
    db=Depends(get_db),
    user: dict = AdminDep,
):
    org_id = user["organization_id"]
    doc = await db.villas.find_one({"organization_id": org_id, "id": villa_id}, {"_id": 0, "blocked_dates": 1, "price_overrides": 1, "price_per_night": 1, "min_stay_nights": 1, "currency": 1})
    if not doc:
        raise AppError(404, "villa_not_found", "Villa bulunamadı.")

    conflicts = []
    for bd in doc.get("blocked_dates", []):
        if bd["start_date"] <= end_date and bd["end_date"] >= start_date:
            conflicts.append(bd)

    return {
        "villa_id": villa_id,
        "start_date": start_date,
        "end_date": end_date,
        "available": len(conflicts) == 0,
        "conflicts": conflicts,
        "base_price_per_night": doc.get("price_per_night", 0),
        "currency": doc.get("currency", "TRY"),
        "min_stay_nights": doc.get("min_stay_nights", 1),
        "price_overrides": [
            po for po in doc.get("price_overrides", [])
            if po["start_date"] <= end_date and po["end_date"] >= start_date
        ],
    }
