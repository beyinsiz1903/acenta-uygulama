from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
# Availability & rates come from PMS connect layer in FAZ-8


from app.services.search_cache import canonical_search_payload, cache_key
from app.utils import now_utc

router = APIRouter(prefix="/agency", tags=["agency-search"])


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
    """Availability search (agency_extranet).

    FAZ-7: Adds response caching (TTL 5 min) keyed by canonical request payload.
    """

    db = await get_db()
    agency_id = user.get("agency_id")

    if not agency_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_AGENCY")

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
    
    # FAZ-8: PMS Connect Layer quote() (mock adapter for now)
    from app.services.connect_layer import quote

    quote_resp = await quote(
        organization_id=user["organization_id"],
        channel="agency_extranet",
        payload={
            "hotel_id": payload.hotel_id,
            "check_in": payload.check_in,
            "check_out": payload.check_out,
            "occupancy": payload.occupancy.model_dump(),
            "currency": payload.currency,
        },
    )

    # Keep existing response contract for frontend
    search_id = quote_resp.get("search_id") or f"srch_{uuid.uuid4().hex[:16]}"
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
            "nights": int(quote_resp.get("nights") or nights),
        },
        "occupancy": {
            "adults": payload.occupancy.adults,
            "children": payload.occupancy.children,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rooms": quote_resp.get("rooms") or [],
        "source": quote_resp.get("source") or "pms",
    }

    # FAZ-7: store cache (5 min TTL)
    ttl_seconds = 300
    expires_at = now_utc() + timedelta(seconds=ttl_seconds)
    await db.search_cache.update_one(
        {"_id": key},
        {
            "$set": {
                "organization_id": user["organization_id"],
                "agency_id": agency_id,
                "normalized": normalized,
                "response": response,
                "expires_at": expires_at,
                "created_at": now_utc(),
            }
        },
        upsert=True,
    )

    
    return response
