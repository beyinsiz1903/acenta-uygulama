#!/usr/bin/env python3
"""
Debug script to check what's actually stored in the database
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

async def debug_db():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("🔍 Checking database for C101 and C102 rooms...")
    
    # Find rooms with room numbers C101 and C102
    rooms = await db.rooms.find(
        {"room_number": {"$in": ["C101", "C102"]}},
        {"_id": 0}
    ).to_list(10)
    
    print(f"📊 Found {len(rooms)} rooms")
    
    for room in rooms:
        print(f"\n🏨 Room from DB: {room.get('room_number')}")
        print(f"   Raw document: {room}")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(debug_db())