from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit import write_audit_log
from app.services.events import write_booking_event
from app.utils import date_to_utc_midnight, now_utc, serialize_doc, build_booking_public_view

router = APIRouter(prefix="/api/hotel", tags=["hotel"])


def _ensure_hotel_id(user: dict[str, Any]) -> str:
    hotel_id = user.get("hotel_id")
    if not hotel_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_HOTEL")
    return str(hotel_id)


def _parse_date(d: str) -> date:
    try:
        return date.fromisoformat(d)
    except Exception:
        raise HTTPException(status_code=422, detail="INVALID_DATE_FORMAT")


def _validate_range(start_date: str, end_date: str) -> None:
    s = _parse_date(start_date)
    e = _parse_date(end_date)
    if e < s:
        raise HTTPException(status_code=422, detail="INVALID_DATE_RANGE")


def _normalize_date_to_inclusive_overlap(date_from: Optional[str], date_to: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """UI sends inclusive date range; bookings overlap checks expect inclusive boundaries too."""
    if not date_from and not date_to:
        return None, None

    if date_from:
        _parse_date(date_from)
    if date_to:
        _parse_date(date_to)

    return date_from, date_to


# -------------------------
# Bookings (hotel view)
# -------------------------


@router.get(
    "/bookings",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff"]))],
)
async def list_hotel_bookings(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    agency_id: Optional[str] = None,
    user=Depends(get_current_user),
):
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    date_from, date_to = _normalize_date_to_inclusive_overlap(date_from, date_to)

    query: dict[str, Any] = {
        "organization_id": user["organization_id"],
        "hotel_id": hotel_id,
    }

    if status:
        query["status"] = status
    if agency_id:
        query["agency_id"] = agency_id

    # Date filter (overlap). Bookings store stay.check_in/check_out as YYYY-MM-DD strings.
    if date_from and date_to:
        # overlap (checkout exclusive stored, but filter is coarse)
        query["stay.check_in"] = {"$lte": date_to}
        query["stay.check_out"] = {"$gte": date_from}
    elif date_from:
        query["stay.check_out"] = {"$gte": date_from}
    elif date_to:
        query["stay.check_in"] = {"$lte": date_to}

    docs = await db.bookings.find(query).sort("created_at", -1).to_list(1000)

    # Join agency names (small list)
    agency_ids = list({d.get("agency_id") for d in docs if d.get("agency_id")})
    agency_map: dict[str, str] = {}
    if agency_ids:
        agencies = await db.agencies.find(
            {"organization_id": user["organization_id"], "_id": {"$in": agency_ids}}
        ).to_list(200)
        agency_map = {str(a["_id"]): a.get("name") or "-" for a in agencies}

    out = []
    for d in docs:
        sd = serialize_doc(d)
        sd["agency_name"] = agency_map.get(str(d.get("agency_id")), d.get("agency_name") or "-")
        out.append(sd)

    return out


@router.get(
    "/bookings/{booking_id}",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff"]))],
)
async def get_hotel_booking(booking_id: str, user=Depends(get_current_user)):
    """Get single booking for this hotel (normalized view)."""
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    booking = await db.bookings.find_one(
        {
            "organization_id": user["organization_id"],
            "hotel_id": hotel_id,
            "_id": booking_id,
        }
    )

    if not booking:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

    return build_booking_public_view(booking)



class BookingNoteIn(BaseModel):
    note: str = Field(min_length=1, max_length=4000)


@router.post(
    "/bookings/{booking_id}/note",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff"]))],
)
async def add_booking_note(booking_id: str, payload: BookingNoteIn, request: Request, user=Depends(get_current_user)):
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    now = now_utc()
    res = await db.bookings.update_one(
        {"organization_id": user["organization_id"], "hotel_id": hotel_id, "_id": booking_id},
        {
            "$set": {"updated_at": now},
            "$push": {
                "hotel_notes": {
                    "id": str(uuid.uuid4()),
                    "note": payload.note,
                    "created_at": now,
                    "created_by": user.get("email"),
                }
            },
        },
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

    doc = await db.bookings.find_one({"_id": booking_id})

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="booking.note",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after={"note": payload.note},
    )

    await write_booking_event(
        db,
        organization_id=user["organization_id"],
        event_type="booking.updated",
        booking_id=booking_id,
        hotel_id=str(user.get("hotel_id")),
        agency_id=str((doc or {}).get("agency_id") or ""),
        payload={"field": "hotel_notes"},
    )

    return serialize_doc(doc)


@router.post(
    "/bookings/{booking_id}/guest-note",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff"]))],
)
async def add_guest_note(booking_id: str, payload: BookingNoteIn, request: Request, user=Depends(get_current_user)):
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    now = now_utc()
    res = await db.bookings.update_one(
        {"organization_id": user["organization_id"], "hotel_id": hotel_id, "_id": booking_id},
        {
            "$set": {"updated_at": now, "guest_note": payload.note},
        },
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

    doc = await db.bookings.find_one({"_id": booking_id})

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="booking.guest_note",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after={"guest_note": payload.note},
    )

    await write_booking_event(
        db,
        organization_id=user["organization_id"],
        event_type="booking.updated",
        booking_id=booking_id,
        hotel_id=str(user.get("hotel_id")),
        agency_id=str((doc or {}).get("agency_id") or ""),
        payload={"field": "guest_note"},
    )

    return serialize_doc(doc)


class CancelRequestIn(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=2000)


@router.post(
    "/bookings/{booking_id}/cancel-request",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff"]))],
)
async def request_cancel(booking_id: str, payload: CancelRequestIn, request: Request, user=Depends(get_current_user)):
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    now = now_utc()
    res = await db.bookings.update_one(
        {"organization_id": user["organization_id"], "hotel_id": hotel_id, "_id": booking_id},
        {
            "$set": {
                "updated_at": now,
                "cancel_request": {
                    "status": "pending",
                    "reason": payload.reason,
                    "requested_at": now,
                    "requested_by": user.get("email"),
                },
            }
        },
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

    doc = await db.bookings.find_one({"_id": booking_id})

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="booking.cancel_request",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after={"cancel_request": {"status": "pending", "reason": payload.reason}},
    )

    await write_booking_event(
        db,
        organization_id=user["organization_id"],
        event_type="booking.updated",
        booking_id=booking_id,
        hotel_id=str(user.get("hotel_id")),
        agency_id=str((doc or {}).get("agency_id") or ""),
        payload={"field": "cancel_request"},
    )

    return serialize_doc(doc)


# -------------------------
# Stop-sell CRUD
# -------------------------


class StopSellIn(BaseModel):
    room_type: str = Field(description="standard|deluxe|...", min_length=1)
    start_date: str
    end_date: str
    reason: Optional[str] = None
    is_active: bool = True


@router.get(
    "/stop-sell",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff"]))],
)
async def list_stop_sell(user=Depends(get_current_user)):
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    rules = await db.stop_sell_rules.find(
        {"organization_id": user["organization_id"], "tenant_id": hotel_id}
    ).sort("updated_at", -1).to_list(500)

    return [serialize_doc(r) for r in rules]


@router.post(
    "/stop-sell",
    dependencies=[Depends(require_roles(["hotel_admin"]))],
)
async def create_stop_sell(payload: StopSellIn, request: Request, user=Depends(get_current_user)):
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    _validate_range(payload.start_date, payload.end_date)

    now = now_utc()
    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": hotel_id,
        "organization_id": user["organization_id"],
        "room_type": payload.room_type,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "reason": payload.reason,
        "is_active": bool(payload.is_active),
        # FAZ-8
        "source": "local",
        # FAZ-7: data hygiene (parsed dates)
        "start_date_dt": date_to_utc_midnight(payload.start_date),
        "end_date_dt": date_to_utc_midnight(payload.end_date),
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
        "updated_by": user.get("email"),
    }

    await db.stop_sell_rules.insert_one(doc)

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="stop_sell.create",
        target_type="stop_sell",
        target_id=doc["_id"],
        before=None,
        after=doc,
    )

    saved = await db.stop_sell_rules.find_one({"_id": doc["_id"]})
    return serialize_doc(saved)


@router.put(
    "/stop-sell/{rule_id}",
    dependencies=[Depends(require_roles(["hotel_admin"]))],
)
async def update_stop_sell(rule_id: str, payload: StopSellIn, request: Request, user=Depends(get_current_user)):
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    _validate_range(payload.start_date, payload.end_date)

    now = now_utc()

    # FAZ-7: data hygiene (parsed dates)
    update_doc = {
        "room_type": payload.room_type,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "reason": payload.reason,
        "is_active": bool(payload.is_active),
        "start_date_dt": date_to_utc_midnight(payload.start_date),
        "end_date_dt": date_to_utc_midnight(payload.end_date),
        "updated_at": now,
        "updated_by": user.get("email"),
    }

    res = await db.stop_sell_rules.update_one(
        {"organization_id": user["organization_id"], "tenant_id": hotel_id, "_id": rule_id},
        {"$set": update_doc},
    )

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="stop_sell.update",
        target_type="stop_sell",
        target_id=rule_id,
        before=await db.stop_sell_rules.find_one({"_id": rule_id}),
        after=update_doc,
    )


    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="STOP_SELL_NOT_FOUND")

    saved = await db.stop_sell_rules.find_one({"_id": rule_id})
    return serialize_doc(saved)


@router.delete(
    "/stop-sell/{rule_id}",
    dependencies=[Depends(require_roles(["hotel_admin"]))],
)
async def delete_stop_sell(rule_id: str, request: Request, user=Depends(get_current_user)):
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    before = await db.stop_sell_rules.find_one(
        {"organization_id": user["organization_id"], "tenant_id": hotel_id, "_id": rule_id}
    )
    if not before:
        raise HTTPException(status_code=404, detail="STOP_SELL_NOT_FOUND")

    res = await db.stop_sell_rules.delete_one(
        {"organization_id": user["organization_id"], "tenant_id": hotel_id, "_id": rule_id}
    )

    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="STOP_SELL_NOT_FOUND")

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="stop_sell.delete",
        target_type="stop_sell",
        target_id=rule_id,
        before=before,
        after=None,
    )

    return {"ok": True}


# -------------------------
# Allocation (channel allotment) CRUD
# -------------------------


class AllocationIn(BaseModel):
    room_type: str = Field(min_length=1)
    start_date: str
    end_date: str
    allotment: int = Field(ge=0)
    is_active: bool = True
    channel: str = "agency_extranet"


@router.get(
    "/allocations",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff"]))],
)
async def list_allocations(user=Depends(get_current_user)):
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    docs = await db.channel_allocations.find(
        {"organization_id": user["organization_id"], "tenant_id": hotel_id, "channel": "agency_extranet"}
    ).sort("updated_at", -1).to_list(500)

    return [serialize_doc(d) for d in docs]


@router.post(
    "/allocations",
    dependencies=[Depends(require_roles(["hotel_admin"]))],
)
async def create_allocation(payload: AllocationIn, request: Request, user=Depends(get_current_user)):
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    if payload.channel != "agency_extranet":
        raise HTTPException(status_code=422, detail="INVALID_CHANNEL")

    _validate_range(payload.start_date, payload.end_date)

    now = now_utc()
    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": hotel_id,
        "organization_id": user["organization_id"],
        "room_type": payload.room_type,
        "channel": "agency_extranet",
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        # FAZ-7: data hygiene (parsed dates)
        "start_date_dt": date_to_utc_midnight(payload.start_date),
        "end_date_dt": date_to_utc_midnight(payload.end_date),
        "allotment": int(payload.allotment),
        "is_active": bool(payload.is_active),
        # FAZ-8
        "source": "local",
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
        "updated_by": user.get("email"),
    }

    await db.channel_allocations.insert_one(doc)

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="allocation.create",
        target_type="allocation",
        target_id=doc["_id"],
        before=None,
        after=doc,
    )

    saved = await db.channel_allocations.find_one({"_id": doc["_id"]})
    return serialize_doc(saved)


@router.put(
    "/allocations/{allocation_id}",
    dependencies=[Depends(require_roles(["hotel_admin"]))],
)
async def update_allocation(allocation_id: str, payload: AllocationIn, request: Request, user=Depends(get_current_user)):
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    if payload.channel != "agency_extranet":
        raise HTTPException(status_code=422, detail="INVALID_CHANNEL")

    _validate_range(payload.start_date, payload.end_date)

    now = now_utc()
    
    update_doc = {
        "room_type": payload.room_type,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "allotment": int(payload.allotment),
        "is_active": bool(payload.is_active),
        "start_date_dt": date_to_utc_midnight(payload.start_date),
        "end_date_dt": date_to_utc_midnight(payload.end_date),
        "updated_at": now,
        "updated_by": user.get("email"),
    }

    before = await db.channel_allocations.find_one(
        {
            "organization_id": user["organization_id"],
            "tenant_id": hotel_id,
            "channel": "agency_extranet",
            "_id": allocation_id,
        }
    )

    res = await db.channel_allocations.update_one(
        {
            "organization_id": user["organization_id"],
            "tenant_id": hotel_id,
            "channel": "agency_extranet",
            "_id": allocation_id,
        },
        {"$set": update_doc},
    )

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="allocation.update",
        target_type="allocation",
        target_id=allocation_id,
        before=before,
        after=update_doc,
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="ALLOCATION_NOT_FOUND")

    saved = await db.channel_allocations.find_one({"_id": allocation_id})
    return serialize_doc(saved)


@router.delete(
    "/allocations/{allocation_id}",
    dependencies=[Depends(require_roles(["hotel_admin"]))],
)
async def delete_allocation(allocation_id: str, request: Request, user=Depends(get_current_user)):
    db = await get_db()
    hotel_id = _ensure_hotel_id(user)

    res = await db.channel_allocations.delete_one(
        {
            "organization_id": user["organization_id"],
            "tenant_id": hotel_id,
            "channel": "agency_extranet",
            "_id": allocation_id,
        }
    )


    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="allocation.delete",
        target_type="allocation",
        target_id=allocation_id,
        before=None,
        after=None,
    )

    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="ALLOCATION_NOT_FOUND")

    return {"ok": True}
