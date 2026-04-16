from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db

router = APIRouter(prefix="/api/admin/flights", tags=["admin-flights"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


class FlightCreate(BaseModel):
    flight_type: str = "charter"
    flight_number: str = ""
    airline: str = ""
    departure_airport: str = ""
    arrival_airport: str = ""
    departure_date: str = ""
    departure_time: str = ""
    arrival_date: str = ""
    arrival_time: str = ""
    aircraft_type: str = ""
    total_seats: int = 0
    available_seats: int = 0
    base_price: float = 0.0
    currency: str = "EUR"
    baggage_allowance: str = "20kg"
    status: str = "scheduled"
    notes: str = ""
    booking_ids: List[str] = []


class FlightPatch(BaseModel):
    flight_type: Optional[str] = None
    flight_number: Optional[str] = None
    airline: Optional[str] = None
    departure_airport: Optional[str] = None
    arrival_airport: Optional[str] = None
    departure_date: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_date: Optional[str] = None
    arrival_time: Optional[str] = None
    aircraft_type: Optional[str] = None
    total_seats: Optional[int] = None
    available_seats: Optional[int] = None
    base_price: Optional[float] = None
    currency: Optional[str] = None
    baggage_allowance: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


def _doc_to_dict(doc: dict) -> dict:
    return {
        "id": doc.get("id") or str(doc.get("_id")),
        "flight_type": doc.get("flight_type", "charter"),
        "flight_number": doc.get("flight_number", ""),
        "airline": doc.get("airline", ""),
        "departure_airport": doc.get("departure_airport", ""),
        "arrival_airport": doc.get("arrival_airport", ""),
        "departure_date": doc.get("departure_date", ""),
        "departure_time": doc.get("departure_time", ""),
        "arrival_date": doc.get("arrival_date", ""),
        "arrival_time": doc.get("arrival_time", ""),
        "aircraft_type": doc.get("aircraft_type", ""),
        "total_seats": doc.get("total_seats", 0),
        "available_seats": doc.get("available_seats", 0),
        "base_price": float(doc.get("base_price", 0)),
        "currency": doc.get("currency", "EUR"),
        "baggage_allowance": doc.get("baggage_allowance", "20kg"),
        "status": doc.get("status", "scheduled"),
        "notes": doc.get("notes", ""),
        "booking_ids": doc.get("booking_ids", []),
        "passengers": doc.get("passengers", []),
        "organization_id": doc.get("organization_id"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


@router.get("", dependencies=[AdminDep])
async def list_flights(
    status: Optional[str] = None,
    departure_date: Optional[str] = None,
    airline: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    filt: Dict[str, Any] = {"organization_id": org_id}
    if status:
        filt["status"] = status
    if departure_date:
        filt["departure_date"] = departure_date
    if airline:
        filt["airline"] = {"$regex": airline, "$options": "i"}
    total = await db.flights.count_documents(filt)
    skip = (page - 1) * page_size
    cursor = db.flights.find(filt, {"_id": 0}).sort("departure_date", -1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)
    return {"items": [_doc_to_dict(d) for d in docs], "total": total, "page": page, "page_size": page_size}


@router.get("/{flight_id}", dependencies=[AdminDep])
async def get_flight(flight_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.flights.find_one({"id": flight_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Ucus bulunamadi"})
    return _doc_to_dict(doc)


@router.post("", dependencies=[AdminDep])
async def create_flight(body: FlightCreate, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        **body.model_dump(),
        "passengers": [],
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("id"),
    }
    await db.flights.insert_one(doc)
    return _doc_to_dict(doc)


@router.patch("/{flight_id}", dependencies=[AdminDep])
async def patch_flight(flight_id: str, body: FlightPatch, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        return JSONResponse(status_code=400, content={"code": "NO_CHANGES", "message": "Guncelleme verisi yok"})
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.flights.update_one({"id": flight_id, "organization_id": org_id}, {"$set": updates})
    if result.matched_count == 0:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Ucus bulunamadi"})
    doc = await db.flights.find_one({"id": flight_id, "organization_id": org_id}, {"_id": 0})
    return _doc_to_dict(doc)


@router.delete("/{flight_id}", dependencies=[AdminDep])
async def delete_flight(flight_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    result = await db.flights.delete_one({"id": flight_id, "organization_id": org_id})
    if result.deleted_count == 0:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Ucus bulunamadi"})
    return {"ok": True}


@router.get("/{flight_id}/passengers", dependencies=[AdminDep])
async def get_passengers(flight_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.flights.find_one({"id": flight_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Ucus bulunamadi"})
    return {"passengers": doc.get("passengers", []), "flight_id": flight_id}


@router.delete("/{flight_id}/passengers/{passenger_id}", dependencies=[AdminDep])
async def remove_passenger(flight_id: str, passenger_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.flights.find_one(
        {"id": flight_id, "organization_id": org_id, "passengers.id": passenger_id},
        {"_id": 1},
    )
    if not doc:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Ucus veya yolcu bulunamadi"})
    now = datetime.now(timezone.utc).isoformat()
    await db.flights.update_one(
        {"id": flight_id, "organization_id": org_id},
        {
            "$pull": {"passengers": {"id": passenger_id}},
            "$inc": {"available_seats": 1},
            "$set": {"updated_at": now},
        },
    )
    return {"ok": True}


@router.post("/{flight_id}/passengers", dependencies=[AdminDep])
async def add_passenger(flight_id: str, payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.flights.find_one({"id": flight_id, "organization_id": org_id})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Ucus bulunamadi"})

    passenger = {
        "id": str(uuid.uuid4()),
        "name": payload.get("name", ""),
        "passport_number": payload.get("passport_number", ""),
        "seat_number": payload.get("seat_number", ""),
        "booking_id": payload.get("booking_id"),
        "ticket_number": payload.get("ticket_number", ""),
        "status": "confirmed",
    }
    now = datetime.now(timezone.utc).isoformat()
    await db.flights.update_one(
        {"id": flight_id, "organization_id": org_id},
        {
            "$push": {"passengers": passenger},
            "$inc": {"available_seats": -1},
            "$set": {"updated_at": now},
        },
    )
    return passenger
