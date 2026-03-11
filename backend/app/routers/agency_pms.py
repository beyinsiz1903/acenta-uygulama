"""PMS (Property Management System) API for Agency Users.

Provides hotel operations: arrival/departure/in-house lists,
room management, check-in/check-out, reservation enrichment,
and flight lookup via AviationStack API.

Endpoints:
  GET  /api/agency/pms/dashboard          — PMS dashboard summary
  GET  /api/agency/pms/arrivals           — Today's arrivals
  GET  /api/agency/pms/in-house           — Currently in-house guests
  GET  /api/agency/pms/departures         — Today's departures
  GET  /api/agency/pms/reservations       — PMS reservations with filters
  GET  /api/agency/pms/reservations/{id}  — Single reservation detail
  PUT  /api/agency/pms/reservations/{id}  — Update reservation (flight/tour/room)
  POST /api/agency/pms/reservations/{id}/check-in   — Check in guest
  POST /api/agency/pms/reservations/{id}/check-out   — Check out guest
  GET  /api/agency/pms/rooms              — List rooms
  POST /api/agency/pms/rooms              — Create room
  PUT  /api/agency/pms/rooms/{id}         — Update room
  DELETE /api/agency/pms/rooms/{id}       — Delete room
  POST /api/agency/pms/reservations/{id}/assign-room — Assign room
  GET  /api/agency/pms/flights/lookup     — Lookup flight info from AviationStack
  POST /api/agency/pms/reservations/{id}/auto-flight — Auto-fill flight info from API
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agency/pms", tags=["agency_pms"])

AgencyDep = Depends(require_roles(["agency_admin", "agency_agent", "admin", "super_admin"]))


def _now():
    return datetime.now(timezone.utc)


def _today_str():
    return date.today().isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_reservation(doc: dict) -> dict:
    """Serialize a reservation document, excluding _id."""
    result = {k: v for k, v in doc.items() if k != "_id"}
    result["id"] = str(doc.get("_id", ""))
    # Convert datetimes to ISO strings
    for key in ("created_at", "updated_at", "checked_in_at", "checked_out_at"):
        if key in result and isinstance(result[key], datetime):
            result[key] = result[key].isoformat()
    return result


def _serialize_room(doc: dict) -> dict:
    """Serialize a room document."""
    result = {k: v for k, v in doc.items() if k != "_id"}
    result["id"] = str(doc.get("_id", ""))
    for key in ("created_at", "updated_at"):
        if key in result and isinstance(result[key], datetime):
            result[key] = result[key].isoformat()
    return result


def _derive_pms_status(reservation: dict) -> str:
    """Derive PMS status from reservation data if not explicitly set."""
    if reservation.get("pms_status"):
        return reservation["pms_status"]

    status = reservation.get("status", "")
    if status == "cancelled":
        return "cancelled"

    today = _today_str()
    check_in = reservation.get("check_in", "")
    check_out = reservation.get("check_out", "")

    if not check_in:
        return "pending"

    if check_in > today:
        return "pending"
    elif check_in == today and check_out > today:
        return "arrival"
    elif check_in < today and check_out > today:
        return "in_house"
    elif check_out == today:
        return "departure"
    elif check_out < today:
        return "checked_out"

    return "pending"


async def _get_agency_hotel_ids(db, org_id: str, agency_id: str) -> list[str]:
    """Get all hotel IDs linked to this agency."""
    links = await db.agency_hotel_links.find(
        {"organization_id": org_id, "agency_id": agency_id, "active": True},
        {"hotel_id": 1}
    ).to_list(200)
    return [link["hotel_id"] for link in links]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", dependencies=[AgencyDep])
async def pms_dashboard(
    hotel_id: Optional[str] = None,
    target_date: Optional[str] = None,
    user=Depends(get_current_user),
):
    """PMS dashboard with arrival/departure/in-house/stayover counts."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        raise HTTPException(status_code=403, detail="Acenta bulunamadi")

    today = target_date or _today_str()

    # Build base query
    base_query = {
        "organization_id": org_id,
        "agency_id": agency_id,
        "status": {"$ne": "cancelled"},
    }
    if hotel_id:
        base_query["hotel_id"] = hotel_id

    # Arrivals: check_in == today, not yet checked in
    arrivals_query = {
        **base_query,
        "check_in": today,
        "pms_status": {"$nin": ["in_house", "checked_out", "no_show"]},
    }
    arrivals_count = await db.reservations.count_documents(arrivals_query)

    # Also count arrivals that don't have pms_status set
    arrivals_no_status = await db.reservations.count_documents({
        **base_query,
        "check_in": today,
        "pms_status": {"$exists": False},
    })
    arrivals_count = arrivals_count + arrivals_no_status

    # Departures: check_out == today
    departures_query = {
        **base_query,
        "check_out": today,
    }
    departures_count = await db.reservations.count_documents(departures_query)

    # In-house: checked in, check_out > today
    in_house_query = {
        **base_query,
        "pms_status": "in_house",
    }
    in_house_count = await db.reservations.count_documents(in_house_query)

    # Also include reservations where check_in < today and check_out > today without pms_status
    stayover_query = {
        **base_query,
        "check_in": {"$lt": today},
        "check_out": {"$gt": today},
        "pms_status": {"$exists": False},
    }
    stayover_no_status = await db.reservations.count_documents(stayover_query)
    in_house_count += stayover_no_status

    # Total rooms (from rooms collection)
    rooms_query = {"organization_id": org_id, "agency_id": agency_id}
    if hotel_id:
        rooms_query["hotel_id"] = hotel_id
    total_rooms = await db.pms_rooms.count_documents(rooms_query)

    # Occupied rooms
    occupied_rooms_query = {
        **base_query,
        "pms_status": "in_house",
        "room_number": {"$exists": True, "$nin": [None, ""]},
    }
    occupied_rooms = await db.reservations.count_documents(occupied_rooms_query)

    # Stayovers: in-house guests not arriving or departing today
    stayover_explicit = await db.reservations.count_documents({
        **base_query,
        "pms_status": "in_house",
        "check_in": {"$lt": today},
        "check_out": {"$gt": today},
    })
    stayover_implicit = await db.reservations.count_documents({
        **base_query,
        "pms_status": {"$exists": False},
        "check_in": {"$lt": today},
        "check_out": {"$gt": today},
    })
    stayover_count = stayover_explicit + stayover_implicit

    # Tomorrow arrivals
    tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
    tomorrow_arrivals = await db.reservations.count_documents({
        **base_query,
        "check_in": tomorrow,
    })

    # Get hotel list for selector
    hotel_ids = await _get_agency_hotel_ids(db, org_id, agency_id)
    hotels = []
    if hotel_ids:
        hotel_docs = await db.hotels.find(
            {"_id": {"$in": hotel_ids}},
            {"_id": 1, "name": 1}
        ).to_list(100)
        hotels = [{"id": str(h["_id"]), "name": h.get("name", "")} for h in hotel_docs]

    return {
        "date": today,
        "arrivals": arrivals_count,
        "departures": departures_count,
        "in_house": in_house_count,
        "stayover": stayover_count,
        "total_rooms": total_rooms,
        "occupied_rooms": occupied_rooms,
        "occupancy_rate": round((occupied_rooms / total_rooms * 100), 1) if total_rooms > 0 else 0,
        "tomorrow_arrivals": tomorrow_arrivals,
        "hotels": hotels,
    }


# ---------------------------------------------------------------------------
# Operational Lists
# ---------------------------------------------------------------------------

@router.get("/arrivals", dependencies=[AgencyDep])
async def pms_arrivals(
    hotel_id: Optional[str] = None,
    target_date: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Today's arrivals list."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        return {"items": [], "total": 0}

    today = target_date or _today_str()

    query = {
        "organization_id": org_id,
        "agency_id": agency_id,
        "check_in": today,
        "status": {"$ne": "cancelled"},
    }
    if hotel_id:
        query["hotel_id"] = hotel_id

    docs = await db.reservations.find(query).sort("guest_name", 1).to_list(500)
    items = [_serialize_reservation(doc) for doc in docs]

    # Enrich with derived pms_status
    for item in items:
        if not item.get("pms_status"):
            item["pms_status"] = "arrival"

    return {"items": items, "total": len(items), "date": today}


@router.get("/in-house", dependencies=[AgencyDep])
async def pms_in_house(
    hotel_id: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Currently in-house guests."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        return {"items": [], "total": 0}

    today = _today_str()

    # In-house: either explicitly marked or date-derived
    query = {
        "organization_id": org_id,
        "agency_id": agency_id,
        "status": {"$ne": "cancelled"},
        "$or": [
            {"pms_status": "in_house"},
            {
                "check_in": {"$lte": today},
                "check_out": {"$gt": today},
                "pms_status": {"$exists": False},
            },
        ],
    }
    if hotel_id:
        query["hotel_id"] = hotel_id

    docs = await db.reservations.find(query).sort("guest_name", 1).to_list(500)
    items = [_serialize_reservation(doc) for doc in docs]
    for item in items:
        if not item.get("pms_status"):
            item["pms_status"] = "in_house"

    return {"items": items, "total": len(items)}


@router.get("/stayovers", dependencies=[AgencyDep])
async def pms_stayovers(
    hotel_id: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Stayover guests: in the middle of their stay (not arriving or departing today)."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        return {"items": [], "total": 0}

    today = _today_str()

    query = {
        "organization_id": org_id,
        "agency_id": agency_id,
        "status": {"$ne": "cancelled"},
        "check_in": {"$lt": today},
        "check_out": {"$gt": today},
        "$or": [
            {"pms_status": "in_house"},
            {"pms_status": {"$exists": False}},
        ],
    }
    if hotel_id:
        query["hotel_id"] = hotel_id

    docs = await db.reservations.find(query).sort("guest_name", 1).to_list(500)
    items = [_serialize_reservation(doc) for doc in docs]
    for item in items:
        if not item.get("pms_status"):
            item["pms_status"] = "in_house"

    return {"items": items, "total": len(items)}


@router.get("/departures", dependencies=[AgencyDep])
async def pms_departures(
    hotel_id: Optional[str] = None,
    target_date: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Today's departures list."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        return {"items": [], "total": 0}

    today = target_date or _today_str()

    query = {
        "organization_id": org_id,
        "agency_id": agency_id,
        "check_out": today,
        "status": {"$ne": "cancelled"},
    }
    if hotel_id:
        query["hotel_id"] = hotel_id

    docs = await db.reservations.find(query).sort("guest_name", 1).to_list(500)
    items = [_serialize_reservation(doc) for doc in docs]
    for item in items:
        if not item.get("pms_status"):
            item["pms_status"] = "departure"

    return {"items": items, "total": len(items), "date": today}


# ---------------------------------------------------------------------------
# PMS Reservations (enhanced list with filters)
# ---------------------------------------------------------------------------

@router.get("/reservations", dependencies=[AgencyDep])
async def pms_reservations(
    hotel_id: Optional[str] = None,
    pms_status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    user=Depends(get_current_user),
):
    """List PMS reservations with filtering."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        return {"items": [], "total": 0}

    query = {
        "organization_id": org_id,
        "agency_id": agency_id,
    }
    if hotel_id:
        query["hotel_id"] = hotel_id
    if pms_status:
        query["pms_status"] = pms_status
    if date_from:
        query["check_in"] = {"$gte": date_from}
    if date_to:
        query.setdefault("check_out", {})
        if isinstance(query.get("check_out"), dict):
            query["check_out"]["$lte"] = date_to
        else:
            query["check_out"] = {"$lte": date_to}
    if search:
        query["$or"] = [
            {"guest_name": {"$regex": search, "$options": "i"}},
            {"pnr": {"$regex": search, "$options": "i"}},
            {"room_number": {"$regex": search, "$options": "i"}},
        ]

    docs = await db.reservations.find(query).sort("check_in", 1).to_list(limit)
    items = []
    for doc in docs:
        item = _serialize_reservation(doc)
        if not item.get("pms_status"):
            item["pms_status"] = _derive_pms_status(doc)
        items.append(item)

    return {"items": items, "total": len(items)}


@router.get("/reservations/{reservation_id}", dependencies=[AgencyDep])
async def get_pms_reservation(
    reservation_id: str,
    user=Depends(get_current_user),
):
    """Get single reservation with PMS details."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    doc = await db.reservations.find_one({
        "_id": reservation_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadi")

    item = _serialize_reservation(doc)
    if not item.get("pms_status"):
        item["pms_status"] = _derive_pms_status(doc)
    return item


# ---------------------------------------------------------------------------
# Reservation Updates (flight/tour/room info)
# ---------------------------------------------------------------------------

class FlightInfo(BaseModel):
    flight_no: Optional[str] = None
    airline: Optional[str] = None
    airport: Optional[str] = None
    flight_datetime: Optional[str] = None


class TourInfo(BaseModel):
    operator: Optional[str] = None
    tour_name: Optional[str] = None
    tour_code: Optional[str] = None


class ReservationUpdateIn(BaseModel):
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None
    pax: Optional[int] = None
    room_number: Optional[str] = None
    notes: Optional[str] = None
    arrival_flight: Optional[FlightInfo] = None
    departure_flight: Optional[FlightInfo] = None
    tour_info: Optional[TourInfo] = None


@router.put("/reservations/{reservation_id}", dependencies=[AgencyDep])
async def update_pms_reservation(
    reservation_id: str,
    payload: ReservationUpdateIn,
    user=Depends(get_current_user),
):
    """Update reservation details (flight, tour, room, guest info)."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    doc = await db.reservations.find_one({
        "_id": reservation_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadi")

    update_fields = {"updated_at": _now()}

    if payload.guest_name is not None:
        update_fields["guest_name"] = payload.guest_name
    if payload.guest_phone is not None:
        update_fields["guest_phone"] = payload.guest_phone
    if payload.guest_email is not None:
        update_fields["guest_email"] = payload.guest_email
    if payload.pax is not None:
        update_fields["pax"] = payload.pax
    if payload.room_number is not None:
        update_fields["room_number"] = payload.room_number
    if payload.notes is not None:
        update_fields["notes"] = payload.notes
    if payload.arrival_flight is not None:
        update_fields["arrival_flight"] = payload.arrival_flight.model_dump(exclude_none=True)
    if payload.departure_flight is not None:
        update_fields["departure_flight"] = payload.departure_flight.model_dump(exclude_none=True)
    if payload.tour_info is not None:
        update_fields["tour_info"] = payload.tour_info.model_dump(exclude_none=True)

    await db.reservations.update_one(
        {"_id": reservation_id},
        {"$set": update_fields},
    )

    updated = await db.reservations.find_one({"_id": reservation_id})
    item = _serialize_reservation(updated)
    if not item.get("pms_status"):
        item["pms_status"] = _derive_pms_status(updated)
    return item


# ---------------------------------------------------------------------------
# Check-in / Check-out
# ---------------------------------------------------------------------------

class CheckInPayload(BaseModel):
    room_number: Optional[str] = None
    notes: Optional[str] = None


@router.post("/reservations/{reservation_id}/check-in", dependencies=[AgencyDep])
async def check_in_guest(
    reservation_id: str,
    payload: Optional[CheckInPayload] = None,
    user=Depends(get_current_user),
):
    """Check in a guest (arrival -> in_house)."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    doc = await db.reservations.find_one({
        "_id": reservation_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadi")

    current_status = doc.get("pms_status") or _derive_pms_status(doc)
    if current_status == "in_house":
        raise HTTPException(status_code=409, detail="Misafir zaten giris yapmis")
    if current_status == "checked_out":
        raise HTTPException(status_code=409, detail="Misafir zaten cikis yapmis")
    if doc.get("status") == "cancelled":
        raise HTTPException(status_code=409, detail="Iptal edilmis rezervasyon")

    now = _now()
    update = {
        "pms_status": "in_house",
        "checked_in_at": now,
        "checked_in_by": user.get("email"),
        "updated_at": now,
    }

    if payload and payload.room_number:
        update["room_number"] = payload.room_number
    if payload and payload.notes:
        update["notes"] = payload.notes

    # If room assigned, update room status
    room_number = (payload and payload.room_number) or doc.get("room_number")
    if room_number:
        await db.pms_rooms.update_one(
            {
                "organization_id": org_id,
                "agency_id": agency_id,
                "room_number": room_number,
            },
            {"$set": {"status": "occupied", "current_reservation_id": reservation_id, "updated_at": now}},
        )

    await db.reservations.update_one({"_id": reservation_id}, {"$set": update})

    updated = await db.reservations.find_one({"_id": reservation_id})
    return _serialize_reservation(updated)


@router.post("/reservations/{reservation_id}/check-out", dependencies=[AgencyDep])
async def check_out_guest(
    reservation_id: str,
    user=Depends(get_current_user),
):
    """Check out a guest (in_house -> checked_out)."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    doc = await db.reservations.find_one({
        "_id": reservation_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadi")

    current_status = doc.get("pms_status") or _derive_pms_status(doc)
    if current_status == "checked_out":
        raise HTTPException(status_code=409, detail="Misafir zaten cikis yapmis")
    if current_status not in ("in_house", "departure"):
        raise HTTPException(status_code=409, detail="Misafir henuz giris yapmamis")

    now = _now()
    update = {
        "pms_status": "checked_out",
        "checked_out_at": now,
        "checked_out_by": user.get("email"),
        "updated_at": now,
    }

    await db.reservations.update_one({"_id": reservation_id}, {"$set": update})

    # Free up room
    room_number = doc.get("room_number")
    if room_number:
        await db.pms_rooms.update_one(
            {
                "organization_id": org_id,
                "agency_id": agency_id,
                "room_number": room_number,
            },
            {"$set": {"status": "cleaning", "current_reservation_id": None, "updated_at": now}},
        )

    updated = await db.reservations.find_one({"_id": reservation_id})
    return _serialize_reservation(updated)


# ---------------------------------------------------------------------------
# Room Assignment
# ---------------------------------------------------------------------------

class RoomAssignPayload(BaseModel):
    room_number: str


@router.post("/reservations/{reservation_id}/assign-room", dependencies=[AgencyDep])
async def assign_room(
    reservation_id: str,
    payload: RoomAssignPayload,
    user=Depends(get_current_user),
):
    """Assign a room to a reservation."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    doc = await db.reservations.find_one({
        "_id": reservation_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadi")

    now = _now()
    await db.reservations.update_one(
        {"_id": reservation_id},
        {"$set": {"room_number": payload.room_number, "updated_at": now}},
    )

    updated = await db.reservations.find_one({"_id": reservation_id})
    return _serialize_reservation(updated)


# ---------------------------------------------------------------------------
# Flight Lookup (AviationStack API)
# ---------------------------------------------------------------------------

AVIATIONSTACK_BASE = "http://api.aviationstack.com/v1"


async def _lookup_flight_aviationstack(flight_no: str, flight_date: Optional[str] = None) -> dict:
    """Query AviationStack API for flight info by IATA flight number."""
    api_key = os.environ.get("AVIATIONSTACK_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Ucus API anahtari yapilandirilmamis. Ayarlarda AVIATIONSTACK_API_KEY tanimlayin.",
        )

    params = {
        "access_key": api_key,
        "flight_iata": flight_no.strip().upper(),
    }
    if flight_date:
        params["flight_date"] = flight_date

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{AVIATIONSTACK_BASE}/flights", params=params)
            data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ucus API zaman asimina ugradi")
    except Exception as e:
        logger.error(f"AviationStack error: {e}")
        raise HTTPException(status_code=502, detail="Ucus API hatasi")

    if "error" in data:
        err_info = data["error"].get("info", "Bilinmeyen hata")
        logger.warning(f"AviationStack API error: {err_info}")
        raise HTTPException(status_code=400, detail=f"Ucus API: {err_info}")

    flights = data.get("data", [])
    if not flights:
        return {"found": False, "message": "Ucus bulunamadi", "flight_no": flight_no}

    flight = flights[0]

    departure = flight.get("departure", {})
    arrival = flight.get("arrival", {})
    airline_info = flight.get("airline", {})

    result = {
        "found": True,
        "flight_no": flight.get("flight", {}).get("iata", flight_no),
        "airline": airline_info.get("name", ""),
        "airline_iata": airline_info.get("iata", ""),
        "departure_airport": departure.get("airport", ""),
        "departure_iata": departure.get("iata", ""),
        "departure_scheduled": departure.get("scheduled", ""),
        "departure_estimated": departure.get("estimated", ""),
        "departure_terminal": departure.get("terminal", ""),
        "departure_gate": departure.get("gate", ""),
        "arrival_airport": arrival.get("airport", ""),
        "arrival_iata": arrival.get("iata", ""),
        "arrival_scheduled": arrival.get("scheduled", ""),
        "arrival_estimated": arrival.get("estimated", ""),
        "arrival_terminal": arrival.get("terminal", ""),
        "arrival_gate": arrival.get("gate", ""),
        "flight_status": flight.get("flight_status", ""),
        "flight_date": flight.get("flight_date", ""),
    }
    return result


@router.get("/flights/lookup", dependencies=[AgencyDep])
async def lookup_flight(
    flight_no: str = Query(..., description="IATA ucus kodu (orn: TK1234)"),
    flight_date: Optional[str] = Query(None, description="Ucus tarihi (YYYY-MM-DD)"),
    user=Depends(get_current_user),
):
    """Lookup flight information from AviationStack API."""
    if not flight_no or len(flight_no.strip()) < 3:
        raise HTTPException(status_code=400, detail="Gecerli bir ucus numarasi girin (orn: TK1234)")

    result = await _lookup_flight_aviationstack(flight_no, flight_date)
    return result


class AutoFlightPayload(BaseModel):
    flight_type: str  # "arrival" or "departure"
    flight_no: str
    flight_date: Optional[str] = None


@router.post("/reservations/{reservation_id}/auto-flight", dependencies=[AgencyDep])
async def auto_fill_flight(
    reservation_id: str,
    payload: AutoFlightPayload,
    user=Depends(get_current_user),
):
    """Lookup flight and auto-fill reservation flight info."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    doc = await db.reservations.find_one({
        "_id": reservation_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadi")

    if payload.flight_type not in ("arrival", "departure"):
        raise HTTPException(status_code=400, detail="flight_type 'arrival' veya 'departure' olmali")

    result = await _lookup_flight_aviationstack(payload.flight_no, payload.flight_date)

    if not result.get("found"):
        return {"updated": False, "message": "Ucus bulunamadi", "lookup": result}

    if payload.flight_type == "arrival":
        flight_data = {
            "flight_no": result["flight_no"],
            "airline": result["airline"],
            "airport": f"{result['arrival_airport']} ({result['arrival_iata']})",
            "flight_datetime": result["arrival_scheduled"] or result["arrival_estimated"] or "",
            "departure_airport": f"{result['departure_airport']} ({result['departure_iata']})",
            "flight_status": result["flight_status"],
        }
        update_field = "arrival_flight"
    else:
        flight_data = {
            "flight_no": result["flight_no"],
            "airline": result["airline"],
            "airport": f"{result['departure_airport']} ({result['departure_iata']})",
            "flight_datetime": result["departure_scheduled"] or result["departure_estimated"] or "",
            "arrival_airport": f"{result['arrival_airport']} ({result['arrival_iata']})",
            "flight_status": result["flight_status"],
        }
        update_field = "departure_flight"

    await db.reservations.update_one(
        {"_id": reservation_id},
        {"$set": {update_field: flight_data, "updated_at": _now()}},
    )

    updated = await db.reservations.find_one({"_id": reservation_id})
    item = _serialize_reservation(updated)
    if not item.get("pms_status"):
        item["pms_status"] = _derive_pms_status(updated)

    return {"updated": True, "reservation": item, "flight_data": flight_data, "lookup": result}


# ---------------------------------------------------------------------------
# Room Management
# ---------------------------------------------------------------------------

class RoomCreateIn(BaseModel):
    hotel_id: str
    room_number: str
    room_type: str = "Standard"
    floor: Optional[int] = None
    status: str = "available"
    notes: Optional[str] = None


class RoomUpdateIn(BaseModel):
    room_number: Optional[str] = None
    room_type: Optional[str] = None
    floor: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None


@router.get("/rooms", dependencies=[AgencyDep])
async def list_rooms(
    hotel_id: Optional[str] = None,
    status: Optional[str] = None,
    user=Depends(get_current_user),
):
    """List rooms for the agency's hotels."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        return {"items": [], "total": 0}

    query = {"organization_id": org_id, "agency_id": agency_id}
    if hotel_id:
        query["hotel_id"] = hotel_id
    if status:
        query["status"] = status

    docs = await db.pms_rooms.find(query).sort("room_number", 1).to_list(500)
    items = [_serialize_room(doc) for doc in docs]
    return {"items": items, "total": len(items)}


@router.post("/rooms", dependencies=[AgencyDep])
async def create_room(
    payload: RoomCreateIn,
    user=Depends(get_current_user),
):
    """Create a new room."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        raise HTTPException(status_code=403, detail="Acenta bulunamadi")

    # Check for duplicate room number in same hotel
    existing = await db.pms_rooms.find_one({
        "organization_id": org_id,
        "agency_id": agency_id,
        "hotel_id": payload.hotel_id,
        "room_number": payload.room_number,
    })
    if existing:
        raise HTTPException(status_code=409, detail="Bu oda numarasi zaten mevcut")

    now = _now()
    room_id = str(uuid.uuid4())
    room = {
        "_id": room_id,
        "organization_id": org_id,
        "agency_id": agency_id,
        "hotel_id": payload.hotel_id,
        "room_number": payload.room_number,
        "room_type": payload.room_type,
        "floor": payload.floor,
        "status": payload.status,
        "notes": payload.notes,
        "current_reservation_id": None,
        "created_at": now,
        "updated_at": now,
    }

    await db.pms_rooms.insert_one(room)
    return _serialize_room(room)


@router.put("/rooms/{room_id}", dependencies=[AgencyDep])
async def update_room(
    room_id: str,
    payload: RoomUpdateIn,
    user=Depends(get_current_user),
):
    """Update a room."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    doc = await db.pms_rooms.find_one({
        "_id": room_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Oda bulunamadi")

    update_fields = {"updated_at": _now()}
    if payload.room_number is not None:
        update_fields["room_number"] = payload.room_number
    if payload.room_type is not None:
        update_fields["room_type"] = payload.room_type
    if payload.floor is not None:
        update_fields["floor"] = payload.floor
    if payload.status is not None:
        update_fields["status"] = payload.status
    if payload.notes is not None:
        update_fields["notes"] = payload.notes

    await db.pms_rooms.update_one({"_id": room_id}, {"$set": update_fields})
    updated = await db.pms_rooms.find_one({"_id": room_id})
    return _serialize_room(updated)


@router.delete("/rooms/{room_id}", dependencies=[AgencyDep])
async def delete_room(
    room_id: str,
    user=Depends(get_current_user),
):
    """Delete a room."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    doc = await db.pms_rooms.find_one({
        "_id": room_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Oda bulunamadi")

    if doc.get("status") == "occupied":
        raise HTTPException(status_code=409, detail="Dolu oda silinemez")

    await db.pms_rooms.delete_one({"_id": room_id})
    return {"status": "deleted", "room_id": room_id}
