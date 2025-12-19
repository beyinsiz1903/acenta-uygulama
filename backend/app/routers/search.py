from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.hotel_availability import compute_availability
from app.services.rate_pricing import compute_rate_for_stay


from app.services.search_cache import canonical_search_payload, cache_key
from app.utils import now_utc

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

    # ------------------------------
    # FAZ-7: Search result caching (TTL 5 min)
    # Keyed by organization + agency + canonical payload (hotel/date/occupancy/currency/channel)
    # ------------------------------
    normalized = canonical_search_payload(
        {
            "hotel_id": payload.hotel_id,
            "check_in": payload.check_in,
            "check_out": payload.check_out,
            "currency": payload.currency,
            "occupancy": payload.occupancy.model_dump(),
            "channel": "agency_extranet",
        }
    )
    key = cache_key(user["organization_id"], agency_id, normalized)
    cached = await db.search_cache.find_one({"_id": key})
    if cached and cached.get("response"):
        return cached["response"]

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
    
    # FAZ-2.2.1: Compute REAL availability from DB
    availability = await compute_availability(
        hotel_id=payload.hotel_id,
        check_in=payload.check_in,
        check_out=payload.check_out,
        organization_id=user["organization_id"],
        channel="agency_extranet",  # FAZ-2.3: Channel context
    )
    
    # Generate search_id
    search_id = f"srch_{uuid.uuid4().hex[:16]}"
    
    # Map availability to gateway format
    rooms_response = []
    
    for room_type, avail_data in availability.items():
        if avail_data["available_rooms"] <= 0:
            continue  # Skip if no availability
        
        # Room type ID
        room_type_id = f"rt_{room_type}"
        room_type_name = room_type.title() + " Oda"
        
        # Max occupancy (from first room of this type - can be enhanced)
        max_occupancy = {"adults": 2, "children": 2}  # Default
        
        # FAZ-2.2.2: Get rates from rate_pricing service
        rate_plans_list = await compute_rate_for_stay(
            tenant_id=payload.hotel_id,
            room_type=room_type,
            check_in=payload.check_in,
            check_out=payload.check_out,
            nights=nights,
            organization_id=user["organization_id"],
            currency=payload.currency,
        )
        
        # Fallback: If no rate plans matched, use base_price
        if not rate_plans_list:
            per_night = avail_data.get("avg_base_price", 0)
            total_price = per_night * nights
            
            rate_plans_list = [
                {
                    "rate_plan_id": "rp_base",
                    "rate_plan_name": "Base Rate",
                    "board": "RO",
                    "cancellation": "FREE_CANCEL",
                    "price": {
                        "currency": payload.currency,
                        "total": round(total_price, 2),
                        "per_night": round(per_night, 2),
                        "tax_included": True,
                    },
                }
            ]
        
        rooms_response.append({
            "room_type_id": room_type_id,
            "name": room_type_name,
            "max_occupancy": max_occupancy,
            "inventory_left": avail_data["available_rooms"],
            "rate_plans": rate_plans_list,
        })
    
    # Generate response
    search_id = f"srch_{uuid.uuid4().hex[:16]}"
    
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
        "rooms": rooms_response,  # Real DB data!
    }
    
    return response
