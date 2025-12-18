from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc, now_utc

router = APIRouter(prefix="/api/agency/bookings", tags=["agency-bookings"])


class GuestInfoIn(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None


class BookingDraftCreateIn(BaseModel):
    search_id: str
    hotel_id: str
    room_type_id: str
    rate_plan_id: str
    guest: GuestInfoIn
    special_requests: Optional[str] = None
    # Stay and occupancy snapshot (from search context)
    check_in: str
    check_out: str
    nights: int
    adults: int
    children: int = 0


class BookingConfirmIn(BaseModel):
    draft_id: str


@router.post("/draft", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def create_booking_draft(payload: BookingDraftCreateIn, user=Depends(get_current_user)):
    """
    FAZ-3.0: Create booking draft with TTL
    FAZ-3.2: Added 15-minute expiration
    """
    db = await get_db()
    agency_id = user.get("agency_id")
    
    if not agency_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_AGENCY")
    
    # Validate hotel link
    link = await db.agency_hotel_links.find_one({
        "organization_id": user["organization_id"],
        "agency_id": agency_id,
        "hotel_id": payload.hotel_id,
        "active": True,
    })
    
    if not link:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_HOTEL")
    
    # Get hotel
    hotel = await db.hotels.find_one({
        "organization_id": user["organization_id"],
        "_id": payload.hotel_id,
    })
    
    if not hotel:
        raise HTTPException(status_code=404, detail="HOTEL_NOT_FOUND")
    
    draft_id = f"draft_{uuid.uuid4().hex[:16]}"
    
    # FAZ-3.2: Set 15-minute TTL (UTC aware)
    now = now_utc()
    expires_at = now + timedelta(minutes=15)
    
    # Calculate total price based on nights
    base_price_per_night = 2450.0 if payload.rate_plan_id == "rp_refundable" else 2100.0
    total_price = base_price_per_night * payload.nights
    
    # Mock rate snapshot
    mock_rate_snapshot = {
        "room_type_id": payload.room_type_id,
        "room_type_name": "Standart Oda" if payload.room_type_id == "rt_standard" else "Deluxe Oda",
        "rate_plan_id": payload.rate_plan_id,
        "rate_plan_name": "İade Edilebilir" if payload.rate_plan_id == "rp_refundable" else "İade Edilemez",
        "board": "RO",
        "price": {
            "currency": "TRY",
            "total": total_price,
            "per_night": base_price_per_night,
            "tax_included": True,
        },
        "cancellation": "FREE_CANCEL" if payload.rate_plan_id == "rp_refundable" else "NON_REFUNDABLE",
    }
    
    draft = {
        "_id": draft_id,
        "organization_id": user["organization_id"],
        "agency_id": agency_id,
        "search_id": payload.search_id,
        "hotel_id": payload.hotel_id,
        "hotel_name": hotel.get("name"),
        "status": "draft",
        "stay": {
            "check_in": payload.check_in,
            "check_out": payload.check_out,
            "nights": payload.nights,
        },
        "occupancy": {
            "adults": payload.adults,
            "children": payload.children,
        },
        "guest": payload.guest.model_dump(),
        "special_requests": payload.special_requests,
        "rate_snapshot": mock_rate_snapshot,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
        "expires_at": expires_at,  # FAZ-3.2: 15 min TTL
    }
    
    await db.booking_drafts.insert_one(draft)
    
    saved = await db.booking_drafts.find_one({"_id": draft_id})
    return serialize_doc(saved)


@router.get("/draft/{draft_id}", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def get_booking_draft(draft_id: str, user=Depends(get_current_user)):
    """
    Get booking draft details
    FAZ-3.2: Check expiration
    """
    db = await get_db()
    agency_id = user.get("agency_id")
    
    # FAZ-3.2: Check expiration BEFORE not-found check
    draft = await db.booking_drafts.find_one({
        "organization_id": user["organization_id"],
        "agency_id": agency_id,
        "_id": draft_id,
    })
    
    if not draft:
        raise HTTPException(status_code=404, detail="DRAFT_NOT_FOUND")
    
    # FAZ-3.2: Check expiration (normalize timezone)
    if draft.get("expires_at"):
        expires_at = draft["expires_at"]
        now = now_utc()
        
        # Normalize timezone-naive datetimes from MongoDB
        if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if now > expires_at:
            raise HTTPException(status_code=410, detail="DRAFT_EXPIRED")
    
    return serialize_doc(draft)


@router.post("/confirm", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def confirm_booking(payload: BookingConfirmIn, user=Depends(get_current_user)):
    """
    FAZ-3.1: Confirm booking draft
    FAZ-3.2: Check expiration + price recheck
    Idempotent: returns same booking if already confirmed
    """
    db = await get_db()
    agency_id = user.get("agency_id")
    
    if not agency_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_AGENCY")
    
    # Get draft
    draft = await db.booking_drafts.find_one({
        "organization_id": user["organization_id"],
        "agency_id": agency_id,
        "_id": payload.draft_id,
    })
    
    if not draft:
        raise HTTPException(status_code=404, detail="DRAFT_NOT_FOUND")
    
    # FAZ-3.2: Check expiration (normalize timezone)
    if draft.get("expires_at"):
        expires_at = draft["expires_at"]
        now = now_utc()
        
        # Normalize timezone-naive datetimes from MongoDB
        if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if now > expires_at:
            raise HTTPException(status_code=410, detail="DRAFT_EXPIRED")
    
    # Check if cancelled
    if draft.get("status") == "cancelled":
        raise HTTPException(status_code=409, detail="DRAFT_CANCELLED")
    
    # Idempotency: if already confirmed, return existing booking
    if draft.get("status") == "confirmed" and draft.get("confirmed_booking_id"):
        existing_booking = await db.bookings.find_one({"_id": draft["confirmed_booking_id"]})
        if existing_booking:
            return serialize_doc(existing_booking)
    
    # FAZ-3.2: Price recheck
    # Re-fetch current price from search (mock simulation)
    draft_total = draft.get("rate_snapshot", {}).get("price", {}).get("total", 0)
    
    # Mock: Simulate price recheck by adding 5% variance randomly
    # In real implementation, call /search endpoint with same params
    import random
    price_variance = random.choice([0, 0, 0, 0.05])  # 20% chance of 5% increase
    
    if price_variance > 0:
        new_total = round(draft_total * (1 + price_variance), 2)
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PRICE_CHANGED",
                "old_total": draft_total,
                "new_total": new_total,
                "currency": draft.get("rate_snapshot", {}).get("price", {}).get("currency", "TRY"),
            },
        )
    
    # Create confirmed booking
    booking_id = f"bkg_{uuid.uuid4().hex[:16]}"
    confirmed_at = now_utc()
    
    booking = {
        "_id": booking_id,
        "organization_id": user["organization_id"],
        "agency_id": agency_id,
        "draft_id": payload.draft_id,
        "search_id": draft.get("search_id"),
        "hotel_id": draft["hotel_id"],
        "hotel_name": draft.get("hotel_name"),
        "status": "confirmed",
        "stay": draft.get("stay"),
        "occupancy": draft.get("occupancy"),
        "guest": draft.get("guest"),
        "special_requests": draft.get("special_requests"),
        "rate_snapshot": draft.get("rate_snapshot"),
        "confirmed_at": confirmed_at,
        "created_at": confirmed_at,
        "updated_at": confirmed_at,
        "created_by": user.get("email"),
        "payment_status": "pending",  # pending|paid|partial
    }
    
    await db.bookings.insert_one(booking)
    
    # Update draft status
    await db.booking_drafts.update_one(
        {"_id": payload.draft_id},
        {
            "$set": {
                "status": "confirmed",
                "confirmed_booking_id": booking_id,
                "updated_at": confirmed_at,
            }
        },
    )
    
    saved = await db.bookings.find_one({"_id": booking_id})
    return serialize_doc(saved)


@router.delete("/draft/{draft_id}", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def cancel_booking_draft(draft_id: str, user=Depends(get_current_user)):
    """
    FAZ-3.1: Cancel booking draft
    Sets status to cancelled (does not delete)
    """
    db = await get_db()
    agency_id = user.get("agency_id")
    
    if not agency_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_AGENCY")
    
    # Get draft
    draft = await db.booking_drafts.find_one({
        "organization_id": user["organization_id"],
        "agency_id": agency_id,
        "_id": draft_id,
    })
    
    if not draft:
        raise HTTPException(status_code=404, detail="DRAFT_NOT_FOUND")
    
    # Cannot cancel confirmed draft
    if draft.get("status") == "confirmed":
        raise HTTPException(status_code=409, detail="DRAFT_ALREADY_CONFIRMED")
    
    # Update status to cancelled
    await db.booking_drafts.update_one(
        {"_id": draft_id},
        {
            "$set": {
                "status": "cancelled",
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    
    saved = await db.booking_drafts.find_one({"_id": draft_id})
    return serialize_doc(saved)


@router.get("/{booking_id}", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def get_booking(booking_id: str, user=Depends(get_current_user)):
    """
    FAZ-3.2: Get confirmed booking details
    """
    db = await get_db()
    agency_id = user.get("agency_id")
    
    booking = await db.bookings.find_one({
        "organization_id": user["organization_id"],
        "agency_id": agency_id,
        "_id": booking_id,
    })
    
    if not booking:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")
    
    return serialize_doc(booking)
