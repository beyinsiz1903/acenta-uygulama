from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db


router = APIRouter(prefix="/api/admin/insights", tags=["admin-insights"])


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# -------- Response Models --------

class QueueBooking(BaseModel):
    booking_id: str
    hotel_id: str
    hotel_name: Optional[str] = None
    created_at: datetime
    age_hours: float
    status: str
    has_note: bool


class QueuesResponse(BaseModel):
    period_days: int
    slow_hours: int
    slow_pending: List[QueueBooking] = []
    noted_pending: List[QueueBooking] = []


class FunnelResponse(BaseModel):
    period_days: int
    total: int
    pending: int
    confirmed: int
    cancelled: int
    conversion_pct: float


# -------- Helper Functions --------

def has_note_fields(doc: dict) -> bool:
    """Check if booking has any note field with content"""
    note_fields = ["note_to_hotel", "hotel_note", "guest_note", "special_requests"]
    for field in note_fields:
        value = doc.get(field)
        if value and isinstance(value, str) and value.strip():
            return True
    return False


def calculate_age_hours(created_at: datetime) -> float:
    """Calculate age in hours from created_at to now"""
    if not created_at:
        return 0.0
    delta = now_utc() - created_at
    return delta.total_seconds() / 3600.0


# -------- Endpoints --------

@router.get("/queues", response_model=QueuesResponse, dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def get_action_queues(
    days: int = Query(30, ge=1, le=365),
    slow_hours: int = Query(24, ge=1, le=720),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Get operational action queues:
    - slow_pending: pending bookings older than slow_hours
    - noted_pending: pending bookings with notes
    """
    
    org_id = user.get("organization_id")
    cutoff_date = now_utc() - timedelta(days=days)
    slow_cutoff = now_utc() - timedelta(hours=slow_hours)
    
    # Get all pending bookings in period
    pending_bookings = await db.bookings.find({
        "organization_id": org_id,
        "status": "pending",
        "created_at": {"$gte": cutoff_date}
    }).sort("created_at", 1).to_list(length=limit * 2)
    
    # Get hotel names
    hotel_ids = list(set(b.get("hotel_id") for b in pending_bookings if b.get("hotel_id")))
    hotels = await db.hotels.find({
        "organization_id": org_id,
        "_id": {"$in": hotel_ids}
    }).to_list(length=None)
    hotel_name_map = {h.get("_id"): h.get("name", "Unknown Hotel") for h in hotels}
    
    # Process queues
    slow_pending = []
    noted_pending = []
    
    for booking in pending_bookings:
        booking_id = booking.get("_id")
        hotel_id = booking.get("hotel_id")
        created_at = booking.get("created_at")
        
        if not booking_id or not created_at:
            continue
        
        age_hours = calculate_age_hours(created_at)
        has_note = has_note_fields(booking)
        
        queue_item = QueueBooking(
            booking_id=str(booking_id),
            hotel_id=str(hotel_id) if hotel_id else "",
            hotel_name=hotel_name_map.get(hotel_id),
            created_at=created_at,
            age_hours=round(age_hours, 1),
            status="pending",
            has_note=has_note,
        )
        
        # Slow pending (older than slow_hours)
        if created_at < slow_cutoff:
            slow_pending.append(queue_item)
        
        # Noted pending
        if has_note:
            noted_pending.append(queue_item)
    
    # Limit results
    slow_pending = slow_pending[:limit]
    noted_pending = noted_pending[:limit]
    
    return QueuesResponse(
        period_days=days,
        slow_hours=slow_hours,
        slow_pending=slow_pending,
        noted_pending=noted_pending,
    )


@router.get("/funnel", response_model=FunnelResponse, dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def get_conversion_funnel(
    days: int = Query(30, ge=1, le=365),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Get conversion funnel metrics:
    - Total bookings created in period
    - Breakdown by status
    - Conversion percentage (confirmed / total)
    """
    
    org_id = user.get("organization_id")
    cutoff_date = now_utc() - timedelta(days=days)
    
    # Aggregate by status
    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "created_at": {"$gte": cutoff_date}
        }},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    results = await db.bookings.aggregate(pipeline).to_list(length=None)
    
    # Parse results
    counts = {"pending": 0, "confirmed": 0, "cancelled": 0}
    for r in results:
        status = (r.get("_id") or "").lower()
        count = int(r.get("count") or 0)
        if status in counts:
            counts[status] = count
    
    total = sum(counts.values())
    conversion_pct = 0.0
    if total > 0:
        conversion_pct = round((counts["confirmed"] / total) * 100.0, 1)
    
    return FunnelResponse(
        period_days=days,
        total=total,
        pending=counts["pending"],
        confirmed=counts["confirmed"],
        cancelled=counts["cancelled"],
        conversion_pct=conversion_pct,
    )
