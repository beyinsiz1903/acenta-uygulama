from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.commission import create_financial_entry, month_from_check_in
from app.services.audit import write_audit_log
from app.services.events import write_booking_event
from app.utils import now_utc, serialize_doc
from app.services.email_outbox import enqueue_booking_email

router = APIRouter(prefix="/api/bookings", tags=["bookings"])
from datetime import datetime

from fastapi import Query

from app.context.org_context import get_current_org
from app.repositories.booking_repository import BookingRepository
from app.services.booking_service import (
    create_booking_draft,
    transition_to_booked,
    transition_to_cancel_requested,
    transition_to_quoted,
)



class BookingCancelIn(BaseModel):
    reason: Optional[str] = None


@router.post(
    "/{booking_id}/cancel",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "hotel_admin", "hotel_staff"]))],
)
async def cancel_booking(booking_id: str, payload: BookingCancelIn, request: Request, user=Depends(get_current_user)):
    """FAZ-6: Cancel booking and create reversal financial entry.

    - allowed: agency or hotel side
    - ownership: agency can cancel its own booking; hotel can cancel bookings for its hotel.
    - creates a negative reversal entry for the booking month.
    """
    db = await get_db()

    booking = await db.bookings.find_one({"organization_id": user["organization_id"], "_id": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

    roles = set(user.get("roles") or [])
    if roles.intersection({"agency_admin", "agency_agent"}):
        if str(booking.get("agency_id")) != str(user.get("agency_id")):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
    elif roles.intersection({"hotel_admin", "hotel_staff"}):
        if str(booking.get("hotel_id")) != str(user.get("hotel_id")):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
    else:
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    if booking.get("status") == "cancelled":
        return serialize_doc(booking)

    # FAZ-8: cancel in PMS first (block if PMS fails)
    pms_booking_id = booking.get("pms_booking_id")
    if pms_booking_id:
        from app.services.connect_layer import cancel_booking as pms_cancel_booking

        await pms_cancel_booking(
            organization_id=user["organization_id"],
            channel=str(booking.get("channel") or "agency_extranet"),
            pms_booking_id=str(pms_booking_id),
            reason=payload.reason,
        )

    if booking.get("commission_reversed") is True:
        # Already reversed; still set status cancelled if needed
        await db.bookings.update_one(
            {"_id": booking_id},
            {"$set": {"status": "cancelled", "updated_at": now_utc(), "cancel_reason": payload.reason}},
        )
        updated = await db.bookings.find_one({"_id": booking_id})
        return serialize_doc(updated)

    gross_amount = float(booking.get("gross_amount") or 0)
    commission_amount = float(booking.get("commission_amount") or 0)
    net_amount = float(booking.get("net_amount") or 0)
    currency = booking.get("currency") or booking.get("rate_snapshot", {}).get("price", {}).get("currency") or "TRY"
    month = month_from_check_in((booking.get("stay") or {}).get("check_in") or "")

    now = now_utc()

    await db.bookings.update_one(
        {"_id": booking_id},
        {
            "$set": {
                "status": "cancelled",
                "cancel_reason": payload.reason,
                "cancelled_at": now,
                "commission_reversed": True,
                "updated_at": now,
            }
        },
    )

    if month:
        await create_financial_entry(
            db,
            organization_id=user["organization_id"],
            booking_id=booking_id,
            agency_id=str(booking.get("agency_id")),
            hotel_id=str(booking.get("hotel_id")),
            entry_type="reversal",
            month=month,
            currency=currency,
            gross_amount=-gross_amount,
            commission_amount=-commission_amount,
            net_amount=-net_amount,
            source_status="cancelled",
            created_at=now,
        )

    # FAZ-9.3: enqueue booking.cancelled email for hotel + agency
    updated = await db.bookings.find_one({"_id": booking_id})
    
    try:
        org_id = user["organization_id"]

        # Hotel recipients (hotel_admin + hotel_staff)
        hotel_users_cursor = db.users.find(
            {
                "organization_id": org_id,
                "hotel_id": str(booking.get("hotel_id")),
                "roles": {"$in": ["hotel_admin", "hotel_staff"]},
                "is_active": True,
            }
        )
        hotel_users = await hotel_users_cursor.to_list(length=50)
        hotel_emails = [u.get("email") for u in hotel_users]

        # Agency recipients (agency_admin + agency_agent)
        agency_users_cursor = db.users.find(
            {
                "organization_id": org_id,
                "agency_id": str(booking.get("agency_id")),
                "roles": {"$in": ["agency_admin", "agency_agent"]},
                "is_active": True,
            }
        )
        agency_users = await agency_users_cursor.to_list(length=50)
        agency_emails = [u.get("email") for u in agency_users]

        to_addresses = hotel_emails + agency_emails

        await enqueue_booking_email(
            db,
            organization_id=org_id,
            booking=updated,
            event_type="booking.cancelled",
            to_addresses=to_addresses,
        )
    except Exception as e:  # pragma: no cover - email errors shouldn't break cancel
        import logging

        logging.getLogger("email_outbox").error("Failed to enqueue booking.cancelled email: %s", e, exc_info=True)

    # FAZ-7: event outbox + audit
    await write_booking_event(
        db,
        organization_id=user["organization_id"],
        event_type="booking.cancelled",
        booking_id=booking_id,
        hotel_id=str(booking.get("hotel_id")),
        agency_id=str(booking.get("agency_id")),
        payload={"reason": payload.reason},
    )

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="booking.cancel",
        target_type="booking",
        target_id=booking_id,
        before=booking,
        after=updated,
        meta={"reason": payload.reason},
    )

    return serialize_doc(updated)


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def create_booking_draft_endpoint(
    payload: Dict[str, Any],
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_org),
) -> Dict[str, Any]:
    """Create a booking in draft state (Phase 1 backoffice-only)."""

    organization_id = str(org["_id"])
    actor = {
        "actor_type": "user",
        "actor_id": user["id"],
        "email": user["email"],
        "roles": user.get("roles", []),
    }
    booking_id = await create_booking_draft(db, organization_id, actor, payload, request)
    repo = BookingRepository(db)
    doc = await repo.get_by_id(organization_id, booking_id)
    if not doc:
        raise HTTPException(status_code=500, detail="BOOKING_PERSISTENCE_ERROR")
    return serialize_doc(doc)


@router.post("/{booking_id}/quote", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def quote_booking_endpoint(
    booking_id: str,
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_org),
) -> Dict[str, Any]:
    organization_id = str(org["_id"])
    actor = {
        "actor_type": "user",
        "actor_id": user["id"],
        "email": user["email"],
        "roles": user.get("roles", []),
    }
    return await transition_to_quoted(db, organization_id, booking_id, actor, request)


@router.post("/{booking_id}/book", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def book_booking_endpoint(
    booking_id: str,
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_org),
) -> Dict[str, Any]:
    organization_id = str(org["_id"])
    actor = {
        "actor_type": "user",
        "actor_id": user["id"],
        "email": user["email"],
        "roles": user.get("roles", []),
    }
    return await transition_to_booked(db, organization_id, booking_id, actor, request)


@router.post("/{booking_id}/cancel-request", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def cancel_request_booking_endpoint(
    booking_id: str,
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_org),
) -> Dict[str, Any]:
    organization_id = str(org["_id"])
    actor = {
        "actor_type": "user",
        "actor_id": user["id"],
        "email": user["email"],
        "roles": user.get("roles", []),
    }
    return await transition_to_cancel_requested(db, organization_id, booking_id, actor, request)


@router.get("", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def list_bookings_endpoint(
    state: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 50,
    db=Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_org),
) -> List[Dict[str, Any]]:
    organization_id = str(org["_id"])
    repo = BookingRepository(db)
    docs = await repo.list_bookings(
        organization_id,
        state=state,
        start_date=start,
        end_date=end,
        limit=limit,
    )
    return [serialize_doc(d) for d in docs]


@router.get("/{booking_id}", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def get_booking_endpoint(
    booking_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_org),
) -> Dict[str, Any]:
    organization_id = str(org["_id"])
    repo = BookingRepository(db)
    doc = await repo.get_by_id(organization_id, booking_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BOOKING_NOT_FOUND")
    return serialize_doc(doc)

        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="booking.cancel",
        target_type="booking",
        target_id=booking_id,
        before=booking,
        after=updated,
        meta={"reason": payload.reason},
    )

    return serialize_doc(updated)


@router.post("/{booking_id}/track/whatsapp-click", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def track_whatsapp_click(booking_id: str, user=Depends(get_current_user)):
    """Track when user clicks WhatsApp share button on booking confirmed page.
    
    Idempotent: same booking_id + actor can only create one event (prevents spam)
    Used for pilot KPI: whatsappShareRate
    """
    db = await get_db()
    
    booking = await db.bookings.find_one({"organization_id": user["organization_id"], "_id": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")
    
    # Ownership check
    if str(booking.get("agency_id")) != str(user.get("agency_id")):
        raise HTTPException(status_code=403, detail="FORBIDDEN")
    
    # Check if event already exists for this booking + actor (idempotency)
    existing_event = await db.booking_events.find_one({
        "organization_id": user["organization_id"],
        "event_type": "booking.whatsapp_clicked",
        "booking_id": booking_id,
        "payload.actor_email": user.get("email")
    })
    
    if existing_event:
        # Already tracked, return success (idempotent)
        return {"ok": True, "already_tracked": True}
    
    # Write new event
    await write_booking_event(
        db,
        organization_id=user["organization_id"],
        event_type="booking.whatsapp_clicked",
        booking_id=booking_id,
        hotel_id=str(booking.get("hotel_id")),
        agency_id=str(booking.get("agency_id")),
        payload={"actor_email": user.get("email")}
    )
    
    return {"ok": True, "already_tracked": False}

