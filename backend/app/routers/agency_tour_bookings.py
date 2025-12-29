from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from app.auth import require_roles
from app.db import get_db
from app.utils import to_object_id
from app.services.agency_offline_payment import prepare_offline_payment_for_tour_booking

router = APIRouter(prefix="/api/agency", tags=["agency:tours:booking"])


def _oid_or_404(id_str: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")


def _sid(x: Any) -> str:
    return str(x)


@router.get("/tour-bookings")
async def list_tour_bookings(
    status: str | None = None,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    query: Dict[str, Any] = {"agency_id": agency_id}
    if status:
        query["status"] = status

    cursor = db.tour_booking_requests.find(query).sort("created_at", -1)
    items: List[Dict[str, Any]] = []
    async for doc in cursor:
        d = dict(doc)
        d["id"] = _sid(d.pop("_id"))
        items.append(d)
    return {"items": items}


@router.post("/tour-bookings/{request_id}/set-status")
async def set_tour_booking_status(
    request_id: str,
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    new_status = (body.get("status") or "").strip()
    if new_status not in {"new", "approved", "rejected", "cancelled"}:
        raise HTTPException(status_code=400, detail="INVALID_STATUS")

    # Convert string ID to ObjectId for MongoDB query
    request_oid = _oid_or_404(request_id)
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    result = await db.tour_booking_requests.update_one(
        {"_id": request_oid, "agency_id": agency_id},
        {"$set": {"status": new_status, "updated_at": now, "staff_note": body.get("note")}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")

    return {"ok": True, "status": new_status}


@router.get("/tour-bookings/{request_id}")
async def get_tour_booking_detail(
    request_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """Get tour booking request detail with internal notes"""
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    # Convert string ID to ObjectId for MongoDB query
    request_oid = _oid_or_404(request_id)

    doc = await db.tour_booking_requests.find_one(
        {"_id": request_oid, "agency_id": agency_id}
    )

    if not doc:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")

    # Convert to dict and format response
    result = dict(doc)
    result["id"] = _sid(result.pop("_id"))
    
    # Ensure internal_notes field exists (empty list if not present)
    if "internal_notes" not in result:
        result["internal_notes"] = []

    return result


@router.post("/tour-bookings/{request_id}/add-note")
async def add_internal_note(
    request_id: str,
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """Add internal note to tour booking request"""
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    note_text = (body.get("text") or "").strip()
    if len(note_text) < 2:
        raise HTTPException(status_code=400, detail="INVALID_NOTE")

    # Convert string ID to ObjectId for MongoDB query
    request_oid = _oid_or_404(request_id)
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # Create note object
    note = {
        "text": note_text,
        "created_at": now,
        "actor": {
            "user_id": _sid(user.get("id")),
            "name": user.get("name", "Unknown"),
            "role": user.get("roles", ["unknown"])[0] if user.get("roles") else "unknown"
        }
    }

    # Add note to internal_notes array
    result = await db.tour_booking_requests.update_one(
        {"_id": request_oid, "agency_id": agency_id},
        {"$push": {"internal_notes": note}, "$set": {"updated_at": now}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")



@router.post("/tour-bookings/{request_id}/prepare-offline-payment")
async def prepare_offline_payment(
    request_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """Prepare offline payment snapshot for a tour booking request.

    - Only allowed for status in {"new", "approved"}
    - Uses agency_payment_settings.offline as source
    - Idempotent if snapshot already exists
    """
    agency_id = _sid(user.get("agency_id"))
    org_id = _sid(user.get("organization_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    request_oid = _oid_or_404(request_id)

    doc = await db.tour_booking_requests.find_one(
        {"_id": request_oid, "agency_id": agency_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")

    updated = await prepare_offline_payment_for_tour_booking(
        org_id=org_id,
        agency_id=agency_id,
        booking=doc,
    )

    # Normalize id field for response
    result = dict(updated)
    result["id"] = _sid(result.pop("_id"))
    return result

    return {"ok": True}
