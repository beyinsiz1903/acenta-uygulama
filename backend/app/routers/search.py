from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/agency", tags=["agency-search"])


class OccupancyIn(BaseModel):
    adults: int
    children: int = 0


class SearchRequestIn(BaseModel):
    hotel_id: str
    check_in: str  # YYYY-MM-DD
    check_out: str  # YYYY-MM-DD
    occupancy: OccupancyIn
    currency: str = "TRY"


@router.post("/search", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def search_availability(payload: SearchRequestIn, user=Depends(get_current_user)):
    """
    FAZ-2.1: Mock availability search
    Returns mock room availability and rates
    """
    db = await get_db()
    agency_id = user.get("agency_id")
    
    if not agency_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_AGENCY")
    
    # Validate hotel is linked to agency
    link = await db.agency_hotel_links.find_one({
        "organization_id": user["organization_id"],
        "agency_id": agency_id,
        "hotel_id": payload.hotel_id,
        "active": True,
    })
    
    if not link:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_HOTEL")
    
    # Get hotel info
    hotel = await db.hotels.find_one({
        "organization_id": user["organization_id"],
        "_id": payload.hotel_id,
        "active": True,
    })
    
    if not hotel:
        raise HTTPException(status_code=404, detail="HOTEL_NOT_FOUND")
    
    # Validate dates
    from datetime import datetime as dt
    try:
        check_in_date = dt.fromisoformat(payload.check_in)
        check_out_date = dt.fromisoformat(payload.check_out)
    except ValueError:
        raise HTTPException(status_code=422, detail="INVALID_DATE_FORMAT")
    
    if check_out_date <= check_in_date:
        raise HTTPException(status_code=422, detail="INVALID_DATE_RANGE")
    
    nights = (check_out_date - check_in_date).days
    if nights < 1:
        raise HTTPException(status_code=422, detail="MINIMUM_1_NIGHT")
    
    # Validate occupancy
    if payload.occupancy.adults < 1:
        raise HTTPException(status_code=422, detail="MINIMUM_1_ADULT")
    
    # Generate mock response (FAZ-2.1)
    search_id = f"srch_{uuid.uuid4().hex[:16]}"
    
    # Mock room types and rate plans
    mock_rooms = [
        {
            "room_type_id": "rt_standard",
            "name": "Standart Oda",
            "max_occupancy": {"adults": 2, "children": 2},
            "inventory_left": 5,
            "rate_plans": [
                {
                    "rate_plan_id": "rp_refundable",
                    "name": "İade Edilebilir",
                    "board": "RO",
                    "cancellation": f"FREE_CANCEL_UNTIL_{payload.check_in}",
                    "price": {
                        "currency": payload.currency,
                        "total": 2450.0 * nights,
                        "per_night": 2450.0,
                        "tax_included": True,
                    },
                },
                {
                    "rate_plan_id": "rp_nonrefundable",
                    "name": "İade Edilemez (İndirimli)",
                    "board": "RO",
                    "cancellation": "NON_REFUNDABLE",
                    "price": {
                        "currency": payload.currency,
                        "total": 2100.0 * nights,
                        "per_night": 2100.0,
                        "tax_included": True,
                    },
                },
            ],
        },
        {
            "room_type_id": "rt_deluxe",
            "name": "Deluxe Oda",
            "max_occupancy": {"adults": 3, "children": 1},
            "inventory_left": 2,
            "rate_plans": [
                {
                    "rate_plan_id": "rp_refundable",
                    "name": "İade Edilebilir",
                    "board": "BB",
                    "cancellation": f"FREE_CANCEL_UNTIL_{payload.check_in}",
                    "price": {
                        "currency": payload.currency,
                        "total": 3200.0 * nights,
                        "per_night": 3200.0,
                        "tax_included": True,
                    },
                },
            ],
        },
    ]
    
    response = {
        "search_id": search_id,
        "hotel": {
            "id": hotel["_id"],
            "name": hotel.get("name"),
            "city": hotel.get("city"),
            "country": hotel.get("country"),
        },



class GuestInfoIn(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None


class BookingDraftCreateIn(BaseModel):
    search_id: str
    hotel_id: str
    room_type_id: str
    rate_plan_id: str
    guest: GuestInfoIn
    special_requests: Optional[str] = None


@router.post("/bookings/draft", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def create_booking_draft(payload: BookingDraftCreateIn, user=Depends(get_current_user)):
    """
    FAZ-3.0: Create booking draft (no payment yet)
    Locks the rate/availability snapshot
    """
    db = await get_db()
    agency_id = user.get("agency_id")
    
    if not agency_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_AGENCY")
    
    # Validate hotel link
    link = await db.agency_hotel_links.find_one({
        "organization_id": user["organization_id"],
        "agency_id": agency_id,
        "hotel_id": payload.hotel_id,
        "active": True,
    })
    
    if not link:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_HOTEL")
    
    # Get hotel
    hotel = await db.hotels.find_one({
        "organization_id": user["organization_id"],
        "_id": payload.hotel_id,
    })
    
    if not hotel:
        raise HTTPException(status_code=404, detail="HOTEL_NOT_FOUND")
    
    # FAZ-3.0: Mock draft creation (no real booking yet)
    # In FAZ-3.2, this will call PMS/CM to hold inventory
    
    draft_id = f"draft_{uuid.uuid4().hex[:16]}"
    
    # Mock rate snapshot (in real scenario, re-fetch from gateway)
    mock_rate_snapshot = {
        "room_type_id": payload.room_type_id,
        "room_type_name": "Standart Oda" if payload.room_type_id == "rt_standard" else "Deluxe Oda",
        "rate_plan_id": payload.rate_plan_id,
        "rate_plan_name": "İade Edilebilir" if payload.rate_plan_id == "rp_refundable" else "İade Edilemez",
        "board": "RO",
        "price": {
            "currency": "TRY",
            "total": 2450.0 if payload.rate_plan_id == "rp_refundable" else 2100.0,
            "per_night": 2450.0 if payload.rate_plan_id == "rp_refundable" else 2100.0,
            "tax_included": True,
        },
        "cancellation": "FREE_CANCEL" if payload.rate_plan_id == "rp_refundable" else "NON_REFUNDABLE",
    }
    
    draft = {
        "_id": draft_id,
        "organization_id": user["organization_id"],
        "agency_id": agency_id,
        "search_id": payload.search_id,
        "hotel_id": payload.hotel_id,
        "hotel_name": hotel.get("name"),
        "status": "draft",  # draft|confirmed|cancelled
        "guest": payload.guest.model_dump(),
        "special_requests": payload.special_requests,
        "rate_snapshot": mock_rate_snapshot,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "created_by": user.get("email"),
        "expires_at": None,  # FAZ-3.2'de 15 min TTL
    }
    
    await db.booking_drafts.insert_one(draft)
    
    saved = await db.booking_drafts.find_one({"_id": draft_id})
    return serialize_doc(saved)


@router.get("/bookings/draft/{draft_id}", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def get_booking_draft(draft_id: str, user=Depends(get_current_user)):
    """
    Get booking draft details
    """
    db = await get_db()
    agency_id = user.get("agency_id")
    
    draft = await db.booking_drafts.find_one({
        "organization_id": user["organization_id"],
        "agency_id": agency_id,
        "_id": draft_id,
    })
    
    if not draft:
        raise HTTPException(status_code=404, detail="DRAFT_NOT_FOUND")
    
    return serialize_doc(draft)

        "stay": {
            "check_in": payload.check_in,
            "check_out": payload.check_out,
            "nights": nights,
        },
        "occupancy": {
            "adults": payload.occupancy.adults,
            "children": payload.occupancy.children,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rooms": mock_rooms,
    }
    
    return response
