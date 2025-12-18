from __future__ import annotations

from datetime import datetime, date
from typing import Any

from app.db import get_db


ACTIVE_BOOKING_STATUSES = ["confirmed", "guaranteed", "checked_in"]
ACTIVE_BLOCK_STATUSES = ["active"]
BLOCK_TYPES = ["out_of_order", "out_of_service", "maintenance"]


def parse_date(date_str: str) -> date:
    """Parse YYYY-MM-DD to date object"""
    return datetime.fromisoformat(date_str).date()


async def compute_availability(
    hotel_id: str,
    check_in: str,
    check_out: str,
    organization_id: str,
) -> dict[str, Any]:
    """
    FAZ-2.2.1: Compute real availability from rooms + bookings + blocks
    
    Returns:
    {
        "room_type": {
            "total_rooms": int,
            "available_rooms": int,
            "occupied_room_ids": [...]
        }
    }
    """
    db = await get_db()
    
    # Parse dates (checkout exclusive)
    search_check_in = parse_date(check_in)
    search_check_out = parse_date(check_out)
    
    # 1) Fetch all active rooms for hotel
    rooms = await db.rooms.find({
        "tenant_id": hotel_id,
        "organization_id": organization_id,
        "active": True,
    }).to_list(1000)
    
    if not rooms:
        return {}
    
    # Group by room_type
    rooms_by_type: dict[str, list] = {}
    room_by_id: dict[str, dict] = {}
    
    for room in rooms:
        room_id = str(room["_id"])
        room_type = room.get("room_type", "standard")
        
        room_by_id[room_id] = room
        if room_type not in rooms_by_type:
            rooms_by_type[room_type] = []
        rooms_by_type[room_type].append(room)
    
    # 2) Fetch overlapping bookings
    # Overlap: booking.check_in < search_check_out AND booking.check_out > search_check_in
    bookings = await db.bookings.find({
        "tenant_id": hotel_id,
        "organization_id": organization_id,
        "status": {"$in": ACTIVE_BOOKING_STATUSES},
    }).to_list(5000)
    
    # Filter overlapping bookings
    overlapping_bookings = []
    for booking in bookings:
        booking_check_in = parse_date(booking.get("check_in") or booking.get("start_date", ""))
        booking_check_out = parse_date(booking.get("check_out") or booking.get("end_date", ""))
        
        # Overlap check
        if booking_check_in < search_check_out and booking_check_out > search_check_in:
            overlapping_bookings.append(booking)
    
    # 3) Fetch overlapping blocks
    blocks = await db.room_blocks.find({
        "tenant_id": hotel_id,
        "organization_id": organization_id,
        "status": {"$in": ACTIVE_BLOCK_STATUSES},
        "type": {"$in": BLOCK_TYPES},
    }).to_list(1000)
    
    overlapping_blocks = []
    for block in blocks:
        block_start = parse_date(block.get("start_date", ""))
        block_end = block.get("end_date")
        
        if block_end:
            block_end_date = parse_date(block_end)
            # Overlap check
            if block_start < search_check_out and block_end_date > search_check_in:
                overlapping_blocks.append(block)
        else:
            # Open-ended block
            if block_start < search_check_out:
                overlapping_blocks.append(block)
    
    # 4) Map bookings + blocks to room_type
    occupied_by_type: dict[str, set] = {}
    blocked_by_type: dict[str, set] = {}
    
    for booking in overlapping_bookings:
        room_id = str(booking.get("room_id", ""))
        if room_id and room_id in room_by_id:
            room = room_by_id[room_id]
            room_type = room.get("room_type", "standard")
            
            if room_type not in occupied_by_type:
                occupied_by_type[room_type] = set()
            occupied_by_type[room_type].add(room_id)
    
    for block in overlapping_blocks:
        room_id = str(block.get("room_id", ""))
        if room_id and room_id in room_by_id:
            room = room_by_id[room_id]
            room_type = room.get("room_type", "standard")
            
            if room_type not in blocked_by_type:
                blocked_by_type[room_type] = set()
            blocked_by_type[room_type].add(room_id)
    
    # 5) Calculate availability per room_type
    availability: dict[str, Any] = {}
    
    for room_type, room_list in rooms_by_type.items():
        total_count = len(room_list)
        
        # Union of occupied + blocked (no double count)
        unavailable = occupied_by_type.get(room_type, set()) | blocked_by_type.get(room_type, set())
        
        available_count = max(0, total_count - len(unavailable))
        
        # Calculate average base_price
        prices = [r.get("base_price", 0) for r in room_list if r.get("base_price")]
        avg_price = round(sum(prices) / len(prices), 2) if prices else 0.0
        
        availability[room_type] = {
            "total_rooms": total_count,
            "available_rooms": available_count,
            "occupied_room_ids": list(occupied_by_type.get(room_type, set())),
            "blocked_room_ids": list(blocked_by_type.get(room_type, set())),
            "avg_base_price": avg_price,
        }
    
    return availability
