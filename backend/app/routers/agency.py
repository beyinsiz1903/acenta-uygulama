from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.mongo_cache_service import cache_get, cache_set
from app.services.redis_cache import redis_get, redis_set
from app.utils import now_utc


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
    sheet_managed_inventory = bool((agg or {}).get("sheet_managed_inventory"))
    sheet_inventory_date = (agg or {}).get("sheet_inventory_date")
    sheet_last_sync_at = (agg or {}).get("sheet_last_sync_at")
    sheet_last_sync_status = (agg or {}).get("sheet_last_sync_status")
    sheet_reservations_imported = (agg or {}).get("sheet_reservations_imported")

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
        "sheet_managed_inventory": sheet_managed_inventory,
        "sheet_inventory_date": sheet_inventory_date,
        "sheet_last_sync_at": sheet_last_sync_at,
        "sheet_last_sync_status": sheet_last_sync_status,
        "sheet_reservations_imported": sheet_reservations_imported,
        "status_label": status_label,
    }

router = APIRouter(prefix="/api/agency", tags=["agency"])


@router.get("/hotels", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def my_hotels(user=Depends(get_current_user)):
    db = await get_db()
    agency_id = user.get("agency_id")
    if not agency_id:
        raise HTTPException(status_code=400, detail="Bu kullanıcı bir acenteye bağlı değil")

    # Cache: L1 Redis → L2 MongoDB (agency hotel links, 30 min)
    cache_key = f"agency_hotels:{user['organization_id']}:{agency_id}"
    redis_hit = await redis_get(cache_key)
    if redis_hit:
        return redis_hit
    cached = await cache_get(cache_key)
    if cached:
        await redis_set(cache_key, cached, ttl_seconds=300)
        return cached

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

    today = now_utc().date().isoformat()
    snapshot_docs = await db.hotel_inventory_snapshots.find(
        {
            "hotel_id": {"$in": hotel_ids},
            "date": {"$gte": today},
        },
        {"hotel_id": 1, "date": 1, "allotment": 1, "stop_sale": 1},
    ).sort("date", 1).to_list(10000)

    snapshot_by_hotel: dict[str, dict[str, object]] = {}
    for snap in snapshot_docs:
        hid = str(snap.get("hotel_id") or "")
        if not hid:
            continue
        current = snapshot_by_hotel.get(hid)
        snap_date = str(snap.get("date") or "")
        if not current or snap_date < str(current.get("date") or ""):
            snapshot_by_hotel[hid] = {
                "date": snap_date,
                "allotment": float(snap.get("allotment", 0) or 0),
                "stop_sale": bool(snap.get("stop_sale")),
            }
            continue
        if snap_date == current.get("date"):
            current["allotment"] = float(current.get("allotment", 0) or 0) + float(snap.get("allotment", 0) or 0)
            current["stop_sale"] = bool(current.get("stop_sale")) or bool(snap.get("stop_sale"))

    connection_docs = await db.hotel_portfolio_sources.find(
        {
            "organization_id": org_id,
            "hotel_id": {"$in": hotel_ids},
            "source_type": "google_sheets",
        },
        {
            "hotel_id": 1,
            "agency_id": 1,
            "last_sync_at": 1,
            "last_sync_status": 1,
            "last_reservation_import_summary": 1,
        },
    ).to_list(1000)

    connection_by_hotel: dict[str, dict] = {}
    for conn in connection_docs:
        hid = str(conn.get("hotel_id") or "")
        if not hid:
            continue
        is_agency_specific = str(conn.get("agency_id") or "") == str(agency_id)
        current = connection_by_hotel.get(hid)
        if current is None or is_agency_specific:
            connection_by_hotel[hid] = conn

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
        snapshot = snapshot_by_hotel.get(str(hid))
        connection = connection_by_hotel.get(str(hid)) or {}
        agg = {
            "stop_sell_active": stop_by_hotel.get(hid, False) or bool((snapshot or {}).get("stop_sale")),
            "allocation_limit": (snapshot or {}).get("allotment") if snapshot else alloc_by_hotel.get(hid),
            "sheet_managed_inventory": snapshot is not None,
            "sheet_inventory_date": (snapshot or {}).get("date"),
            "sheet_last_sync_at": connection.get("last_sync_at"),
            "sheet_last_sync_status": connection.get("last_sync_status"),
            "sheet_reservations_imported": (connection.get("last_reservation_import_summary") or {}).get("processed", 0),
        }
        row = _normalize_agency_hotel(h, link_by_hotel.get(hid), agg)
        row["cm_status"] = cm_status_by_hotel.get(hid, "not_configured")
        items.append(row)

    result = {"items": items}

    # Cache the result: L1 Redis (5 min) + L2 MongoDB (30 min)
    await redis_set(cache_key, result, ttl_seconds=300)
    await cache_set(cache_key, result, category="agency_hotel_links")

    return result
