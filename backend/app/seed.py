from __future__ import annotations

from app.db import get_db
from app.auth import hash_password
from app.utils import now_utc

DEFAULT_ADMIN_EMAIL = "admin@acenta.test"
DEFAULT_ADMIN_PASSWORD = "admin123"


async def ensure_seed_data() -> None:
    db = await get_db()

    await db.organizations.create_index("slug", unique=True)
    await db.users.create_index([("organization_id", 1), ("email", 1)], unique=True)
    await db.customers.create_index([("organization_id", 1), ("email", 1)])
    await db.products.create_index([("organization_id", 1), ("type", 1)])
    await db.rate_plans.create_index([("organization_id", 1), ("product_id", 1)])
    await db.inventory.create_index([("organization_id", 1), ("product_id", 1), ("date", 1)], unique=True)
    await db.reservations.create_index([("organization_id", 1), ("pnr", 1)], unique=True)
    await db.reservations.create_index([("organization_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
    await db.payments.create_index([("organization_id", 1), ("reservation_id", 1)])
    await db.leads.create_index([("organization_id", 1), ("status", 1), ("sort_index", -1)])
    await db.quotes.create_index([("organization_id", 1), ("status", 1)])

    org = await db.organizations.find_one({"slug": "default"})
    if not org:
        org_doc = {
            "name": "Varsayılan Acenta",
            "slug": "default",
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "settings": {
                "currency": "TRY",
            },
        }
        res = await db.organizations.insert_one(org_doc)
        org_id = str(res.inserted_id)
    else:
        org_id = str(org["_id"])

    admin = await db.users.find_one({"organization_id": org_id, "email": DEFAULT_ADMIN_EMAIL})
    if not admin:
        await db.users.insert_one(
            {
                "organization_id": org_id,
                "email": DEFAULT_ADMIN_EMAIL,
                "name": "Admin",
                "password_hash": hash_password(DEFAULT_ADMIN_PASSWORD),
                "roles": ["super_admin"],
                "created_at": now_utc(),
                "updated_at": now_utc(),
                "is_active": True,
            }
        )
    else:
        # Normalize legacy role -> new role names
        roles = set(admin.get("roles") or [])
        if "admin" in roles:
            roles.discard("admin")
            roles.add("super_admin")
        if "sales" in roles:
            roles.discard("sales")
            roles.add("agency_agent")
        if "b2b_agent" in roles:
            roles.discard("b2b_agent")
            roles.add("agency_agent")
        if roles != set(admin.get("roles") or []):
            await db.users.update_one({"_id": admin["_id"]}, {"$set": {"roles": list(roles), "updated_at": now_utc()}})

    # Create a default commission+discount group for quick setup
    cg = await db.commission_groups.find_one({"organization_id": org_id, "name": "Standart Komisyon"})
    if not cg:
        await db.commission_groups.insert_one(
            {
                "organization_id": org_id,
                "name": "Standart Komisyon",
                "percent": 10.0,
                "created_at": now_utc(),
                "updated_at": now_utc(),
            }
        )

    # -------------------------------
    # Phase-1 tenant demo: agencies/hotels/links + agency_admin users
    # -------------------------------
    await db.agencies.create_index([("organization_id", 1), ("name", 1)])
    await db.hotels.create_index([("organization_id", 1), ("name", 1)])
    await db.agency_hotel_links.create_index(
        [("organization_id", 1), ("agency_id", 1), ("hotel_id", 1)], unique=True
    )

    # Create 2 agencies if none
    agencies = await db.agencies.find({"organization_id": org_id}).to_list(10)
    if len(agencies) == 0:
        import uuid

        now = now_utc()
        a1 = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "Demo Acente A",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": DEFAULT_ADMIN_EMAIL,
            "updated_by": DEFAULT_ADMIN_EMAIL,
        }
        a2 = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "Demo Acente B",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": DEFAULT_ADMIN_EMAIL,
            "updated_by": DEFAULT_ADMIN_EMAIL,
        }
        await db.agencies.insert_many([a1, a2])
        agencies = [a1, a2]

    # Create 3 hotels if none
    hotels = await db.hotels.find({"organization_id": org_id}).to_list(10)
    if len(hotels) == 0:
        import uuid

        now = now_utc()
        h1 = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "Demo Hotel 1",
            "city": "İstanbul",
            "country": "TR",
            "active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": DEFAULT_ADMIN_EMAIL,
            "updated_by": DEFAULT_ADMIN_EMAIL,
        }
        h2 = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "Demo Hotel 2",
            "city": "Antalya",
            "country": "TR",
            "active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": DEFAULT_ADMIN_EMAIL,
            "updated_by": DEFAULT_ADMIN_EMAIL,
        }
        h3 = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "Demo Hotel 3",
            "city": "İzmir",
            "country": "TR",
            "active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": DEFAULT_ADMIN_EMAIL,
            "updated_by": DEFAULT_ADMIN_EMAIL,
        }
        await db.hotels.insert_many([h1, h2, h3])
        hotels = [h1, h2, h3]

    # Create agency_admin users (1 per agency) if missing
    for idx, ag in enumerate(agencies[:2]):
        email = f"agency{idx+1}@demo.test"
        existing_user = await db.users.find_one({"organization_id": org_id, "email": email})
        if not existing_user:
            await db.users.insert_one(
                {
                    "organization_id": org_id,
                    "email": email,
                    "name": f"Agency Admin {idx+1}",
                    "password_hash": hash_password("agency123"),
                    "roles": ["agency_admin"],
                    "agency_id": ag["_id"],
                    "created_at": now_utc(),
                    "updated_at": now_utc(),
                    "is_active": True,
                }
            )

    # Ensure links: agency A -> hotel1+hotel2, agency B -> hotel3
    if len(agencies) >= 2 and len(hotels) >= 3:
        import uuid

        def _link(agency_id: str, hotel_id: str):
            return {
                "_id": str(uuid.uuid4()),
                "organization_id": org_id,
                "agency_id": agency_id,
                "hotel_id": hotel_id,
                "active": True,
                "created_at": now_utc(),
                "updated_at": now_utc(),
                "created_by": DEFAULT_ADMIN_EMAIL,
                "updated_by": DEFAULT_ADMIN_EMAIL,
            }

        desired = [
            (agencies[0]["_id"], hotels[0]["_id"]),
            (agencies[0]["_id"], hotels[1]["_id"]),
            (agencies[1]["_id"], hotels[2]["_id"]),
        ]
        for agency_id, hotel_id in desired:
            existing_link = await db.agency_hotel_links.find_one(
                {"organization_id": org_id, "agency_id": agency_id, "hotel_id": hotel_id}
            )
            if not existing_link:
                await db.agency_hotel_links.insert_one(_link(agency_id, hotel_id))

    dg = await db.discount_groups.find_one({"organization_id": org_id, "name": "B2B İndirim"})


    # FAZ-2.2.1: Create rooms for hotels if none exist
    rooms_count = await db.rooms.count_documents({"organization_id": org_id})
    if rooms_count == 0 and len(hotels) >= 3:
        import uuid

        now = now_utc()
        rooms_to_create = []

        # Hotel 1 (İstanbul): 5 standard, 3 deluxe
        for i in range(1, 6):
            rooms_to_create.append({
                "_id": str(uuid.uuid4()),
                "tenant_id": hotels[0]["_id"],
                "organization_id": org_id,
                "room_type": "standard",
                "room_number": f"10{i}",
                "base_price": 2450.0,
                "max_occupancy": {"adults": 2, "children": 2},
                "active": True,
                "created_at": now,
                "updated_at": now,
                "created_by": DEFAULT_ADMIN_EMAIL,
            })
        for i in range(1, 4):
            rooms_to_create.append({
                "_id": str(uuid.uuid4()),
                "tenant_id": hotels[0]["_id"],
                "organization_id": org_id,
                "room_type": "deluxe",
                "room_number": f"20{i}",
                "base_price": 3200.0,
                "max_occupancy": {"adults": 3, "children": 1},
                "active": True,
                "created_at": now,
                "updated_at": now,
                "created_by": DEFAULT_ADMIN_EMAIL,
            })

        # Hotel 2 (Antalya): 4 standard, 2 deluxe
        for i in range(1, 5):
            rooms_to_create.append({
                "_id": str(uuid.uuid4()),
                "tenant_id": hotels[1]["_id"],
                "organization_id": org_id,
                "room_type": "standard",
                "room_number": f"10{i}",
                "base_price": 2200.0,
                "max_occupancy": {"adults": 2, "children": 2},
                "active": True,
                "created_at": now,
                "updated_at": now,
                "created_by": DEFAULT_ADMIN_EMAIL,
            })
        for i in range(1, 3):
            rooms_to_create.append({
                "_id": str(uuid.uuid4()),
                "tenant_id": hotels[1]["_id"],
                "organization_id": org_id,
                "room_type": "deluxe",
                "room_number": f"20{i}",
                "base_price": 2900.0,
                "max_occupancy": {"adults": 3, "children": 1},
                "active": True,
                "created_at": now,
                "updated_at": now,
                "created_by": DEFAULT_ADMIN_EMAIL,
            })

        # Hotel 3 (İzmir): 3 standard
        for i in range(1, 4):
            rooms_to_create.append({
                "_id": str(uuid.uuid4()),
                "tenant_id": hotels[2]["_id"],
                "organization_id": org_id,
                "room_type": "standard",
                "room_number": f"10{i}",
                "base_price": 1950.0,
                "max_occupancy": {"adults": 2, "children": 2},
                "active": True,
                "created_at": now,
                "updated_at": now,
                "created_by": DEFAULT_ADMIN_EMAIL,
            })

        await db.rooms.insert_many(rooms_to_create)
        logger.info(f"Created {len(rooms_to_create)} rooms for demo hotels")

    if not dg:
        await db.discount_groups.insert_one(
            {
                "organization_id": org_id,
                "name": "B2B İndirim",
                "percent": 5.0,
                "created_at": now_utc(),
                "updated_at": now_utc(),
            }
        )

    # -------------------------------
    # Minimal demo data (only if empty)
    # -------------------------------
    demo_product = await db.products.find_one({"organization_id": org_id})
    if not demo_product:
        prod_res = await db.products.insert_one(
            {
                "organization_id": org_id,
                "type": "tour",
                "title": "Demo İstanbul Şehir Turu",
                "description": "Kurulum sonrası hızlı test için örnek ürün.",
                "created_at": now_utc(),
                "updated_at": now_utc(),
                "created_by": DEFAULT_ADMIN_EMAIL,
                "updated_by": DEFAULT_ADMIN_EMAIL,
            }
        )
        demo_product = await db.products.find_one({"_id": prod_res.inserted_id})

    demo_customer = await db.customers.find_one({"organization_id": org_id})
    if not demo_customer:
        cust_res = await db.customers.insert_one(
            {
                "organization_id": org_id,
                "name": "Demo Müşteri",
                "email": "demo.musteri@example.com",
                "phone": "+90 555 000 00 00",
                "notes": "Kurulum sonrası hızlı test için örnek müşteri.",
                "created_at": now_utc(),
                "updated_at": now_utc(),
                "created_by": DEFAULT_ADMIN_EMAIL,
                "updated_by": DEFAULT_ADMIN_EMAIL,
            }
        )
        demo_customer = await db.customers.find_one({"_id": cust_res.inserted_id})

    # Ensure a rate plan exists for demo product (used for pricing fallback)
    if demo_product:
        rp = await db.rate_plans.find_one({"organization_id": org_id, "product_id": demo_product["_id"]})
        if not rp:
            await db.rate_plans.insert_one(
                {
                    "organization_id": org_id,
                    "product_id": demo_product["_id"],
                    "name": "Standart",
                    "currency": "TRY",
                    "base_price": 1500.0,
                    "seasons": [],
                    "actions": [],
                    "created_at": now_utc(),
                    "updated_at": now_utc(),
                    "created_by": DEFAULT_ADMIN_EMAIL,
                    "updated_by": DEFAULT_ADMIN_EMAIL,
                }
            )

        # Ensure inventory exists for next 60 days so reservation creation doesn't fail
        # We only upsert if records are missing.
        from datetime import timedelta

        today = now_utc().date()
        for i in range(0, 60):
            d = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            existing_inv = await db.inventory.find_one(
                {"organization_id": org_id, "product_id": demo_product["_id"], "date": d}
            )
            if not existing_inv:
                await db.inventory.insert_one(
                    {
                        "organization_id": org_id,
                        "product_id": demo_product["_id"],
                        "date": d,
                        "capacity_total": 30,
                        "capacity_available": 30,
                        "price": 1500.0,
                        "restrictions": {"closed": False, "cta": False, "ctd": False},
                        "created_at": now_utc(),
                        "updated_at": now_utc(),
                        "created_by": DEFAULT_ADMIN_EMAIL,
                        "updated_by": DEFAULT_ADMIN_EMAIL,
                    }
                )
