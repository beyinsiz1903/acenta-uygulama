"""Agency Availability API — E-Tablo Entegrasyonu.

Hotels share availability via Google Sheets. This module exposes
synced availability data to agency users so they can see real-time
room availability, prices, and stop-sale status without checking
the raw spreadsheet.

Endpoints:
  GET /api/agency/availability          — hotel list with availability summary
  GET /api/agency/availability/changes  — recent inventory changes feed
  GET /api/agency/availability/{hotel_id} — detailed date×room grid
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/agency/availability", tags=["agency_availability"])

AgencyDep = Depends(require_roles(["agency_admin", "agency_agent"]))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


# ── Hotels with Availability Summary ──────────────────────────

@router.get("", dependencies=[AgencyDep])
async def list_hotels_availability(
    user=Depends(get_current_user),
):
    """Return agency's hotels with availability summary from synced sheets."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        return {"items": [], "total": 0}

    # Get agency's linked hotels
    links = await db.agency_hotel_links.find({
        "organization_id": org_id,
        "agency_id": agency_id,
        "active": True,
    }).to_list(2000)

    hotel_ids = [link["hotel_id"] for link in links]
    if not hotel_ids:
        return {"items": [], "total": 0}

    # Get hotels info
    hotels = await db.hotels.find({
        "organization_id": org_id,
        "_id": {"$in": hotel_ids},
        "active": True,
    }).sort("name", 1).to_list(2000)

    hotel_map = {h["_id"]: h for h in hotels}

    # Get sheet connection info for each hotel
    # Priority: agency-specific connection > hotel-level default connection
    tenant_id = user.get("tenant_id") or org_id
    
    # First get agency-specific connections
    agency_conns = await db.hotel_portfolio_sources.find({
        "tenant_id": tenant_id,
        "hotel_id": {"$in": hotel_ids},
        "agency_id": agency_id,
    }).to_list(2000)
    agency_conn_map = {c["hotel_id"]: c for c in agency_conns}
    
    # Then get default (no agency_id) connections for hotels without agency-specific ones
    default_conns = await db.hotel_portfolio_sources.find({
        "tenant_id": tenant_id,
        "hotel_id": {"$in": hotel_ids},
        "agency_id": {"$exists": False},
    }).to_list(2000)
    default_conn_map = {c["hotel_id"]: c for c in default_conns}
    
    # Merge: agency-specific takes priority
    conn_map = {}
    for hid in hotel_ids:
        conn_map[hid] = agency_conn_map.get(hid) or default_conn_map.get(hid)

    # Get availability stats per hotel (today + 30 days)
    today = _date_str(_now())
    end_date = _date_str(_now() + timedelta(days=30))

    items = []
    for hid in hotel_ids:
        hotel = hotel_map.get(hid)
        if not hotel:
            continue

        conn = conn_map.get(hid)

        # Count available inventory snapshots
        pipeline = [
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "hotel_id": hid,
                    "date": {"$gte": today, "$lte": end_date},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_records": {"$sum": 1},
                    "total_allotment": {"$sum": {"$ifNull": ["$allotment", 0]}},
                    "available_dates": {"$addToSet": "$date"},
                    "room_types": {"$addToSet": "$room_type"},
                    "stop_sale_count": {
                        "$sum": {"$cond": [{"$eq": ["$stop_sale", True]}, 1, 0]}
                    },
                    "avg_price": {"$avg": "$price"},
                    "min_price": {"$min": "$price"},
                    "max_price": {"$max": "$price"},
                    "last_updated": {"$max": "$updated_at"},
                }
            },
        ]

        agg_result = await db.hotel_inventory_snapshots.aggregate(pipeline).to_list(1)
        stats = agg_result[0] if agg_result else {}

        items.append({
            "hotel_id": hid,
            "hotel_name": hotel.get("name", ""),
            "city": hotel.get("city", ""),
            "stars": hotel.get("stars"),
            "sheet_connected": conn is not None,
            "last_sync_at": conn.get("last_sync_at") if conn else None,
            "last_sync_status": conn.get("last_sync_status") if conn else None,
            "sync_enabled": conn.get("sync_enabled", False) if conn else False,
            "total_records": stats.get("total_records", 0),
            "total_allotment": stats.get("total_allotment", 0),
            "available_dates_count": len(stats.get("available_dates", [])),
            "room_types_count": len(stats.get("room_types", [])),
            "room_types": sorted(stats.get("room_types", [])),
            "stop_sale_count": stats.get("stop_sale_count", 0),
            "avg_price": round(stats.get("avg_price") or 0, 2),
            "min_price": stats.get("min_price"),
            "max_price": stats.get("max_price"),
            "last_data_update": stats.get("last_updated"),
        })

    return {"items": items, "total": len(items)}


# ── Detailed Availability Grid for a Hotel ────────────────────

@router.get("/changes", dependencies=[AgencyDep])
async def list_availability_changes(
    hotel_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
):
    """Return recent inventory changes from sheet syncs."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id") or org_id

    if not agency_id:
        return {"items": [], "total": 0}

    # Get agency's linked hotel IDs
    links = await db.agency_hotel_links.find({
        "organization_id": org_id,
        "agency_id": agency_id,
        "active": True,
    }).to_list(2000)
    hotel_ids = [link["hotel_id"] for link in links]

    if not hotel_ids:
        return {"items": [], "total": 0}

    # Build query for sync runs
    query: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "hotel_id": {"$in": hotel_ids},
        "status": {"$in": ["success", "partial"]},
    }
    if hotel_id and hotel_id in hotel_ids:
        query["hotel_id"] = hotel_id

    runs = await db.sheet_sync_runs.find(query).sort("started_at", -1).to_list(limit)

    # Get hotel names
    hotels = await db.hotels.find(
        {"_id": {"$in": hotel_ids}},
        {"_id": 1, "name": 1},
    ).to_list(2000)
    hotel_name_map = {h["_id"]: h.get("name", "") for h in hotels}

    items = []
    for run in runs:
        items.append({
            "run_id": run["_id"],
            "hotel_id": run["hotel_id"],
            "hotel_name": hotel_name_map.get(run["hotel_id"], ""),
            "status": run.get("status"),
            "trigger": run.get("trigger"),
            "rows_read": run.get("rows_read", 0),
            "rows_changed": run.get("rows_changed", 0),
            "upserted": run.get("upserted", 0),
            "skipped": run.get("skipped", 0),
            "started_at": run.get("started_at"),
            "finished_at": run.get("finished_at"),
            "duration_ms": run.get("duration_ms", 0),
        })

    return {"items": items, "total": len(items)}


@router.get("/{hotel_id}", dependencies=[AgencyDep])
async def get_hotel_availability(
    hotel_id: str,
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    room_type: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    """Return detailed date×room_type availability grid for a hotel."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id") or org_id

    if not agency_id:
        return {"hotel": None, "grid": [], "dates": [], "room_types": []}

    # Verify agency has access to this hotel
    link = await db.agency_hotel_links.find_one({
        "organization_id": org_id,
        "agency_id": agency_id,
        "hotel_id": hotel_id,
        "active": True,
    })
    if not link:
        return {"hotel": None, "grid": [], "dates": [], "room_types": [], "error": "Bu otele erişiminiz yok."}

    # Get hotel info
    hotel = await db.hotels.find_one({"_id": hotel_id, "organization_id": org_id})
    if not hotel:
        return {"hotel": None, "grid": [], "dates": [], "room_types": [], "error": "Otel bulunamadı."}

    # Default date range: today + 14 days
    if not start_date:
        start_date = _date_str(_now())
    if not end_date:
        end_date = _date_str(_now() + timedelta(days=14))

    # Query inventory snapshots
    query: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
        "date": {"$gte": start_date, "$lte": end_date},
    }
    if room_type:
        query["room_type"] = room_type

    snapshots = await db.hotel_inventory_snapshots.find(query).sort("date", 1).to_list(5000)

    # Build grid data
    dates_set = set()
    room_types_set = set()
    grid_map: Dict[str, Dict[str, Any]] = {}

    for snap in snapshots:
        d = snap.get("date", "")
        rt = snap.get("room_type", "standard")
        dates_set.add(d)
        room_types_set.add(rt)

        key = f"{d}|{rt}"
        grid_map[key] = {
            "date": d,
            "room_type": rt,
            "price": snap.get("price"),
            "allotment": snap.get("allotment"),
            "stop_sale": snap.get("stop_sale", False),
            "updated_at": snap.get("updated_at"),
            "source": snap.get("source", ""),
        }

    dates = sorted(dates_set)
    room_types = sorted(room_types_set)

    # Build grid as flat array
    grid = []
    for d in dates:
        for rt in room_types:
            key = f"{d}|{rt}"
            if key in grid_map:
                grid.append(grid_map[key])
            else:
                grid.append({
                    "date": d,
                    "room_type": rt,
                    "price": None,
                    "allotment": None,
                    "stop_sale": False,
                    "updated_at": None,
                    "source": "",
                })

    # Get sheet connection info
    conn = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
    })

    return {
        "hotel": {
            "id": hotel_id,
            "name": hotel.get("name", ""),
            "city": hotel.get("city", ""),
            "stars": hotel.get("stars"),
        },
        "sheet_connected": conn is not None,
        "last_sync_at": conn.get("last_sync_at") if conn else None,
        "last_sync_status": conn.get("last_sync_status") if conn else None,
        "dates": dates,
        "room_types": room_types,
        "grid": grid,
        "total_records": len(snapshots),
        "date_range": {"start": start_date, "end": end_date},
    }
