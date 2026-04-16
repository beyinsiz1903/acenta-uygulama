from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db

router = APIRouter(prefix="/api/admin/transfers", tags=["admin-transfers"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


class TransferCreate(BaseModel):
    transfer_type: str = Field(..., description="private | shuttle | vip")
    date: str
    pickup_time: str = ""
    pickup_location: str = ""
    dropoff_location: str = ""
    route_name: str = ""
    vehicle_id: Optional[str] = None
    driver_name: str = ""
    guide_id: Optional[str] = None
    booking_id: Optional[str] = None
    passengers: List[Dict[str, Any]] = []
    pax_count: int = 1
    notes: str = ""
    status: str = "planned"
    price: float = 0.0
    currency: str = "EUR"


class TransferPatch(BaseModel):
    transfer_type: Optional[str] = None
    date: Optional[str] = None
    pickup_time: Optional[str] = None
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    route_name: Optional[str] = None
    vehicle_id: Optional[str] = None
    driver_name: Optional[str] = None
    guide_id: Optional[str] = None
    booking_id: Optional[str] = None
    passengers: Optional[List[Dict[str, Any]]] = None
    pax_count: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None


def _doc_to_dict(doc: dict) -> dict:
    return {
        "id": doc.get("id") or str(doc.get("_id")),
        "transfer_type": doc.get("transfer_type", "private"),
        "date": doc.get("date", ""),
        "pickup_time": doc.get("pickup_time", ""),
        "pickup_location": doc.get("pickup_location", ""),
        "dropoff_location": doc.get("dropoff_location", ""),
        "route_name": doc.get("route_name", ""),
        "vehicle_id": doc.get("vehicle_id"),
        "driver_name": doc.get("driver_name", ""),
        "guide_id": doc.get("guide_id"),
        "booking_id": doc.get("booking_id"),
        "passengers": doc.get("passengers", []),
        "pax_count": doc.get("pax_count", 1),
        "notes": doc.get("notes", ""),
        "status": doc.get("status", "planned"),
        "price": float(doc.get("price", 0)),
        "currency": doc.get("currency", "EUR"),
        "organization_id": doc.get("organization_id"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


@router.get("", dependencies=[AdminDep])
async def list_transfers(
    status: Optional[str] = None,
    date: Optional[str] = None,
    transfer_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    filt: Dict[str, Any] = {"organization_id": org_id}
    if status:
        filt["status"] = status
    if date:
        filt["date"] = date
    if transfer_type:
        filt["transfer_type"] = transfer_type

    total = await db.transfers.count_documents(filt)
    skip = (page - 1) * page_size
    cursor = db.transfers.find(filt, {"_id": 0}).sort("date", -1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)
    return {"items": [_doc_to_dict(d) for d in docs], "total": total, "page": page, "page_size": page_size}


@router.get("/{transfer_id}", dependencies=[AdminDep])
async def get_transfer(transfer_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.transfers.find_one({"id": transfer_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Transfer bulunamadi"})
    return _doc_to_dict(doc)


@router.post("", dependencies=[AdminDep])
async def create_transfer(body: TransferCreate, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        **body.model_dump(),
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("id"),
    }
    await db.transfers.insert_one(doc)
    return _doc_to_dict(doc)


@router.patch("/{transfer_id}", dependencies=[AdminDep])
async def patch_transfer(transfer_id: str, body: TransferPatch, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        return JSONResponse(status_code=400, content={"code": "NO_CHANGES", "message": "Guncelleme verisi yok"})
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.transfers.update_one(
        {"id": transfer_id, "organization_id": org_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Transfer bulunamadi"})
    doc = await db.transfers.find_one({"id": transfer_id, "organization_id": org_id}, {"_id": 0})
    return _doc_to_dict(doc)


@router.delete("/{transfer_id}", dependencies=[AdminDep])
async def delete_transfer(transfer_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    result = await db.transfers.delete_one({"id": transfer_id, "organization_id": org_id})
    if result.deleted_count == 0:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Transfer bulunamadi"})
    return {"ok": True}


@router.post("/{transfer_id}/assign-vehicle", dependencies=[AdminDep])
async def assign_vehicle(transfer_id: str, payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()
    updates = {"updated_at": now}
    if "vehicle_id" in payload:
        updates["vehicle_id"] = payload["vehicle_id"]
    if "driver_name" in payload:
        updates["driver_name"] = payload["driver_name"]
    result = await db.transfers.update_one(
        {"id": transfer_id, "organization_id": org_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Transfer bulunamadi"})
    return {"ok": True}


@router.post("/{transfer_id}/assign-guide", dependencies=[AdminDep])
async def assign_guide(transfer_id: str, payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()
    result = await db.transfers.update_one(
        {"id": transfer_id, "organization_id": org_id},
        {"$set": {"guide_id": payload.get("guide_id"), "updated_at": now}},
    )
    if result.matched_count == 0:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Transfer bulunamadi"})
    return {"ok": True}


@router.get("/manifest/{date}", dependencies=[AdminDep])
async def get_manifest(date: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    cursor = db.transfers.find(
        {"organization_id": org_id, "date": date}, {"_id": 0}
    ).sort("pickup_time", 1)
    docs = await cursor.to_list(length=500)
    return {"date": date, "transfers": [_doc_to_dict(d) for d in docs], "total": len(docs)}
