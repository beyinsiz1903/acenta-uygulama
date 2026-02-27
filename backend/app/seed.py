"""Seed data — demo organizations, users, agencies, hotels, etc.

Index creation has been moved to app/indexes/seed_indexes.py.
This file only handles idempotent data seeding.
"""
from __future__ import annotations

import logging
import uuid

from app.auth import hash_password
from app.db import get_db
from app.utils import now_utc

logger = logging.getLogger("acenta-master")

DEFAULT_ADMIN_EMAIL = "admin@acenta.test"
DEFAULT_ADMIN_PASSWORD = "admin123"


async def ensure_seed_data() -> None:
    db = await get_db()

    # ── CRM indexes (kept here because ensure_crm_indexes may insert data) ──
    from app.indexes.crm_indexes import ensure_crm_indexes
    await ensure_crm_indexes(db)

    # ══════════════════════════════════════════════════════════
    # 1. Organization
    # ══════════════════════════════════════════════════════════
    org = await db.organizations.find_one({"slug": "default"})
    if not org:
        org_doc = {
            "name": "Varsayilan Acenta",
            "slug": "default",
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "settings": {"currency": "TRY"},
        }
        res = await db.organizations.insert_one(org_doc)
        org_id = str(res.inserted_id)
    else:
        org_id = str(org["_id"])

    # P1.4: cancel penalty percent
    await db.organizations.update_one(
        {"_id": org_id},
        {"$set": {"settings.cancel_penalty_percent": 20.0}},
        upsert=False,
    )

    # ══════════════════════════════════════════════════════════
    # 2. Admin user
    # ══════════════════════════════════════════════════════════
    admin = await db.users.find_one({"organization_id": org_id, "email": DEFAULT_ADMIN_EMAIL})
    if not admin:
        await db.users.insert_one({
            "organization_id": org_id,
            "email": DEFAULT_ADMIN_EMAIL,
            "name": "Admin",
            "password_hash": hash_password(DEFAULT_ADMIN_PASSWORD),
            "roles": ["super_admin"],
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "is_active": True,
        })
    else:
        # Normalize legacy roles
        roles = set(admin.get("roles") or [])
        mapping = {"admin": "super_admin", "sales": "agency_agent", "b2b_agent": "agency_agent"}
        new_roles = {mapping.get(r, r) for r in roles}
        if new_roles != roles:
            await db.users.update_one(
                {"_id": admin["_id"]},
                {"$set": {"roles": list(new_roles), "updated_at": now_utc()}},
            )

    # ══════════════════════════════════════════════════════════
    # 3. Commission & discount groups
    # ══════════════════════════════════════════════════════════
    if not await db.commission_groups.find_one({"organization_id": org_id, "name": "Standart Komisyon"}):
        await db.commission_groups.insert_one({
            "organization_id": org_id,
            "name": "Standart Komisyon",
            "percent": 10.0,
            "created_at": now_utc(),
            "updated_at": now_utc(),
        })

    if not await db.discount_groups.find_one({"organization_id": org_id, "name": "B2B Indirim"}):
        await db.discount_groups.insert_one({
            "organization_id": org_id,
            "name": "B2B Indirim",
            "percent": 5.0,
            "created_at": now_utc(),
            "updated_at": now_utc(),
        })

    # ══════════════════════════════════════════════════════════
    # 4. Agencies
    # ══════════════════════════════════════════════════════════
    agencies = await db.agencies.find({"organization_id": org_id}).to_list(10)
    if len(agencies) == 0:
        now = now_utc()
        a1 = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "Demo Acente A",
            "is_active": True,
            "active": True,
            "settings": {"selling_currency": "TRY"},
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
            "active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": DEFAULT_ADMIN_EMAIL,
            "updated_by": DEFAULT_ADMIN_EMAIL,
        }
        await db.agencies.insert_many([a1, a2])
        agencies = [a1, a2]

    # ══════════════════════════════════════════════════════════
    # 5. Hotels
    # ══════════════════════════════════════════════════════════
    hotels = await db.hotels.find({"organization_id": org_id}).to_list(10)
    if len(hotels) == 0:
        now = now_utc()
        h1 = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "Demo Hotel 1",
            "city": "Istanbul",
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
            "city": "Izmir",
            "country": "TR",
            "active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": DEFAULT_ADMIN_EMAIL,
            "updated_by": DEFAULT_ADMIN_EMAIL,
        }
        await db.hotels.insert_many([h1, h2, h3])
        hotels = [h1, h2, h3]

    # ══════════════════════════════════════════════════════════
    # 6. Agency users (1 per agency)
    # ══════════════════════════════════════════════════════════
    for idx, ag in enumerate(agencies[:2]):
        email = f"agency{idx + 1}@demo.test"
        if not await db.users.find_one({"organization_id": org_id, "email": email}):
            await db.users.insert_one({
                "organization_id": org_id,
                "email": email,
                "name": f"Agency Admin {idx + 1}",
                "password_hash": hash_password("agency123"),
                "roles": ["agency_admin"],
                "agency_id": ag["_id"],
                "created_at": now_utc(),
                "updated_at": now_utc(),
                "is_active": True,
            })

    # Hotel admin user
    if len(hotels) >= 1:
        hotel_admin_email = "hoteladmin@acenta.test"
        if not await db.users.find_one({"organization_id": org_id, "email": hotel_admin_email}):
            await db.users.insert_one({
                "organization_id": org_id,
                "email": hotel_admin_email,
                "name": "Hotel Admin",
                "password_hash": hash_password("admin123"),
                "roles": ["hotel_admin"],
                "hotel_id": hotels[0]["_id"],
                "created_at": now_utc(),
                "updated_at": now_utc(),
                "is_active": True,
            })

    # ══════════════════════════════════════════════════════════
    # 7. Agency-hotel links
    # ══════════════════════════════════════════════════════════
    if len(agencies) >= 2 and len(hotels) >= 3:
        desired_links = [
            (agencies[0]["_id"], hotels[0]["_id"]),
            (agencies[0]["_id"], hotels[1]["_id"]),
            (agencies[1]["_id"], hotels[2]["_id"]),
        ]
        for agency_id, hotel_id in desired_links:
            existing = await db.agency_hotel_links.find_one(
                {"organization_id": org_id, "agency_id": agency_id, "hotel_id": hotel_id}
            )
            if not existing:
                await db.agency_hotel_links.insert_one({
                    "_id": str(uuid.uuid4()),
                    "organization_id": org_id,
                    "agency_id": agency_id,
                    "hotel_id": hotel_id,
                    "active": True,
                    "commission_type": "percent",
                    "commission_value": 10.0,
                    "created_at": now_utc(),
                    "updated_at": now_utc(),
                    "created_by": DEFAULT_ADMIN_EMAIL,
                    "updated_by": DEFAULT_ADMIN_EMAIL,
                })

        # Backfill commission fields for existing links
        await db.agency_hotel_links.update_many(
            {"organization_id": org_id, "commission_type": {"$exists": False}},
            {"$set": {"commission_type": "percent", "commission_value": 10.0, "updated_at": now_utc()}},
        )

    # ══════════════════════════════════════════════════════════
    # 8. B2B channel
    # ══════════════════════════════════════════════════════════
    try:
        if await db.channels.count_documents({"organization_id": org_id}) == 0:
            await db.channels.insert_one({
                "_id": "ch_b2b_portal",
                "organization_id": org_id,
                "name": "B2B Portal",
                "type": "b2b",
                "status": "active",
                "created_at": now_utc(),
                "updated_at": now_utc(),
                "created_by": DEFAULT_ADMIN_EMAIL,
                "updated_by": DEFAULT_ADMIN_EMAIL,
            })
    except Exception:
        pass

    # ══════════════════════════════════════════════════════════
    # 9. Rooms
    # ══════════════════════════════════════════════════════════
    if await db.rooms.count_documents({"organization_id": org_id}) == 0 and len(hotels) >= 3:
        now = now_utc()
        rooms = []

        # Hotel 1 (Istanbul): 5 standard, 3 deluxe
        for i in range(1, 6):
            rooms.append({
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
            rooms.append({
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
            rooms.append({
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
            rooms.append({
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

        # Hotel 3 (Izmir): 3 standard
        for i in range(1, 4):
            rooms.append({
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

        await db.rooms.insert_many(rooms)
        logger.info("Created %d rooms for demo hotels", len(rooms))

    # ══════════════════════════════════════════════════════════
    # 10. Rate plans & periods
    # ══════════════════════════════════════════════════════════
    if await db.rate_plans.count_documents({"organization_id": org_id}) == 0 and len(hotels) >= 3:
        from bson import ObjectId

        now = now_utc()
        plans = []
        periods = []

        # Hotel 1: RO flexible + BB
        plan_ro_h1 = ObjectId()
        plans.append({
            "_id": plan_ro_h1,
            "tenant_id": hotels[0]["_id"],
            "organization_id": org_id,
            "name": "Room Only - Flexible",
            "board": "RO",
            "cancellation_policy_type": "H24",
            "is_active": True,
            "priority": 10,
            "applies_to_room_types": None,
            "created_at": now,
            "updated_at": now,
        })
        plan_bb_h1 = ObjectId()
        plans.append({
            "_id": plan_bb_h1,
            "tenant_id": hotels[0]["_id"],
            "organization_id": org_id,
            "name": "Bed & Breakfast",
            "board": "BB",
            "cancellation_policy_type": "H24",
            "is_active": True,
            "priority": 20,
            "applies_to_room_types": ["standard", "deluxe"],
            "created_at": now,
            "updated_at": now,
        })
        periods.append({
            "_id": str(uuid.uuid4()),
            "tenant_id": hotels[0]["_id"],
            "organization_id": org_id,
            "rate_plan_id": plan_ro_h1,
            "start_date": "2025-01-01",
            "end_date": "2026-12-31",
            "days_of_week": [4, 5, 6],
            "min_stay": None,
            "price_per_night": 2800.0,
            "is_active": True,
            "priority": 5,
            "created_at": now,
        })
        periods.append({
            "_id": str(uuid.uuid4()),
            "tenant_id": hotels[0]["_id"],
            "organization_id": org_id,
            "rate_plan_id": plan_ro_h1,
            "start_date": "2025-01-01",
            "end_date": "2026-12-31",
            "days_of_week": [0, 1, 2, 3],
            "min_stay": None,
            "price_per_night": 2200.0,
            "is_active": True,
            "priority": 10,
            "created_at": now,
        })
        periods.append({
            "_id": str(uuid.uuid4()),
            "tenant_id": hotels[0]["_id"],
            "organization_id": org_id,
            "rate_plan_id": plan_bb_h1,
            "start_date": "2025-01-01",
            "end_date": "2026-12-31",
            "days_of_week": None,
            "min_stay": 2,
            "price_per_night": 2900.0,
            "is_active": True,
            "priority": 15,
            "created_at": now,
        })

        # Hotel 2: Standard rate
        plan_ro_h2 = ObjectId()
        plans.append({
            "_id": plan_ro_h2,
            "tenant_id": hotels[1]["_id"],
            "organization_id": org_id,
            "name": "Standard Rate",
            "board": "RO",
            "cancellation_policy_type": "same_day",
            "is_active": True,
            "priority": 10,
            "applies_to_room_types": None,
            "created_at": now,
            "updated_at": now,
        })
        periods.append({
            "_id": str(uuid.uuid4()),
            "tenant_id": hotels[1]["_id"],
            "organization_id": org_id,
            "rate_plan_id": plan_ro_h2,
            "start_date": "2025-01-01",
            "end_date": None,
            "days_of_week": None,
            "min_stay": None,
            "price_per_night": 2000.0,
            "is_active": True,
            "priority": 10,
            "created_at": now,
        })

        await db.rate_plans.insert_many(plans)
        await db.rate_periods.insert_many(periods)
        logger.info("Created %d rate plans and %d rate periods", len(plans), len(periods))

    # ══════════════════════════════════════════════════════════
    # 11. Pricing rules
    # ══════════════════════════════════════════════════════════
    if not await db.pricing_rules.find_one({"organization_id": org_id, "notes": "seed_p12_default_hotel_markup"}):
        await db.pricing_rules.insert_one({
            "organization_id": org_id,
            "status": "active",
            "priority": 100,
            "scope": {"product_type": "hotel"},
            "validity": {"from": "2026-01-01", "to": "2027-01-01"},
            "action": {"type": "markup_percent", "value": 10.0},
            "notes": "seed_p12_default_hotel_markup",
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by_email": DEFAULT_ADMIN_EMAIL,
        })

    agency1 = await db.agencies.find_one({"organization_id": org_id, "name": "Demo Acente A"})
    if agency1 and not await db.pricing_rules.find_one({"organization_id": org_id, "notes": "seed_p12_agency1_markup"}):
        await db.pricing_rules.insert_one({
            "organization_id": org_id,
            "status": "active",
            "priority": 200,
            "scope": {"product_type": "hotel", "agency_id": agency1["_id"]},
            "validity": {"from": "2026-01-01", "to": "2027-01-01"},
            "action": {"type": "markup_percent", "value": 12.0},
            "notes": "seed_p12_agency1_markup",
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by_email": DEFAULT_ADMIN_EMAIL,
        })

    # ══════════════════════════════════════════════════════════
    # 12. Stop-sell rules & channel allocations
    # ══════════════════════════════════════════════════════════
    if await db.stop_sell_rules.count_documents({"organization_id": org_id}) == 0 and len(hotels) >= 1:
        await db.stop_sell_rules.insert_one({
            "_id": str(uuid.uuid4()),
            "tenant_id": hotels[0]["_id"],
            "organization_id": org_id,
            "source": "local",
            "room_type": "deluxe",
            "start_date": "2025-12-30",
            "end_date": "2026-01-02",
            "is_active": True,
            "reason": "Yilbasi bakim",
            "created_at": now_utc(),
            "updated_at": now_utc(),
        })

    if await db.channel_allocations.count_documents({"organization_id": org_id}) == 0 and len(hotels) >= 1:
        await db.channel_allocations.insert_one({
            "_id": str(uuid.uuid4()),
            "tenant_id": hotels[0]["_id"],
            "organization_id": org_id,
            "source": "local",
            "room_type": "standard",
            "channel": "agency_extranet",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "allotment": 2,
            "is_active": True,
            "created_at": now_utc(),
            "updated_at": now_utc(),
        })

    # ══════════════════════════════════════════════════════════
    # 13. FX rates (EUR/TRY)
    # ══════════════════════════════════════════════════════════
    if not await db.fx_rates.find_one({"organization_id": org_id, "base": "EUR", "quote": "TRY"}):
        await db.fx_rates.insert_one({
            "organization_id": org_id,
            "base": "EUR",
            "quote": "TRY",
            "rate": 34.25,
            "rate_basis": "QUOTE_PER_EUR",
            "as_of": now_utc(),
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by": DEFAULT_ADMIN_EMAIL,
            "updated_by": DEFAULT_ADMIN_EMAIL,
        })

    # ══════════════════════════════════════════════════════════
    # 14. Demo product + rate plan + inventory (60 days)
    # ══════════════════════════════════════════════════════════
    demo_product = await db.products.find_one({"organization_id": org_id, "_id": "demo_product_1"})
    if not demo_product:
        demo_product = {
            "_id": "demo_product_1",
            "organization_id": org_id,
            "type": "hotel",
            "title": "Demo B2B Hotel Product",
            "description": "B2B quotes/bookings happy path demo urunu.",
            "status": "active",
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by": DEFAULT_ADMIN_EMAIL,
            "updated_by": DEFAULT_ADMIN_EMAIL,
        }
        await db.products.insert_one(demo_product)

    # EUR catalog product
    if not await db.products.find_one({"organization_id": org_id, "type": "hotel", "default_currency": "EUR"}):
        now = now_utc()
        hotel_doc = {
            "organization_id": org_id,
            "type": "hotel",
            "code": "HTL_P0_DEMO",
            "name": {"tr": "P0 Demo Otel", "en": "P0 Demo Hotel"},
            "name_search": "p0 demo otel",
            "status": "active",
            "default_currency": "EUR",
            "location": {"city": "Istanbul", "country": "TR"},
            "created_at": now,
            "updated_at": now,
        }
        res_h = await db.products.insert_one(hotel_doc)
        await db.rate_plans.insert_one({
            "organization_id": org_id,
            "product_id": res_h.inserted_id,
            "code": "BB_P0",
            "name": {"tr": "BB Plan", "en": "BB Plan"},
            "board": "BB",
            "cancellation_policy_id": None,
            "payment_type": "postpay",
            "min_stay": 1,
            "max_stay": 30,
            "currency": "EUR",
            "base_net_price": 100.0,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        })

    # Rate plan for demo product
    if not await db.rate_plans.find_one({"organization_id": org_id, "product_id": demo_product["_id"]}):
        await db.rate_plans.insert_one({
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
        })

    # Inventory for next 60 days
    from datetime import timedelta

    today = now_utc().date()
    for i in range(60):
        d = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        if not await db.inventory.find_one({"organization_id": org_id, "product_id": demo_product["_id"], "date": d}):
            await db.inventory.insert_one({
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
            })

    # ══════════════════════════════════════════════════════════
    # 15. Demo customer
    # ══════════════════════════════════════════════════════════
    if not await db.customers.find_one({"organization_id": org_id}):
        await db.customers.insert_one({
            "organization_id": org_id,
            "name": "Demo Musteri",
            "email": "demo.musteri@example.com",
            "phone": "+90 555 000 00 00",
            "notes": "Kurulum sonrasi hizli test icin ornek musteri.",
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by": DEFAULT_ADMIN_EMAIL,
            "updated_by": DEFAULT_ADMIN_EMAIL,
        })

    # ══════════════════════════════════════════════════════════
    # 16. Risk profiles
    # ══════════════════════════════════════════════════════════
    await db.risk_profiles.update_one(
        {"organization_id": org_id},
        {
            "$set": {
                "organization_id": org_id,
                "rate_threshold": 0.5,
                "repeat_threshold_7": 2,
                "mode": "rate_or_repeat",
                "updated_at": now_utc(),
                "updated_by_email": DEFAULT_ADMIN_EMAIL,
            },
            "$setOnInsert": {"created_at": now_utc()},
        },
        upsert=True,
    )

    # ══════════════════════════════════════════════════════════
    # 17. Demo no-show booking
    # ══════════════════════════════════════════════════════════
    from app.routers.admin_demo_seed import ensure_demo_no_show_booking
    await ensure_demo_no_show_booking(db, org_id)

    # ══════════════════════════════════════════════════════════
    # 18. Match Risk v1.2 demo bookings
    # ══════════════════════════════════════════════════════════
    if not await db.bookings.find_one({"organization_id": org_id, "tags": "not_arrived_v1_2_seed"}):
        if len(agencies) >= 1 and len(hotels) >= 1:
            from datetime import timedelta as td

            now = now_utc()
            seven_days_ago = now - td(days=7)
            agency_a = agencies[0]
            hotel_a = hotels[0]
            hotel_b = hotels[1] if len(hotels) > 1 else hotels[0]

            base = {
                "organization_id": org_id,
                "created_at": seven_days_ago + td(days=1),
                "updated_at": now,
                "submitted_at": seven_days_ago + td(days=1),
                "agency_id": agency_a["_id"],
                "hotel_id": hotel_a["_id"],
                "check_in_date": seven_days_ago.date().isoformat(),
                "check_out_date": seven_days_ago.date().isoformat(),
                "status": "cancelled",
                "tags": "not_arrived_v1_2_seed",
            }

            docs = []
            for i in range(3):
                d = base.copy()
                d.update({"_id": str(uuid.uuid4()), "code": f"SEED-A-{i + 1}", "cancel_reason": "PRICE_CHANGED", "cancelled_by": "system"})
                docs.append(d)
            for i in range(3):
                d = base.copy()
                d.update({"_id": str(uuid.uuid4()), "code": f"SEED-B-{i + 1}", "agency_id": agency_a["_id"], "hotel_id": hotel_b["_id"]})
                if i < 2:
                    d["cancelled_by"] = "agency"
                    d["cancel_reason"] = None
                else:
                    d["status"] = "confirmed"
                    d.pop("cancel_reason", None)
                    d.pop("cancelled_by", None)
                docs.append(d)

            await db.bookings.insert_many(docs)
            logger.info("Seeded Match Risk v1.2 demo bookings")

    # ══════════════════════════════════════════════════════════
    # 19. Finance accounts & credit profiles
    # ══════════════════════════════════════════════════════════
    if not await db.finance_accounts.find_one({"organization_id": org_id, "type": "platform", "code": "PLATFORM_AR_EUR"}):
        await db.finance_accounts.insert_one({
            "_id": "acct_platform_ar_eur",
            "organization_id": org_id,
            "type": "platform",
            "owner_id": org_id,
            "code": "PLATFORM_AR_EUR",
            "name": "Platform Receivables (EUR)",
            "currency": "EUR",
            "status": "active",
            "created_at": now_utc(),
            "updated_at": now_utc(),
        })

    for agency in agencies:
        agency_id = str(agency["_id"])
        if not await db.finance_accounts.find_one({"organization_id": org_id, "type": "agency", "owner_id": agency_id}):
            try:
                await db.finance_accounts.insert_one({
                    "_id": f"acct_agency_{agency_id}",
                    "organization_id": org_id,
                    "type": "agency",
                    "owner_id": agency_id,
                    "code": f"AGY_{agency_id[:8].upper()}",
                    "name": f"{agency['name']} Account",
                    "currency": "EUR",
                    "status": "active",
                    "created_at": now_utc(),
                    "updated_at": now_utc(),
                })
                await db.credit_profiles.insert_one({
                    "_id": f"cred_{agency_id}",
                    "organization_id": org_id,
                    "agency_id": agency_id,
                    "currency": "EUR",
                    "limit": 10000.0,
                    "soft_limit": 9000.0,
                    "payment_terms": "NET14",
                    "status": "active",
                    "created_at": now_utc(),
                    "updated_at": now_utc(),
                })
                await db.account_balances.insert_one({
                    "_id": f"bal_{agency_id}_eur",
                    "organization_id": org_id,
                    "account_id": f"acct_agency_{agency_id}",
                    "currency": "EUR",
                    "balance": 0.0,
                    "as_of": now_utc(),
                    "updated_at": now_utc(),
                })
                logger.info("Created finance account for agency: %s", agency["name"])
            except Exception as e:
                logger.warning("Could not create finance account for %s: %s", agency["name"], e)

    logger.info("Seed data complete")
