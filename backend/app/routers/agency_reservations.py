"""Quick Reservation API — Takvimden Hızlı Rezervasyon.

Allows agency users to create reservations directly from the calendar view.
After creation, triggers sheet write-back and allotment decrement.

Endpoints:
  POST /api/agency/reservations/quick  — Create a quick reservation
  GET  /api/agency/reservations        — List reservations for the agency
  POST /api/agency/reservations/{id}/cancel — Cancel a reservation
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agency/reservations", tags=["agency_reservations"])

AgencyDep = Depends(require_roles(["agency_admin", "agency_agent", "admin", "super_admin"]))


def _now():
    return datetime.now(timezone.utc)


class QuickReservationIn(BaseModel):
    hotel_id: str
    room_type: str
    check_in: str   # YYYY-MM-DD
    check_out: str  # YYYY-MM-DD
    guest_name: str
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None
    pax: int = 1
    notes: Optional[str] = None


@router.post("/quick", dependencies=[AgencyDep])
async def create_quick_reservation(
    payload: QuickReservationIn,
    user=Depends(get_current_user),
):
    """Create a quick reservation from the calendar view."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id") or org_id

    if not agency_id:
        raise HTTPException(status_code=403, detail="Acenta bulunamadı")

    # Verify hotel access
    link = await db.agency_hotel_links.find_one({
        "organization_id": org_id,
        "agency_id": agency_id,
        "hotel_id": payload.hotel_id,
        "active": True,
    })
    if not link:
        raise HTTPException(status_code=403, detail="Bu otele erişiminiz yok")

    # Get hotel info
    hotel = await db.hotels.find_one({"_id": payload.hotel_id})
    hotel_name = (hotel or {}).get("name", "")

    # Get agency name
    agency = await db.agencies.find_one({"_id": agency_id})
    agency_name = (agency or {}).get("name", "")

    # Check dates
    try:
        ci = datetime.strptime(payload.check_in, "%Y-%m-%d")
        co = datetime.strptime(payload.check_out, "%Y-%m-%d")
        if co <= ci:
            raise HTTPException(status_code=400, detail="Çıkış tarihi giriş tarihinden sonra olmalı")
        nights = (co - ci).days
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz tarih formatı (YYYY-MM-DD)")

    # Get price from inventory for the date and room type
    tenant_ids = list({t for t in [tenant_id, org_id] if t})
    snapshots = await db.hotel_inventory_snapshots.find({
        "tenant_id": {"$in": tenant_ids},
        "hotel_id": payload.hotel_id,
        "room_type": payload.room_type,
        "date": {"$gte": payload.check_in, "$lt": payload.check_out},
    }).to_list(365)

    # Calculate total price and check availability
    total_price = 0.0
    unavailable_dates = []
    for snap in snapshots:
        if snap.get("stop_sale"):
            unavailable_dates.append(snap["date"])
        elif (snap.get("allotment") or 0) <= 0:
            unavailable_dates.append(snap["date"])
        total_price += float(snap.get("price") or 0)

    if unavailable_dates:
        raise HTTPException(
            status_code=409,
            detail=f"Şu tarihlerde müsaitlik yok: {', '.join(unavailable_dates[:5])}"
        )

    reservation_id = str(uuid.uuid4())
    now = _now()

    # Generate unique PNR and idempotency_key for the reservation (required by unique indexes)
    pnr = f"QR-{uuid.uuid4().hex[:8].upper()}"
    idempotency_key = f"quick-{reservation_id}"

    reservation = {
        "_id": reservation_id,
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "agency_id": agency_id,
        "agency_name": agency_name,
        "hotel_id": payload.hotel_id,
        "hotel_name": hotel_name,
        "room_type": payload.room_type,
        "check_in": payload.check_in,
        "check_out": payload.check_out,
        "nights": nights,
        "guest_name": payload.guest_name,
        "guest_phone": payload.guest_phone,
        "guest_email": payload.guest_email,
        "pax": payload.pax,
        "notes": payload.notes,
        "total_price": round(total_price, 2),
        "currency": "TRY",
        "status": "confirmed",
        "source": "calendar_quick",
        "pnr": pnr,  # Unique PNR for reservation index
        "idempotency_key": idempotency_key,  # Unique key for idempotency index
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
    }

    await db.reservations.insert_one(reservation)

    # Trigger write-back to Google Sheet + allotment decrement
    writeback_job_id = None
    allotment_result = None
    try:
        from app.services.sheet_writeback_service import (
            on_reservation_created,
            decrement_allotment_for_reservation,
        )

        # Use org_id for tenant lookup (matches how sheets stores data)
        writeback_job_id = await on_reservation_created(
            db, org_id, org_id, {
                "_id": reservation_id,
                "hotel_id": payload.hotel_id,
                "customer": {"name": payload.guest_name},
                "start_date": payload.check_in,
                "end_date": payload.check_out,
                "pax": payload.pax,
                "room_type": payload.room_type,
                "total_price": total_price,
                "currency": "TRY",
                "status": "confirmed",
                "channel": "calendar_quick",
                "created_at": str(now),
            }
        )

        # Decrement allotment directly (using org_id as tenant for matching snapshots)
        allotment_result = await decrement_allotment_for_reservation(
            db, org_id, payload.hotel_id, {
                "room_type": payload.room_type,
                "start_date": payload.check_in,
                "end_date": payload.check_out,
            }
        )
    except Exception as e:
        logger.warning("Write-back trigger failed (reservation saved): %s", e)

    return {
        "reservation_id": reservation_id,
        "hotel_name": hotel_name,
        "room_type": payload.room_type,
        "guest_name": payload.guest_name,
        "check_in": payload.check_in,
        "check_out": payload.check_out,
        "nights": nights,
        "total_price": round(total_price, 2),
        "currency": "TRY",
        "status": "confirmed",
        "writeback_job_id": writeback_job_id,
        "allotment_updated": allotment_result is not None,
        "created_at": now.isoformat(),
    }


@router.get("", dependencies=[AgencyDep])
async def list_agency_reservations(
    hotel_id: Optional[str] = None,
    user=Depends(get_current_user),
):
    """List reservations for the agency."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        return {"items": [], "total": 0}

    query = {
        "organization_id": org_id,
        "agency_id": agency_id,
    }
    if hotel_id:
        query["hotel_id"] = hotel_id

    docs = await db.reservations.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(200)

    # Also include id field for each
    items = []
    for doc in docs:
        items.append(doc)

    return {"items": items, "total": len(items)}


@router.post("/{reservation_id}/cancel", dependencies=[AgencyDep])
async def cancel_reservation(
    reservation_id: str,
    user=Depends(get_current_user),
):
    """Cancel a reservation and restore allotment."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    reservation = await db.reservations.find_one({
        "_id": reservation_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })

    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadı")

    if reservation.get("status") == "cancelled":
        raise HTTPException(status_code=409, detail="Rezervasyon zaten iptal edilmiş")

    await db.reservations.update_one(
        {"_id": reservation_id},
        {"$set": {"status": "cancelled", "updated_at": _now(), "cancelled_by": user.get("email")}},
    )

    # Restore allotment
    try:
        from app.services.sheet_writeback_service import (
            on_reservation_cancelled,
            restore_allotment_for_cancellation,
        )

        await on_reservation_cancelled(
            db, org_id, org_id, {
                "_id": reservation_id,
                "hotel_id": reservation["hotel_id"],
                "start_date": reservation["check_in"],
                "end_date": reservation["check_out"],
                "pax": reservation.get("pax", 1),
                "room_type": reservation.get("room_type", ""),
                "currency": reservation.get("currency", "TRY"),
                "channel": reservation.get("source", ""),
            }
        )

        await restore_allotment_for_cancellation(
            db, org_id, reservation["hotel_id"], {
                "room_type": reservation.get("room_type", ""),
                "start_date": reservation["check_in"],
                "end_date": reservation["check_out"],
            }
        )
    except Exception as e:
        logger.warning("Cancel write-back failed: %s", e)

    return {"status": "cancelled", "reservation_id": reservation_id}
