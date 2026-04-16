from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db

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


@router.get("", dependencies=[AdminDep])
async def list_vehicles(
    status: Optional[str] = None,
    vehicle_type: Optional[str] = None,
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
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Arac bulunamadi"})
    return _doc_to_dict(doc)


@router.post("", dependencies=[AdminDep])
async def create_vehicle(body: VehicleCreate, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
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
    return _doc_to_dict(doc)


@router.patch("/{vehicle_id}", dependencies=[AdminDep])
async def patch_vehicle(vehicle_id: str, body: VehiclePatch, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        return JSONResponse(status_code=400, content={"code": "NO_CHANGES", "message": "Guncelleme verisi yok"})
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.vehicles.update_one({"id": vehicle_id, "organization_id": org_id}, {"$set": updates})
    if result.matched_count == 0:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Arac bulunamadi"})
    doc = await db.vehicles.find_one({"id": vehicle_id, "organization_id": org_id}, {"_id": 0})
    return _doc_to_dict(doc)


@router.delete("/{vehicle_id}", dependencies=[AdminDep])
async def delete_vehicle(vehicle_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    result = await db.vehicles.delete_one({"id": vehicle_id, "organization_id": org_id})
    if result.deleted_count == 0:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Arac bulunamadi"})
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
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Arac bulunamadi"})

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
async def add_maintenance_record(vehicle_id: str, payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        "vehicle_id": vehicle_id,
        "date": payload.get("date", now[:10]),
        "type": payload.get("type", "general"),
        "description": payload.get("description", ""),
        "cost": float(payload.get("cost", 0)),
        "currency": payload.get("currency", "TRY"),
        "km_reading": payload.get("km_reading", 0),
        "created_at": now,
    }
    await db.vehicle_maintenance.insert_one(doc)
    return doc
