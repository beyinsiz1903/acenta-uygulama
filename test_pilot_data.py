"""
FAZ-2.0.1 Test Data Generator
Creates realistic pilot data for last 7 days to validate KPI calculations
"""
import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "test_database")

async def generate_test_data():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("=" * 80)
    print("🧪 PILOT TEST DATA GENERATOR")
    print("=" * 80)
    
    # Get organization, agencies, hotels
    org = await db.organizations.find_one()
    if not org:
        print("❌ No organization found")
        return
    
    org_id = str(org["_id"])
    print(f"\n✅ Organization: {org_id}")
    
    agencies = await db.agencies.find({"organization_id": org_id}).to_list(10)
    hotels = await db.hotels.find({"organization_id": org_id}).to_list(10)
    
    if not agencies or not hotels:
        print("❌ No agencies or hotels found")
        return
    
    print(f"✅ Found {len(agencies)} agencies, {len(hotels)} hotels")
    
    agency1 = agencies[0]
    hotel1 = hotels[0]
    
    # Create test bookings for last 7 days
    now = datetime.utcnow()
    bookings_created = []
    
    print("\n📝 Creating 10 test bookings...")
    
    for i in range(10):
        days_ago = 6 - (i % 7)  # Spread across last 7 days
        created_at = now - timedelta(days=days_ago, hours=i, minutes=i*3)
        updated_at = created_at + timedelta(minutes=15 + i*2)  # Approval time varies
        
        # Status distribution: 6 confirmed, 4 cancelled
        status = "confirmed" if i < 6 else "cancelled"
        
        booking = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "agency_id": str(agency1["_id"]),
            "hotel_id": str(hotel1["_id"]),
            "hotel_name": hotel1.get("name", "Demo Hotel"),
            "status": status,
            "guest": {
                "full_name": f"Test Guest {i+1}",
                "email": f"guest{i+1}@test.com"
            },
            "stay": {
                "check_in": (now + timedelta(days=30+i)).strftime("%Y-%m-%d"),
                "check_out": (now + timedelta(days=32+i)).strftime("%Y-%m-%d"),
                "nights": 2
            },
            "occupancy": {"adults": 2, "children": 0},
            "rate_snapshot": {
                "price": {
                    "total": 2000.0,
                    "currency": "TRY",
                    "per_night": 1000.0
                }
            },
            "created_at": created_at,
            "updated_at": updated_at
        }
        
        await db.bookings.insert_one(booking)
        bookings_created.append(booking)
        print(f"   ✓ Booking {i+1}: {status} (created {days_ago} days ago)")
    
    print(f"\n✅ Created {len(bookings_created)} bookings")
    
    # Create WhatsApp click events for 5 bookings (50% engagement)
    print("\n📱 Creating WhatsApp click events...")
    
    whatsapp_events = []
    for i in range(5):
        booking = bookings_created[i]
        event = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "event_type": "booking.whatsapp_clicked",
            "booking_id": booking["_id"],
            "hotel_id": booking["hotel_id"],
            "agency_id": booking["agency_id"],
            "payload": {
                "actor_email": "agency1@demo.test"
            },
            "delivered": False,
            "created_at": booking["updated_at"] + timedelta(minutes=5)
        }
        await db.booking_events.insert_one(event)
        whatsapp_events.append(event)
        print(f"   ✓ WhatsApp click for booking {i+1}")
    
    print(f"\n✅ Created {len(whatsapp_events)} WhatsApp click events")
    
    # Show summary
    print("\n" + "=" * 80)
    print("📊 TEST DATA SUMMARY")
    print("=" * 80)
    print(f"Total Bookings: 10")
    print(f"  - Confirmed: 6")
    print(f"  - Cancelled: 4")
    print(f"WhatsApp Clicks: 5")
    print(f"Date Range: Last 7 days")
    print("\n💡 Expected KPIs:")
    print(f"  - totalRequests: 10")
    print(f"  - confirmedBookings: 6")
    print(f"  - cancelledBookings: 4")
    print(f"  - whatsappClickedCount: 5")
    print(f"  - whatsappShareRate: 0.5 (5/10)")
    print(f"  - hotelPanelActionRate: 1.0 (10/10)")
    print(f"  - flowCompletionRate: 0.6 (6/10)")
    print("=" * 80)
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(generate_test_data())
