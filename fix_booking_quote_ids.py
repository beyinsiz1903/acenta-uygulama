#!/usr/bin/env python3
"""
Add quote_id to seed bookings to make them visible in ops endpoint
"""

import asyncio
import sys

# Add backend to path for imports
sys.path.append('/app/backend')
from app.db import get_db


async def add_quote_ids_to_seed_bookings():
    """Add quote_id to seed bookings so they appear in ops/bookings endpoint"""
    db = await get_db()
    
    # Update seed bookings to have quote_id
    result = await db.bookings.update_many(
        {"booking_id": {"$in": ["BKG-SEED-LINKED", "BKG-SEED-UNLINKED"]}},
        {"$set": {"quote_id": "quote_seed_test"}}
    )
    
    print(f"Updated {result.modified_count} bookings to have quote_id")
    
    # Verify the fix
    linked_booking = await db.bookings.find_one({"booking_id": "BKG-SEED-LINKED"})
    unlinked_booking = await db.bookings.find_one({"booking_id": "BKG-SEED-UNLINKED"})
    
    if linked_booking:
        print(f"BKG-SEED-LINKED quote_id: {linked_booking.get('quote_id')}")
    if unlinked_booking:
        print(f"BKG-SEED-UNLINKED quote_id: {unlinked_booking.get('quote_id')}")


async def main():
    await add_quote_ids_to_seed_bookings()


if __name__ == "__main__":
    asyncio.run(main())