from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc


def _normalize_agency_hotel(hotel: dict, link: dict | None, agg: dict | None) -> dict:
    """Build agency-facing hotel row with sales status fields.

    hotel: base hotel document
    link: agency_hotel_link document
    agg: optional aggregation info (stop_sell, allocation)
    """
    hotel_id = hotel.get("_id")
    location = hotel.get("city") or hotel.get("region") or ""

    channel = "agency_extranet"
    source = hotel.get("source") or "local"
    sales_mode = (link or {}).get("sales_mode") or "free_sale"

    # Derive status fields
    is_active = bool((link or {}).get("active") and hotel.get("active", True))
    stop_sell_active = bool((agg or {}).get("stop_sell_active"))
    allocation_available = agg.get("allocation_limit") if agg else None

    status_label = "Satışa Kapalı"
    if is_active and not stop_sell_active:
        if allocation_available is None or allocation_available > 5:
            status_label = "Satışa Açık"
        elif allocation_available > 0:
            status_label = "Kısıtlı"
        else:
            status_label = "Satışa Kapalı"

    return {
        "hotel_id": hotel_id,
        "hotel_name": hotel.get("name"),
        "location": location,
        "channel": channel,
        "source": source,
        "sales_mode": sales_mode,
        "is_active": is_active,
        "stop_sell_active": stop_sell_active,
        "allocation_available": allocation_available,
        "status_label": status_label,
    }

router = APIRouter(prefix="/api/agency", tags=["agency"])


@router.get("/hotels", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def my_hotels(user=Depends(get_current_user)):
    db = await get_db()
    agency_id = user.get("agency_id")
    if not agency_id:
        raise HTTPException(status_code=400, detail="Bu kullanıcı bir acenteye bağlı değil")

    links = await db.agency_hotel_links.find(
        {
            "organization_id": user["organization_id"],
            "agency_id": agency_id,
            "active": True,
        }
    ).to_list(2000)

    hotel_ids = [link["hotel_id"] for link in links]
    if not hotel_ids:
        return []

    hotels = await db.hotels.find({"organization_id": user["organization_id"], "_id": {"$in": hotel_ids}, "active": True}).sort("name", 1).to_list(2000)
    return [serialize_doc(h) for h in hotels]
