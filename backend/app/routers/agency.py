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

    hotels = await db.hotels.find(
        {"organization_id": user["organization_id"], "_id": {"$in": hotel_ids}, "active": True}
    ).sort("name", 1).to_list(2000)

    # Build map for quick lookup
    link_by_hotel = {link_doc["hotel_id"]: link_doc for link_doc in links}

    org_id = user["organization_id"]

    # Aggregate stop-sell rules per hotel (any active rule marks hotel as stop_sell_active)
    stop_rules = await db.stop_sell_rules.find(
        {"organization_id": org_id, "tenant_id": {"$in": hotel_ids}, "is_active": True}
    ).to_list(2000)
    stop_by_hotel: dict[str, bool] = {}
    for r in stop_rules:
        hid = r.get("tenant_id")
        if not hid:
            continue
        stop_by_hotel[str(hid)] = True

    # Aggregate channel allocations per hotel for agency_extranet
    alloc_docs = await db.channel_allocations.find(
        {
            "organization_id": org_id,
            "tenant_id": {"$in": hotel_ids},
            "channel": "agency_extranet",
            "is_active": True,
        }
    ).to_list(2000)
    alloc_by_hotel: dict[str, float] = {}
    for a in alloc_docs:
        hid = a.get("tenant_id")
        if not hid:
            continue
        key = str(hid)
        alloc_by_hotel[key] = alloc_by_hotel.get(key, 0) + float(a.get("allotment", 0) or 0)

    # Join hotel integrations (channel manager status)
    integ_docs = await db.hotel_integrations.find(
        {
            "organization_id": org_id,
            "hotel_id": {"$in": hotel_ids},
            "kind": "channel_manager",
        }
    ).to_list(2000)
    cm_status_by_hotel: dict[str, str] = {}
    for integ in integ_docs:
        hid = integ.get("hotel_id")
        if not hid:
            continue
        cm_status_by_hotel[str(hid)] = integ.get("status") or "not_configured"

    items = []
    for h in hotels:
        hid = h["_id"]
        agg = {
            "stop_sell_active": stop_by_hotel.get(hid, False),
            "allocation_limit": alloc_by_hotel.get(hid),
        }
        row = _normalize_agency_hotel(h, link_by_hotel.get(hid), agg)
        row["cm_status"] = cm_status_by_hotel.get(hid, "not_configured")
        items.append(row)

    return {"items": items}
