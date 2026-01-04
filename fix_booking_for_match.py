#!/usr/bin/env python3
"""
Fix booking to add hotel_id fields for match outcome testing
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_booking(booking_id, hotel_id, from_hotel_id):
    # Connect to MongoDB
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client.acenta_master
    
    # Update the booking to add hotel_id and from_hotel_id
    result = await db.agency_catalog_booking_requests.update_one(
        {"_id": booking_id},
        {"$set": {
            "hotel_id": hotel_id,
            "to_hotel_id": hotel_id,
            "from_hotel_id": from_hotel_id
        }}
    )
    
    print(f"Updated {result.modified_count} booking(s)")
    
    # Verify
    booking = await db.agency_catalog_booking_requests.find_one({"_id": booking_id})
    if booking:
        print(f"Booking now has:")
        print(f"  hotel_id: {booking.get('hotel_id')}")
        print(f"  to_hotel_id: {booking.get('to_hotel_id')}")
        print(f"  from_hotel_id: {booking.get('from_hotel_id')}")
    
    client.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python fix_booking_for_match.py <booking_id> <hotel_id> <from_hotel_id>")
        sys.exit(1)
    
    booking_id = sys.argv[1]
    hotel_id = sys.argv[2]
    from_hotel_id = sys.argv[3]
    
    asyncio.run(fix_booking(booking_id, hotel_id, from_hotel_id))
