from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.auth import get_current_user, require_roles
from app.db import get_db

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

AuthDep = Depends(require_roles(["super_admin", "admin", "agency_agent"]))


@router.get("/events", dependencies=[AuthDep])
async def list_events(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    event_type: Optional[str] = None,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    events: List[Dict[str, Any]] = []

    transfer_filt: Dict[str, Any] = {
        "organization_id": org_id,
        "date": {"$gte": start_date, "$lte": end_date},
    }
    cursor = db.transfers.find(transfer_filt, {"_id": 0}).sort("date", 1)
    transfers = await cursor.to_list(length=500)
    for t in transfers:
        if event_type and event_type != "transfer":
            continue
        events.append({
            "id": t.get("id"),
            "type": "transfer",
            "title": f"Transfer: {t.get('pickup_location', '')} → {t.get('dropoff_location', '')}",
            "date": t.get("date", ""),
            "time": t.get("pickup_time", ""),
            "status": t.get("status", "planned"),
            "resource_id": t.get("vehicle_id"),
            "meta": {"pax_count": t.get("pax_count", 0), "guide_id": t.get("guide_id")},
        })

    if not event_type or event_type == "flight":
        flight_filt: Dict[str, Any] = {
            "organization_id": org_id,
            "departure_date": {"$gte": start_date, "$lte": end_date},
        }
        cursor = db.flights.find(flight_filt, {"_id": 0}).sort("departure_date", 1)
        flights = await cursor.to_list(length=200)
        for f in flights:
            events.append({
                "id": f.get("id"),
                "type": "flight",
                "title": f"{f.get('airline', '')} {f.get('flight_number', '')} {f.get('departure_airport', '')}→{f.get('arrival_airport', '')}",
                "date": f.get("departure_date", ""),
                "time": f.get("departure_time", ""),
                "status": f.get("status", "scheduled"),
                "resource_id": None,
                "meta": {"available_seats": f.get("available_seats", 0)},
            })

    if not event_type or event_type == "visa":
        visa_filt: Dict[str, Any] = {
            "organization_id": org_id,
            "appointment_date": {"$gte": start_date, "$lte": end_date},
        }
        cursor = db.visa_applications.find(visa_filt, {"_id": 0})
        visas = await cursor.to_list(length=200)
        for v in visas:
            events.append({
                "id": v.get("id"),
                "type": "visa",
                "title": f"Vize: {v.get('customer_name', '')} - {v.get('destination_country', '')}",
                "date": v.get("appointment_date", ""),
                "time": "",
                "status": v.get("status", "draft"),
                "resource_id": None,
                "meta": {"consulate": v.get("consulate", "")},
            })

    if not event_type or event_type == "tour":
        tour_filt: Dict[str, Any] = {"organization_id": org_id, "status": "active"}
        cursor = db.tours.find(tour_filt, {"_id": 0}).limit(200)
        tours = await cursor.to_list(length=200)
        for tr in tours:
            events.append({
                "id": str(tr.get("_id", tr.get("id", ""))),
                "type": "tour",
                "title": f"Tur: {tr.get('name', '')}",
                "date": tr.get("start_date", tr.get("created_at", "")[:10] if tr.get("created_at") else ""),
                "time": "",
                "status": tr.get("status", "active"),
                "resource_id": None,
                "meta": {"destination": tr.get("destination", "")},
            })

    if not event_type or event_type == "insurance":
        ins_filt: Dict[str, Any] = {
            "organization_id": org_id,
            "start_date": {"$lte": end_date},
            "end_date": {"$gte": start_date},
        }
        cursor = db.insurance_policies.find(ins_filt, {"_id": 0}).limit(200)
        ins_docs = await cursor.to_list(length=200)
        for i in ins_docs:
            events.append({
                "id": i.get("id"),
                "type": "insurance",
                "title": f"Sigorta: {i.get('customer_name', '')} - {i.get('provider', '')}",
                "date": i.get("start_date", ""),
                "time": "",
                "status": i.get("status", "active"),
                "resource_id": None,
                "meta": {"policy_number": i.get("policy_number", "")},
            })

    events.sort(key=lambda e: (e.get("date", ""), e.get("time", "")))
    return {"events": events, "total": len(events), "start_date": start_date, "end_date": end_date}


@router.get("/resource-availability", dependencies=[AuthDep])
async def resource_availability(
    resource_type: str = Query(..., description="guide | vehicle"),
    date: str = Query(..., description="YYYY-MM-DD"),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]

    if resource_type == "guide":
        cursor = db.guides.find({"organization_id": org_id, "status": "active"}, {"_id": 0})
        resources = await cursor.to_list(length=200)
        assigned_cursor = db.transfers.find(
            {"organization_id": org_id, "date": date, "guide_id": {"$ne": None}}, {"guide_id": 1, "_id": 0}
        )
        assigned = await assigned_cursor.to_list(length=500)
        assigned_ids = {a["guide_id"] for a in assigned if a.get("guide_id")}
        result = []
        for r in resources:
            result.append({
                "id": r.get("id"),
                "name": r.get("name", ""),
                "available": r.get("id") not in assigned_ids,
                "type": "guide",
            })
        return {"date": date, "resources": result}

    elif resource_type == "vehicle":
        cursor = db.vehicles.find({"organization_id": org_id, "status": "active"}, {"_id": 0})
        resources = await cursor.to_list(length=200)
        assigned_cursor = db.transfers.find(
            {"organization_id": org_id, "date": date, "vehicle_id": {"$ne": None}}, {"vehicle_id": 1, "_id": 0}
        )
        assigned = await assigned_cursor.to_list(length=500)
        assigned_ids = {a["vehicle_id"] for a in assigned if a.get("vehicle_id")}
        result = []
        for r in resources:
            result.append({
                "id": r.get("id"),
                "name": f"{r.get('plate_number', '')} ({r.get('brand', '')} {r.get('model', '')})",
                "available": r.get("id") not in assigned_ids,
                "type": "vehicle",
                "capacity": r.get("capacity", 0),
            })
        return {"date": date, "resources": result}

    return JSONResponse(status_code=400, content={"code": "INVALID", "message": "resource_type guide veya vehicle olmali"})
