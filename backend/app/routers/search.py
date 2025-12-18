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
