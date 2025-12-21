"""
FAZ-2 Migration: Move drafts from bookings to booking_drafts collection
Run once before deploying FAZ-2 changes
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "test_database")

async def migrate_drafts():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("=" * 80)
    print("🔄 FAZ-2 MIGRATION: bookings → booking_drafts")
    print("=" * 80)
    
    # Find all drafts in bookings collection
    drafts = await db.bookings.find({"status": "draft"}).to_list(1000)
    print(f"\n✅ Found {len(drafts)} drafts in bookings collection")
    
    if len(drafts) == 0:
        print("✅ No drafts to migrate")
        client.close()
        return
    
    # Move to booking_drafts
    migrated = 0
    for draft in drafts:
        # Check if already exists in booking_drafts
        existing = await db.booking_drafts.find_one({"_id": draft["_id"]})
        if existing:
            print(f"⚠️  Draft {draft['_id']} already in booking_drafts, skipping")
            continue
        
        # Insert into booking_drafts
        await db.booking_drafts.insert_one(draft)
        
        # Delete from bookings
        await db.bookings.delete_one({"_id": draft["_id"]})
        
        migrated += 1
        print(f"✓ Migrated draft {draft['_id']}")
    
    print(f"\n✅ Migration complete: {migrated} drafts moved")
    print("=" * 80)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_drafts())
