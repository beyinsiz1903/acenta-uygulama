from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError

logger = logging.getLogger(__name__)

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


class PassengerCreate(BaseModel):
    name: str
    passport_number: str = ""
    seat_number: str = ""
    booking_id: Optional[str] = None
    ticket_number: str = ""


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


async def _audit(db, org_id: str, user: dict, action: str, target_id: str, meta: dict = None):
    try:
        from app.services.audit import write_audit_log
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles") or []},
            request=None,
            action=action,
            target_type="flight",
            target_id=target_id,
            before=None,
            after=None,
            meta=meta or {},
        )
    except Exception:
        logger.exception("Audit log failed for %s: %s", action, target_id)


@router.get("", dependencies=[AdminDep])
async def list_flights(
    status: Optional[str] = None,
    departure_date: Optional[str] = None,
    airline: Optional[str] = None,
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
    if departure_date:
        filt["departure_date"] = departure_date
    if airline:
        filt["airline"] = {"$regex": airline, "$options": "i"}
    if search:
        filt["flight_number"] = {"$regex": search, "$options": "i"}
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
        raise AppError(404, "NOT_FOUND", "Ucus bulunamadi")
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
    result = _doc_to_dict(doc)
    await _audit(db, org_id, user, "FLIGHT_CREATED", result["id"], {"flight_number": body.flight_number})
    return result


@router.patch("/{flight_id}", dependencies=[AdminDep])
async def patch_flight(flight_id: str, body: FlightPatch, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise AppError(400, "NO_CHANGES", "Guncelleme verisi yok")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.flights.update_one({"id": flight_id, "organization_id": org_id}, {"$set": updates})
    if result.matched_count == 0:
        raise AppError(404, "NOT_FOUND", "Ucus bulunamadi")
    doc = await db.flights.find_one({"id": flight_id, "organization_id": org_id}, {"_id": 0})
    await _audit(db, org_id, user, "FLIGHT_UPDATED", flight_id, {"fields": list(updates.keys())})
    return _doc_to_dict(doc)


@router.delete("/{flight_id}", dependencies=[AdminDep])
async def delete_flight(flight_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    result = await db.flights.delete_one({"id": flight_id, "organization_id": org_id})
    if result.deleted_count == 0:
        raise AppError(404, "NOT_FOUND", "Ucus bulunamadi")
    await _audit(db, org_id, user, "FLIGHT_DELETED", flight_id)
    return {"ok": True}


@router.get("/{flight_id}/passengers", dependencies=[AdminDep])
async def get_passengers(flight_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.flights.find_one({"id": flight_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        raise AppError(404, "NOT_FOUND", "Ucus bulunamadi")
    return {"passengers": doc.get("passengers", []), "flight_id": flight_id, "total": len(doc.get("passengers", []))}


@router.delete("/{flight_id}/passengers/{passenger_id}", dependencies=[AdminDep])
async def remove_passenger(flight_id: str, passenger_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.flights.find_one(
        {"id": flight_id, "organization_id": org_id, "passengers.id": passenger_id},
        {"_id": 1},
    )
    if not doc:
        raise AppError(404, "NOT_FOUND", "Ucus veya yolcu bulunamadi")
    now = datetime.now(timezone.utc).isoformat()
    await db.flights.update_one(
        {"id": flight_id, "organization_id": org_id},
        {
            "$pull": {"passengers": {"id": passenger_id}},
            "$inc": {"available_seats": 1},
            "$set": {"updated_at": now},
        },
    )
    await _audit(db, org_id, user, "FLIGHT_PASSENGER_REMOVED", flight_id, {"passenger_id": passenger_id})
    return {"ok": True}


@router.post("/{flight_id}/passengers", dependencies=[AdminDep])
async def add_passenger(flight_id: str, body: PassengerCreate, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]

    if not body.name.strip():
        raise AppError(400, "INVALID", "Yolcu adi gereklidir")

    passenger = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "passport_number": body.passport_number,
        "seat_number": body.seat_number,
        "booking_id": body.booking_id,
        "ticket_number": body.ticket_number,
        "status": "confirmed",
    }
    now = datetime.now(timezone.utc).isoformat()
    result = await db.flights.update_one(
        {"id": flight_id, "organization_id": org_id, "available_seats": {"$gt": 0}},
        {
            "$push": {"passengers": passenger},
            "$inc": {"available_seats": -1},
            "$set": {"updated_at": now},
        },
    )
    if result.modified_count == 0:
        exists = await db.flights.find_one({"id": flight_id, "organization_id": org_id}, {"_id": 1})
        if not exists:
            raise AppError(404, "NOT_FOUND", "Ucus bulunamadi")
        raise AppError(400, "NO_SEATS", "Bu ucusta bos koltuk bulunmamaktadir")
    await _audit(db, org_id, user, "FLIGHT_PASSENGER_ADDED", flight_id, {"passenger_name": body.name})
    return passenger


@router.post("/bulk-status", dependencies=[AdminDep])
async def bulk_update_status(payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    ids = payload.get("ids", [])
    new_status = payload.get("status", "")
    if not ids or not new_status:
        raise AppError(400, "INVALID", "ids ve status alanlari gereklidir")
    valid_statuses = ["scheduled", "boarding", "departed", "arrived", "cancelled", "delayed"]
    if new_status not in valid_statuses:
        raise AppError(400, "INVALID", f"Gecersiz durum. Gecerli degerler: {', '.join(valid_statuses)}")
    now = datetime.now(timezone.utc).isoformat()
    result = await db.flights.update_many(
        {"id": {"$in": ids}, "organization_id": org_id},
        {"$set": {"status": new_status, "updated_at": now}},
    )
    await _audit(db, org_id, user, "FLIGHT_BULK_STATUS", ",".join(ids[:5]), {"status": new_status, "count": result.modified_count})
    return {"ok": True, "modified_count": result.modified_count}
