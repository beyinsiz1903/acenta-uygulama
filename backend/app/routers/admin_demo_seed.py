from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db


router = APIRouter(prefix="/api/admin/demo", tags=["admin-demo"])


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# -------- Request/Response Models --------

class SeedBookingsRequest(BaseModel):
    count: int = 20
    days_back: int = 14
    wipe_existing_seed: bool = True


class SeedBookingsResponse(BaseModel):
    ok: bool
    seed_tag: str
    inserted: int
    wiped: int = 0


# -------- Helper: Generate Random Booking --------

def random_date_in_range(start: datetime, end: datetime) -> datetime:
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def generate_demo_booking(
    org_id: str,
    hotel_ids: list[str],
    hotel_names: dict[str, str],
    created_at: datetime,
    status: str,
) -> dict:
    """Generate a single demo booking document"""
    
    booking_id = str(uuid.uuid4())
    hotel_id = random.choice(hotel_ids) if hotel_ids else "demo-hotel-1"
    hotel_name = hotel_names.get(hotel_id, "Demo Hotel")
    
    # Guest info
    guest_first = random.choice(["Ahmet", "Mehmet", "Ayşe", "Fatma", "Ali", "Zeynep"])
    guest_last = random.choice(["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Aydın"])
    
    # Check-in/out dates (future dates, 3-60 days from now)
    days_ahead = random.randint(3, 60)
    checkin = now_utc() + timedelta(days=days_ahead)
    checkout = checkin + timedelta(days=random.randint(1, 7))
    
    # Room details
    room_types = ["Standard", "Deluxe", "Suite", "Family Room"]
    room_type = random.choice(room_types)
    
    adults = random.randint(1, 4)
    children = random.randint(0, 2)
    
    # Pricing
    room_rate = random.randint(500, 3000)
    nights = (checkout - checkin).days
    total = room_rate * nights
    commission_pct = random.choice([10, 12, 15, 18, 20])
    commission = (total * commission_pct) / 100
    net = total - commission
    
    # Note (30-40% should have notes)
    has_note = random.random() < 0.35
    note_text = random.choice([
        "Geç giriş isteniyor (20:00 sonrası)",
        "Bebek beşiği gerekli",
        "Yüksek katta oda tercihi",
        "Balkonlu oda lütfen",
        "Sessiz oda isteniyor",
        "Havuz manzaralı",
    ]) if has_note else None
    
    # Base booking document
    booking = {
        "_id": booking_id,
        "organization_id": org_id,
        "hotel_id": hotel_id,
        "hotel_name": hotel_name,
        "status": status,
        "created_at": created_at,
        "created_by": "demo@seed.test",
        "updated_at": created_at,
        "updated_by": "demo@seed.test",
        
        # Guest
        "guest_first_name": guest_first,
        "guest_last_name": guest_last,
        "guest_email": f"{guest_first.lower()}.{guest_last.lower()}@example.com",
        "guest_phone": f"+90 5{random.randint(300000000, 599999999)}",
        
        # Stay
        "checkin": checkin,
        "checkout": checkout,
        "room_type": room_type,
        "adults": adults,
        "children": children,
        
        # Pricing
        "room_rate": room_rate,
        "total": total,
        "commission_pct": commission_pct,
        "commission": commission,
        "net": net,
        "currency": "TRY",
        
        # Notes (for metrics)
        "note_to_hotel": note_text if has_note else "",
        "hotel_note": "",
        "guest_note": "",
        "special_requests": "",
        
        # Metadata
        "source": "demo_seed",
        "demo_seed_tag": "v1",
        "code": f"DEMO-{random.randint(10000, 99999)}",
    }
    
    # Confirmed bookings need confirmed_at
    if status == "confirmed":
        # Approval time between 10 minutes and 24 hours
        approval_seconds = random.randint(600, 86400)
        booking["confirmed_at"] = created_at + timedelta(seconds=approval_seconds)
    
    return booking


# -------- Endpoint --------

@router.post("/seed-bookings", response_model=SeedBookingsResponse, dependencies=[Depends(require_roles(["super_admin"]))])
async def seed_demo_bookings(
    payload: SeedBookingsRequest,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Generate demo booking data for testing dashboard metrics.
    Only accessible by super_admin.
    
    Distribution:
    - 45% pending
    - 45% confirmed
    - 10% cancelled
    """
    
    org_id = user.get("organization_id")
    count = min(max(payload.count, 1), 100)  # Cap at 100
    days_back = min(max(payload.days_back, 1), 365)
    
    # Wipe existing seed data if requested
    wiped = 0
    if payload.wipe_existing_seed:
        result = await db.bookings.delete_many({
            "organization_id": org_id,
            "source": "demo_seed",
        })
        wiped = result.deleted_count
    
    # Get available hotels
    hotels = await db.hotels.find({"organization_id": org_id}).to_list(length=None)
    hotel_ids = [h.get("_id") for h in hotels if h.get("_id")]
    hotel_names = {h.get("_id"): h.get("name", "Demo Hotel") for h in hotels}
    
    # Fallback if no hotels exist
    if not hotel_ids:
        hotel_ids = ["demo-hotel-1", "demo-hotel-2"]
        hotel_names = {"demo-hotel-1": "Demo Hotel 1", "demo-hotel-2": "Demo Hotel 2"}
    
    # Generate bookings
    cutoff = now_utc() - timedelta(days=days_back)
    bookings_to_insert = []
    
    # Status distribution
    pending_count = int(count * 0.45)
    confirmed_count = int(count * 0.45)
    cancelled_count = count - pending_count - confirmed_count
    
    statuses = (
        ["pending"] * pending_count +
        ["confirmed"] * confirmed_count +
        ["cancelled"] * cancelled_count
    )
    random.shuffle(statuses)
    
    for status in statuses:
        created_at = random_date_in_range(cutoff, now_utc())
        booking = generate_demo_booking(org_id, hotel_ids, hotel_names, created_at, status)
        bookings_to_insert.append(booking)
    
    # Insert all bookings
    if bookings_to_insert:
        await db.bookings.insert_many(bookings_to_insert)
    
    return SeedBookingsResponse(
        ok=True,
        seed_tag="v1",
        inserted=len(bookings_to_insert),
        wiped=wiped,
    )
