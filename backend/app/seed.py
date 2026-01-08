from __future__ import annotations

import logging

from app.db import get_db
from app.auth import hash_password
from app.utils import now_utc

logger = logging.getLogger("acenta-master")

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

    # FAZ-8: indexes for PMS/mock + source
    await db.rate_plans.create_index([("organization_id", 1), ("source", 1)])
    await db.rate_periods.create_index([("organization_id", 1), ("source", 1)])
    await db.inventory.create_index([("organization_id", 1), ("source", 1)])
    await db.stop_sell_rules.create_index([("organization_id", 1), ("source", 1)])
    await db.channel_allocations.create_index([("organization_id", 1), ("source", 1)])

    await db.agency_hotel_links.create_index(
        [("organization_id", 1), ("agency_id", 1), ("hotel_id", 1)], unique=True
    )

    # FAZ-6: booking_financial_entries indexes

    # FAZ-7: audit logs indexes
    await db.audit_logs.create_index([("organization_id", 1), ("created_at", -1)])
    await db.audit_logs.create_index([("organization_id", 1), ("target.type", 1), ("target.id", 1), ("created_at", -1)])

    # FAZ-7: booking events outbox indexes
    await db.booking_events.create_index([("organization_id", 1), ("delivered", 1), ("created_at", 1)])
    await db.booking_events.create_index([("organization_id", 1), ("entity_id", 1), ("event_type", 1)])
    
    # FAZ-2.0.1: WhatsApp tracking idempotency index
    await db.booking_events.create_index([
        ("booking_id", 1), 
        ("event_type", 1), 
        ("payload.actor_email", 1)
    ])


    # FAZ-8: PMS mock collections indexes
    await db.pms_idempotency.create_index([( "organization_id", 1), ("idempotency_key", 1)], unique=True)
    await db.pms_bookings.create_index([( "organization_id", 1), ("hotel_id", 1), ("created_at", -1)])

    # FAZ-7: search cache indexes (TTL by expires_at)
    await db.search_cache.create_index([("expires_at", 1)], expireAfterSeconds=0)
    await db.search_cache.create_index([("organization_id", 1), ("agency_id", 1), ("created_at", -1)])

    # FAZ-9.2: voucher tokens (public share links)
    await db.vouchers.create_index([("expires_at", 1)], expireAfterSeconds=0)
    await db.vouchers.create_index([("organization_id", 1), ("booking_id", 1)])
    await db.vouchers.create_index([("token", 1)], unique=True)

    # FAZ-9.3: email outbox for booking events
    await db.email_outbox.create_index([("status", 1), ("next_retry_at", 1)])
    await db.email_outbox.create_index([("organization_id", 1), ("booking_id", 1)])

    # FAZ-10.0: hotel integrations (channel manager, ota, etc.)
    await db.hotel_integrations.create_index(
        [("organization_id", 1), ("hotel_id", 1), ("kind", 1)], unique=True
    )
    await db.hotel_integrations.create_index([("status", 1), ("provider", 1)])
    await db.hotel_integrations.create_index([("organization_id", 1), ("kind", 1), ("updated_at", -1)])

    # FAZ-2: booking_drafts collection (TTL 15 minutes)
    await db.booking_drafts.create_index([("expires_at", 1)], expireAfterSeconds=0)
    await db.booking_drafts.create_index([("organization_id", 1), ("created_at", -1)])
    await db.booking_drafts.create_index([("submitted_booking_id", 1)])  # Idempotency
    
    # FAZ-2: bookings indexes for pending workflow
    await db.bookings.create_index([("organization_id", 1), ("status", 1), ("submitted_at", -1)])
    await db.bookings.create_index([("agency_id", 1), ("status", 1), ("submitted_at", -1)])
    await db.bookings.create_index([("hotel_id", 1), ("status", 1), ("submitted_at", -1)])
    await db.bookings.create_index([("approval_deadline_at", 1)])  # SLA tracking
    # Repeat not-arrived 7d: index for per-pair window scans
    await db.bookings.create_index([
        ("organization_id", 1),
        ("agency_id", 1),
        ("hotel_id", 1),
        ("status", 1),
        ("created_at", -1),
    ])


    # FAZ-10.1: integration sync outbox
    await db.integration_sync_outbox.create_index([("status", 1), ("next_retry_at", 1)])
    await db.integration_sync_outbox.create_index([
        ("organization_id", 1), ("hotel_id", 1), ("kind", 1), ("created_at", -1)
    ])

    await db.booking_financial_entries.create_index(
        [("organization_id", 1), ("hotel_id", 1), ("month", 1), ("settlement_status", 1)]
    )
    await db.booking_financial_entries.create_index(
        [("organization_id", 1), ("agency_id", 1), ("month", 1), ("settlement_status", 1)]
    )
    await db.booking_financial_entries.create_index(
        [("organization_id", 1), ("booking_id", 1), ("type", 1)]
    )

    # P4 v0: match_actions indexes
    await db.match_actions.create_index([
        ("organization_id", 1),
        ("match_id", 1),
    ], unique=True)
    await db.match_actions.create_index([
        ("organization_id", 1),
        ("status", 1),
        ("updated_at", -1),
    ])

    # SCALE v1: action_policies indexes (per-org)
    await db.action_policies.create_index([
        ("organization_id", 1),
    ], unique=True)

    # SCALE v1: approval_tasks indexes
    await db.approval_tasks.create_index([
        ("organization_id", 1),
        ("status", 1),
        ("requested_at", -1),
    ])
    await db.approval_tasks.create_index([
        ("organization_id", 1),
        ("task_type", 1),
        ("status", 1),
    ])
    await db.approval_tasks.create_index([
        ("organization_id", 1),
        ("target.match_id", 1),
    ])

    # STORY v1: risk_snapshots indexes
    await db.risk_snapshots.create_index([
        ("organization_id", 1),
        ("snapshot_key", 1),
        ("generated_at", -1),
    ])

    # Alerting v0: match_alert_policies & match_alert_deliveries indexes
    await db.match_alert_policies.create_index([
        ("organization_id", 1)
    ], unique=True)
    # Update match_alert_deliveries indexes to be channel-aware
    # Drop old unique index (organization_id, match_id, fingerprint) if it exists
    try:
        indexes = await db.match_alert_deliveries.index_information()
        for name, info in indexes.items():
            keys = info.get("key") or []
            if keys == [("organization_id", 1), ("match_id", 1), ("fingerprint", 1)]:
                await db.match_alert_deliveries.drop_index(name)
    except Exception:
        # Best-effort; if anything fails we don't want seed to crash
        pass

    await db.match_alert_deliveries.create_index([
        ("organization_id", 1),
        ("match_id", 1),
        ("fingerprint", 1),
        ("channel", 1),
    ], unique=True)

    # Booking outcomes indexes
    await db.booking_outcomes.create_index([
        ("organization_id", 1),
        ("booking_id", 1),
    ], unique=True)
    await db.booking_outcomes.create_index([
        ("organization_id", 1),
        ("agency_id", 1),
        ("hotel_id", 1),
        ("checkin_date", -1),
    ])
    await db.match_alert_deliveries.create_index([
        ("organization_id", 1),
        ("sent_at", -1),
    ])

    # Risk profiles: per-org unified thresholds for match risk
    await db.risk_profiles.create_index([
        ("organization_id", 1),
    ], unique=True)

    # Deterministic org_demo risk profile for tests (affects only org 'default')
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


    # Exports v0: export_policies & export_runs indexes
    await db.export_policies.create_index([
        ("organization_id", 1),
        ("key", 1),
    ], unique=True)
    await db.export_runs.create_index([
        ("organization_id", 1),
        ("policy_key", 1),
        ("generated_at", -1),
    ])

    # Ensure deterministic no-show demo booking for org_demo
    from app.routers.admin_demo_seed import ensure_demo_no_show_booking

    await ensure_demo_no_show_booking(db, org_id)
    await db.export_runs.create_index([
        ("organization_id", 1),
        ("download.token", 1),
    ], unique=True, sparse=True)


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
                # FAZ-6: default commission on link
                "commission_type": "percent",
                "commission_value": 10.0,
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

        # FAZ-6: backfill commission fields for existing links
        await db.agency_hotel_links.update_many(
            {"organization_id": org_id, "commission_type": {"$exists": False}},
            {"$set": {"commission_type": "percent", "commission_value": 10.0, "updated_at": now_utc()}},
        )

    # -------------------------------
    # B2B channels seed (stable channel_id for portal)
    # -------------------------------
    channels_count = await db.channels.count_documents({"organization_id": org_id}) if hasattr(db, "channels") else 0
    try:
        if hasattr(db, "channels") and channels_count == 0:
            await db.channels.insert_one(
                {
                    "_id": "ch_b2b_portal",
                    "organization_id": org_id,
                    "name": "B2B Portal",
                    "type": "b2b",
                    "status": "active",
                    "created_at": now_utc(),
                    "updated_at": now_utc(),
    # Voucher template seed (Phase 1)\n    existing_tpl = await db.voucher_templates.find_one({\"organization_id\": org_id, \"key\": \"b2b_booking_default\"}) if hasattr(db, \"voucher_templates\") else None\n    try:\n        if hasattr(db, \"voucher_templates\") and not existing_tpl:\n            await db.voucher_templates.insert_one(\n                {\n                    \"organization_id\": org_id,\n                    \"key\": \"b2b_booking_default\",\n                    \"name\": \"B2B Booking Default Voucher\",\n                    \"html\": \"<html><body><h1>Booking Voucher</h1><p>Booking ID: {booking_id}</p><p>Guest: {customer_name} ({customer_email})</p><p>Dates: {check_in} → {check_out}</p><p>Amount: {amount_sell} {currency}</p></body></html>\",\n                    \"locale\": \"tr-TR\",\n                    \"version\": 1,\n                    \"status\": \"active\",\n                    \"created_at\": now_utc(),\n                    \"updated_at\": now_utc(),\n                    \"created_by\": DEFAULT_ADMIN_EMAIL,\n                    \"updated_by\": DEFAULT_ADMIN_EMAIL,\n                }\n            )\n    except Exception:\n        # voucher_templates collection optional; ignore if missing\n        pass\n
                    "created_by": DEFAULT_ADMIN_EMAIL,
                    "updated_by": DEFAULT_ADMIN_EMAIL,
                }
            )
    except Exception:
        # channels collection is optional in current schema; ignore if missing
        pass


    dg = await db.discount_groups.find_one({"organization_id": org_id, "name": "B2B İndirim"})


    # -------------------------------
    # FAZ-5: Seed 1 hotel_admin user (separate from super_admin)
    # -------------------------------
    if len(hotels) >= 1:
        hotel_admin_email = "hoteladmin@acenta.test"
        existing_hotel_admin = await db.users.find_one({"organization_id": org_id, "email": hotel_admin_email})
        if not existing_hotel_admin:
            await db.users.insert_one(
                {
                    "organization_id": org_id,
                    "email": hotel_admin_email,
                    "name": "Hotel Admin",
                    "password_hash": hash_password("admin123"),
                    "roles": ["hotel_admin"],
                    "hotel_id": hotels[0]["_id"],
                    "created_at": now_utc(),
                    "updated_at": now_utc(),
                    "is_active": True,
                }
            )


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


    # FAZ-2.2.2: Create rate_plans and rate_periods if none exist
    rate_plans_count = await db.rate_plans.count_documents({"organization_id": org_id})
    if rate_plans_count == 0 and len(hotels) >= 3:
        from bson import ObjectId

        now = now_utc()
        plans_to_create = []
        periods_to_create = []

        # Hotel 1: 2 rate plans (RO flexible, BB flexible)
        plan_ro_h1 = ObjectId()
        plans_to_create.append({
            "_id": plan_ro_h1,
            "tenant_id": hotels[0]["_id"],
            "organization_id": org_id,
            "name": "Room Only - Flexible",
            "board": "RO",
            "cancellation_policy_type": "H24",
            "is_active": True,
            "priority": 10,
            "applies_to_room_types": None,  # All room types
            "created_at": now,
            "updated_at": now,
        })

        plan_bb_h1 = ObjectId()
        plans_to_create.append({
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

        # Periods for Hotel 1
        # Weekend premium (Fri-Sat-Sun)
        periods_to_create.append({
            "_id": str(uuid.uuid4()),
            "tenant_id": hotels[0]["_id"],
            "organization_id": org_id,
            "rate_plan_id": plan_ro_h1,
            "start_date": "2025-01-01",
            "end_date": "2026-12-31",
            "days_of_week": [4, 5, 6],  # Fri, Sat, Sun
            "min_stay": None,
            "price_per_night": 2800.0,
            "is_active": True,
            "priority": 5,
            "created_at": now,
        })

        # Weekday (Mon-Thu)
        periods_to_create.append({
            "_id": str(uuid.uuid4()),
            "tenant_id": hotels[0]["_id"],
            "organization_id": org_id,
            "rate_plan_id": plan_ro_h1,
            "start_date": "2025-01-01",
            "end_date": "2026-12-31",
            "days_of_week": [0, 1, 2, 3],  # Mon-Thu
            "min_stay": None,
            "price_per_night": 2200.0,
            "is_active": True,
            "priority": 10,
            "created_at": now,
        })

        # BB Plan - All days
        periods_to_create.append({
            "_id": str(uuid.uuid4()),
            "tenant_id": hotels[0]["_id"],
            "organization_id": org_id,
            "rate_plan_id": plan_bb_h1,
            "start_date": "2025-01-01",
            "end_date": "2026-12-31",
            "days_of_week": None,  # All days
            "min_stay": 2,  # Min 2 nights
            "price_per_night": 2900.0,
            "is_active": True,
            "priority": 15,
            "created_at": now,
        })

        # Hotel 2: 1 simple rate plan
        plan_ro_h2 = ObjectId()
        plans_to_create.append({
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

        # All days, no min stay
        periods_to_create.append({
            "_id": str(uuid.uuid4()),
            "tenant_id": hotels[1]["_id"],
            "organization_id": org_id,
            "rate_plan_id": plan_ro_h2,
            "start_date": "2025-01-01",
            "end_date": None,  # Open-ended
            "days_of_week": None,
            "min_stay": None,
            "price_per_night": 2000.0,
            "is_active": True,
            "priority": 10,
            "created_at": now,
        })

        await db.rate_plans.insert_many(plans_to_create)
        await db.rate_periods.insert_many(periods_to_create)
        
        logger.info(f"Created {len(plans_to_create)} rate plans and {len(periods_to_create)} rate periods")


    # FAZ-2.3: Create stop-sell rules + channel allocations if none exist
    stop_sell_count = await db.stop_sell_rules.count_documents({"organization_id": org_id})
    if stop_sell_count == 0 and len(hotels) >= 1:
        import uuid

        now = now_utc()

        # Stop-sell for Hotel 1 deluxe (New Year period)
        await db.stop_sell_rules.insert_one({
            "_id": str(uuid.uuid4()),
            "tenant_id": hotels[0]["_id"],
            "organization_id": org_id,
            "source": "local",
            "room_type": "deluxe",
            "start_date": "2025-12-30",
            "end_date": "2026-01-02",
            "is_active": True,
            "reason": "Yılbaşı bakım",
            "created_at": now,
            "updated_at": now,
        })

        logger.info("Created demo stop-sell rule")

    allocation_count = await db.channel_allocations.count_documents({"organization_id": org_id})
    if allocation_count == 0 and len(hotels) >= 1:
        import uuid

        now = now_utc()

        # Allocation for Hotel 1 standard (agency_extranet gets 2 rooms)
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
            "created_at": now,
            "updated_at": now,
        })

        logger.info("Created demo channel allocation")


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
    # -------------------------------
    # Minimal B2B demo product for quotes/booking flow
    # -------------------------------
    # Use stable ID "demo_product_1" so test scripts can rely on it.
    from bson import ObjectId

    demo_product = await db.products.find_one({"organization_id": org_id, "_id": "demo_product_1"})
    if not demo_product:
        # Legacy structure for B2B booking engine (title/description)
        demo_product_doc = {
            "_id": "demo_product_1",
            "organization_id": org_id,
            "type": "hotel",  # B2B hotel-style product
            "title": "Demo B2B Hotel Product",
            "description": "B2B quotes/bookings happy path demo ürünü.",
            "status": "active",  # required by B2BPricingService._ensure_product_sellable
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by": DEFAULT_ADMIN_EMAIL,
            "updated_by": DEFAULT_ADMIN_EMAIL,
        }
        await db.products.insert_one(demo_product_doc)
        demo_product = demo_product_doc

    # Ensure at least one catalog-style EUR hotel product + rate plan for Commerce OS
    hotel_catalog = await db.products.find_one(
        {
            "organization_id": org_id,
            "type": "hotel",
            "status": "active",
            "default_currency": "EUR",
        }
    )
    if not hotel_catalog:
        from datetime import datetime as _dt
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
        hotel_id = res_h.inserted_id

        rate_doc = {
            "organization_id": org_id,
            "product_id": hotel_id,
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
        }
        await db.rate_plans.insert_one(rate_doc)

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


    # -------------------------------
    # Match Risk v1.2 demo data: operational vs behavioral cancels
    # -------------------------------
    seed_marker = await db.bookings.find_one({"organization_id": org_id, "tags": "not_arrived_v1_2_seed"})
    if not seed_marker and len(agencies) >= 1 and len(hotels) >= 1:
        import uuid
        from datetime import timedelta

        now = now_utc()
        seven_days_ago = now - timedelta(days=7)

        agency_a = agencies[0]
        hotel_a = hotels[0]
        agency_b = agencies[0]
        hotel_b = hotels[1] if len(hotels) > 1 else hotels[0]

        base_common = {
            "organization_id": org_id,
            "created_at": seven_days_ago + timedelta(days=1),
            "updated_at": now,
            "submitted_at": seven_days_ago + timedelta(days=1),
            "agency_id": agency_a["_id"],
            "hotel_id": hotel_a["_id"],
            "check_in_date": (seven_days_ago.date().isoformat()),
            "check_out_date": (seven_days_ago.date().isoformat()),
            "status": "cancelled",
            "tags": "not_arrived_v1_2_seed",
        }

        # Match-A: purely operational cancels (PRICE_CHANGED/system)
        match_a_docs = []
        for i in range(3):
            d = base_common.copy()
            d.update(
                {
                    "_id": str(uuid.uuid4()),
                    "code": f"SEED-A-{i+1}",
                    "cancel_reason": "PRICE_CHANGED",
                    "cancelled_by": "system",
                }
            )
            match_a_docs.append(d)

        # Match-B: behavioral cancels (agency)
        match_b_docs = []
        for i in range(3):
            d = base_common.copy()
            d.update(
                {
                    "_id": str(uuid.uuid4()),
                    "code": f"SEED-B-{i+1}",
                    "agency_id": agency_b["_id"],
                    "hotel_id": hotel_b["_id"],
                }
            )
            if i < 2:
                d["status"] = "cancelled"
                d["cancelled_by"] = "agency"
                d["cancel_reason"] = None
            else:
                d["status"] = "confirmed"
                d.pop("cancel_reason", None)
                d.pop("cancelled_by", None)
            match_b_docs.append(d)

        await db.bookings.insert_many(match_a_docs + match_b_docs)
        logger.info("Seeded Match Risk v1.2 demo bookings for operational vs behavioral cancels")

    # ========================================================================
    # Finance OS Phase 1: Platform + Agency accounts + Credit profile
    # ========================================================================
    platform_account = await db.finance_accounts.find_one(
        {"organization_id": org_id, "type": "platform", "code": "PLATFORM_AR_EUR"}
    )
    if not platform_account:
        platform_doc = {
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
        }
        await db.finance_accounts.insert_one(platform_doc)
        logger.info("✅ Created platform finance account: PLATFORM_AR_EUR")

    # Create finance accounts for all existing agencies
    if agencies:
        for agency in agencies:
            agency_id = str(agency["_id"])
            
            # Check if account already exists
            existing_account = await db.finance_accounts.find_one(
                {"organization_id": org_id, "type": "agency", "owner_id": agency_id}
            )
            
            if not existing_account:
                # Use agency_id suffix to ensure uniqueness
                agency_code = f"AGY_{agency_id[:8].upper()}"
                
                account_doc = {
                    "_id": f"acct_agency_{agency_id}",
                    "organization_id": org_id,
                    "type": "agency",
                    "owner_id": agency_id,
                    "code": agency_code,
                    "name": f"{agency['name']} Account",
                    "currency": "EUR",
                    "status": "active",
                    "created_at": now_utc(),
                    "updated_at": now_utc(),
                }
                
                try:
                    await db.finance_accounts.insert_one(account_doc)
                    
                    # Create credit profile for agency
                    credit_doc = {
                        "_id": f"cred_{agency_id}",
                        "organization_id": org_id,
                        "agency_id": agency_id,
                        "currency": "EUR",
                        "limit": 10000.0,
                        "soft_limit": 9000.0,  # soft_limit <= limit (warning at 90%)
                        "payment_terms": "NET14",
                        "status": "active",
                        "created_at": now_utc(),
                        "updated_at": now_utc(),
                    }
                    await db.credit_profiles.insert_one(credit_doc)
                    
                    # Initialize balance cache
                    balance_doc = {
                        "_id": f"bal_{agency_id}_eur",
                        "organization_id": org_id,
                        "account_id": f"acct_agency_{agency_id}",
                        "currency": "EUR",
                        "balance": 0.0,
                        "as_of": now_utc(),
                        "updated_at": now_utc(),
                    }
                    await db.account_balances.insert_one(balance_doc)
                    
                    logger.info(f"✅ Created finance account + credit profile for agency: {agency['name']}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not create finance account for {agency['name']}: {e}")

    logger.info("✅ Finance OS Phase 1 seed data complete")
