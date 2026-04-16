from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/vehicles", tags=["admin-vehicles"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


class VehicleCreate(BaseModel):
    plate_number: str
    vehicle_type: str = "minibus"
    brand: str = ""
    model: str = ""
    year: int = 2024
    capacity: int = 0
    color: str = ""
    driver_name: str = ""
    driver_phone: str = ""
    insurance_expiry: str = ""
    inspection_expiry: str = ""
    daily_cost: float = 0.0
    currency: str = "TRY"
    status: str = "active"
    notes: str = ""


class VehiclePatch(BaseModel):
    plate_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    capacity: Optional[int] = None
    color: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    insurance_expiry: Optional[str] = None
    inspection_expiry: Optional[str] = None
    daily_cost: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class MaintenanceCreate(BaseModel):
    date: str = ""
    maintenance_type: str = "general"
    description: str = ""
    cost: float = 0.0
    currency: str = "TRY"
    mileage: int = 0
    next_maintenance_date: Optional[str] = None


def _doc_to_dict(doc: dict) -> dict:
    return {
        "id": doc.get("id") or str(doc.get("_id")),
        "plate_number": doc.get("plate_number", ""),
        "vehicle_type": doc.get("vehicle_type", "minibus"),
        "brand": doc.get("brand", ""),
        "model": doc.get("model", ""),
        "year": doc.get("year", 2024),
        "capacity": doc.get("capacity", 0),
        "color": doc.get("color", ""),
        "driver_name": doc.get("driver_name", ""),
        "driver_phone": doc.get("driver_phone", ""),
        "insurance_expiry": doc.get("insurance_expiry", ""),
        "inspection_expiry": doc.get("inspection_expiry", ""),
        "daily_cost": float(doc.get("daily_cost", 0)),
        "currency": doc.get("currency", "TRY"),
        "status": doc.get("status", "active"),
        "notes": doc.get("notes", ""),
        "total_km": doc.get("total_km", 0),
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
            target_type="vehicle",
            target_id=target_id,
            before=None,
            after=None,
            meta=meta or {},
        )
    except Exception:
        logger.exception("Audit log failed for %s: %s", action, target_id)


@router.get("", dependencies=[AdminDep])
async def list_vehicles(
    status: Optional[str] = None,
    vehicle_type: Optional[str] = None,
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
    if vehicle_type:
        filt["vehicle_type"] = vehicle_type
    if search:
        filt["plate_number"] = {"$regex": search, "$options": "i"}
    total = await db.vehicles.count_documents(filt)
    skip = (page - 1) * page_size
    cursor = db.vehicles.find(filt, {"_id": 0}).sort("plate_number", 1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)
    return {"items": [_doc_to_dict(d) for d in docs], "total": total, "page": page, "page_size": page_size}


@router.get("/{vehicle_id}", dependencies=[AdminDep])
async def get_vehicle(vehicle_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.vehicles.find_one({"id": vehicle_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        raise AppError(404, "NOT_FOUND", "Arac bulunamadi")
    return _doc_to_dict(doc)


@router.post("", dependencies=[AdminDep])
async def create_vehicle(body: VehicleCreate, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    existing = await db.vehicles.find_one(
        {"organization_id": org_id, "plate_number": body.plate_number}, {"_id": 1}
    )
    if existing:
        raise AppError(409, "ALREADY_EXISTS", f"Bu plaka zaten kayitli: {body.plate_number}")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        **body.model_dump(),
        "total_km": 0,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("id"),
    }
    await db.vehicles.insert_one(doc)
    result = _doc_to_dict(doc)
    await _audit(db, org_id, user, "VEHICLE_CREATED", result["id"], {"plate_number": body.plate_number})
    return result


@router.patch("/{vehicle_id}", dependencies=[AdminDep])
async def patch_vehicle(vehicle_id: str, body: VehiclePatch, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise AppError(400, "NO_CHANGES", "Guncelleme verisi yok")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.vehicles.update_one({"id": vehicle_id, "organization_id": org_id}, {"$set": updates})
    if result.matched_count == 0:
        raise AppError(404, "NOT_FOUND", "Arac bulunamadi")
    doc = await db.vehicles.find_one({"id": vehicle_id, "organization_id": org_id}, {"_id": 0})
    await _audit(db, org_id, user, "VEHICLE_UPDATED", vehicle_id, {"fields": list(updates.keys())})
    return _doc_to_dict(doc)


@router.delete("/{vehicle_id}", dependencies=[AdminDep])
async def delete_vehicle(vehicle_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    result = await db.vehicles.delete_one({"id": vehicle_id, "organization_id": org_id})
    if result.deleted_count == 0:
        raise AppError(404, "NOT_FOUND", "Arac bulunamadi")
    await _audit(db, org_id, user, "VEHICLE_DELETED", vehicle_id)
    return {"ok": True}


@router.get("/{vehicle_id}/calendar", dependencies=[AdminDep])
async def get_vehicle_calendar(
    vehicle_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    doc = await db.vehicles.find_one({"id": vehicle_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        raise AppError(404, "NOT_FOUND", "Arac bulunamadi")

    filt: Dict[str, Any] = {"organization_id": org_id, "vehicle_id": vehicle_id}
    if start_date and end_date:
        filt["date"] = {"$gte": start_date, "$lte": end_date}
    cursor = db.transfers.find(filt, {"_id": 0}).sort("date", 1)
    assignments = await cursor.to_list(length=500)
    return {"vehicle": _doc_to_dict(doc), "assignments": assignments}


@router.get("/{vehicle_id}/maintenance", dependencies=[AdminDep])
async def get_vehicle_maintenance(vehicle_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    cursor = db.vehicle_maintenance.find(
        {"organization_id": org_id, "vehicle_id": vehicle_id}, {"_id": 0}
    ).sort("date", -1)
    records = await cursor.to_list(length=100)
    return {"vehicle_id": vehicle_id, "records": records}


@router.post("/{vehicle_id}/maintenance", dependencies=[AdminDep])
async def add_maintenance_record(vehicle_id: str, body: MaintenanceCreate, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    vehicle = await db.vehicles.find_one({"id": vehicle_id, "organization_id": org_id}, {"_id": 1})
    if not vehicle:
        raise AppError(404, "NOT_FOUND", "Arac bulunamadi")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        "vehicle_id": vehicle_id,
        "date": body.date or now[:10],
        "type": body.maintenance_type,
        "maintenance_type": body.maintenance_type,
        "description": body.description,
        "cost": body.cost,
        "currency": body.currency,
        "km_reading": body.mileage,
        "mileage": body.mileage,
        "next_maintenance_date": body.next_maintenance_date,
        "created_at": now,
        "created_by": user.get("id"),
    }
    await db.vehicle_maintenance.insert_one(doc)

    if body.mileage > 0:
        await db.vehicles.update_one(
            {"id": vehicle_id, "organization_id": org_id},
            {"$set": {"total_km": body.mileage, "updated_at": now}},
        )

    await _audit(db, org_id, user, "VEHICLE_MAINTENANCE_ADDED", vehicle_id, {"maintenance_type": body.maintenance_type, "cost": body.cost})
    doc.pop("_id", None)
    return doc
