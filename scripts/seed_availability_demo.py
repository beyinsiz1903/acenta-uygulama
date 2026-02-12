"""Seed demo data for agency availability feature."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

async def seed_availability_demo():
    import sys
    sys.path.insert(0, "/app/backend")
    from app.db import get_db
    from app.auth import hash_password

    db = await get_db()
    now = datetime.now(timezone.utc)
    org_id = "org_default"

    # Check org
    admin = await db.users.find_one({"email": "admin@acenta.test"})
    if admin:
        org_id = admin["organization_id"]
    print(f"Using org_id: {org_id}")

    # 1. Create agency
    agency_id = "agency-demo-001"
    existing_agency = await db.agencies.find_one({"_id": agency_id})
    if not existing_agency:
        await db.agencies.insert_one({
            "_id": agency_id,
            "organization_id": org_id,
            "name": "Demo Acenta",
            "contact_email": "agency1@acenta.test",
            "city": "Istanbul",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        })
        print("Created agency: Demo Acenta")
    else:
        print("Agency already exists")

    # 2. Create agency user
    existing_user = await db.users.find_one({"email": "agency1@acenta.test"})
    if not existing_user:
        await db.users.insert_one({
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "email": "agency1@acenta.test",
            "name": "Acenta Yönetici",
            "password_hash": hash_password("agency123"),
            "roles": ["agency_admin"],
            "agency_id": agency_id,
            "tenant_id": org_id,
            "created_at": now,
            "updated_at": now,
            "is_active": True,
        })
        print("Created agency user: agency1@acenta.test / agency123")
    else:
        print("Agency user already exists")
        # Make sure agency_id is set
        if not existing_user.get("agency_id"):
            await db.users.update_one(
                {"email": "agency1@acenta.test"},
                {"$set": {"agency_id": agency_id, "tenant_id": org_id}}
            )
            print("Updated agency_id on existing user")

    # 3. Create demo hotels
    hotels_data = [
        {"_id": "hotel-demo-001", "name": "Grand Palace Hotel", "city": "Antalya", "stars": 5, "active": True},
        {"_id": "hotel-demo-002", "name": "Blue Coast Resort", "city": "Bodrum", "stars": 4, "active": True},
        {"_id": "hotel-demo-003", "name": "Green Valley Inn", "city": "Fethiye", "stars": 3, "active": True},
    ]
    for h in hotels_data:
        existing = await db.hotels.find_one({"_id": h["_id"]})
        if not existing:
            await db.hotels.insert_one({
                **h,
                "organization_id": org_id,
                "description": f"{h['name']} - Premium otel deneyimi",
                "created_at": now,
                "updated_at": now,
            })
            print(f"Created hotel: {h['name']}")
        else:
            print(f"Hotel already exists: {h['name']}")

    # 4. Create agency-hotel links
    for h in hotels_data:
        existing_link = await db.agency_hotel_links.find_one({
            "organization_id": org_id,
            "agency_id": agency_id,
            "hotel_id": h["_id"],
        })
        if not existing_link:
            await db.agency_hotel_links.insert_one({
                "_id": str(uuid.uuid4()),
                "organization_id": org_id,
                "agency_id": agency_id,
                "hotel_id": h["_id"],
                "active": True,
                "commission_type": "percent",
                "commission_value": 10.0,
                "created_at": now,
                "updated_at": now,
            })
            print(f"Created link: agency -> {h['name']}")
        else:
            print(f"Link already exists for: {h['name']}")

    # 5. Create demo availability data (hotel_inventory_snapshots)
    room_types = {
        "hotel-demo-001": ["Standart Oda", "Deluxe Oda", "Suite"],
        "hotel-demo-002": ["Standart", "Deniz Manzaralı", "Aile Odası"],
        "hotel-demo-003": ["Ekonomik", "Standart Oda", "Superior"],
    }

    base_prices = {
        "hotel-demo-001": {"Standart Oda": 2500, "Deluxe Oda": 3800, "Suite": 6500},
        "hotel-demo-002": {"Standart": 1800, "Deniz Manzaralı": 2600, "Aile Odası": 3200},
        "hotel-demo-003": {"Ekonomik": 900, "Standart Oda": 1400, "Superior": 2100},
    }

    import random
    random.seed(42)

    tenant_id = org_id
    total_inserted = 0

    for hotel_id, types in room_types.items():
        for room_type in types:
            base_price = base_prices[hotel_id][room_type]
            for day_offset in range(21):  # 21 days
                date_str = (now + timedelta(days=day_offset)).strftime("%Y-%m-%d")

                # Skip weekends for some rooms to create variety
                day_of_week = (now + timedelta(days=day_offset)).weekday()
                is_weekend = day_of_week >= 5

                # Price variation: +20% weekends, random ±10%
                price = base_price * (1.2 if is_weekend else 1.0) * (0.9 + random.random() * 0.2)
                price = round(price, 0)

                # Allotment: 0-10, some dates sold out
                allotment = random.randint(0, 10)
                if random.random() < 0.1:
                    allotment = 0  # 10% chance sold out

                # Stop sale: some dates closed
                stop_sale = random.random() < 0.05  # 5% chance

                existing = await db.hotel_inventory_snapshots.find_one({
                    "tenant_id": tenant_id,
                    "hotel_id": hotel_id,
                    "date": date_str,
                    "room_type": room_type,
                })
                if not existing:
                    await db.hotel_inventory_snapshots.insert_one({
                        "_id": str(uuid.uuid4()),
                        "tenant_id": tenant_id,
                        "hotel_id": hotel_id,
                        "date": date_str,
                        "room_type": room_type,
                        "price": price,
                        "allotment": allotment,
                        "stop_sale": stop_sale,
                        "source": "sheet_sync",
                        "created_at": now,
                        "updated_at": now - timedelta(minutes=random.randint(5, 120)),
                    })
                    total_inserted += 1

    print(f"Created {total_inserted} inventory snapshots")

    # 6. Create some demo sheet connections
    for h in hotels_data:
        existing_conn = await db.hotel_portfolio_sources.find_one({
            "tenant_id": tenant_id,
            "hotel_id": h["_id"],
        })
        if not existing_conn:
            await db.hotel_portfolio_sources.insert_one({
                "_id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "organization_id": org_id,
                "hotel_id": h["_id"],
                "hotel_name": h["name"],
                "source_type": "google_sheets",
                "sheet_id": f"demo-sheet-{h['_id']}",
                "sheet_tab": "Sheet1",
                "sheet_title": f"{h['name']} Müsaitlik",
                "mapping": {},
                "sync_enabled": True,
                "sync_interval_minutes": 5,
                "last_sync_at": now - timedelta(minutes=3),
                "last_sync_status": "success",
                "last_error": None,
                "status": "active",
                "created_at": now - timedelta(days=7),
                "updated_at": now,
            })
            print(f"Created sheet connection for: {h['name']}")

    # 7. Create some demo sync runs
    for h in hotels_data:
        for i in range(3):
            run_time = now - timedelta(hours=i*2)
            await db.sheet_sync_runs.insert_one({
                "_id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "hotel_id": h["_id"],
                "connection_id": f"conn-{h['_id']}",
                "sheet_id": f"demo-sheet-{h['_id']}",
                "trigger": "scheduled" if i > 0 else "manual",
                "started_at": run_time,
                "finished_at": run_time + timedelta(seconds=2),
                "status": "success",
                "rows_read": random.randint(30, 80),
                "rows_changed": random.randint(0, 15),
                "upserted": random.randint(0, 10),
                "skipped": random.randint(20, 60),
                "errors_count": 0,
                "errors": [],
                "duration_ms": random.randint(800, 3000),
            })
    print(f"Created demo sync runs")

    print("\n✅ Demo verileri başarıyla oluşturuldu!")
    print("Login: agency1@acenta.test / agency123")

asyncio.run(seed_availability_demo())
