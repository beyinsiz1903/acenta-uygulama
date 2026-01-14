from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Optional

from bson import ObjectId

from app.db import get_db
from app.utils import now_utc


async def _get_seed_user(db) -> Optional[Dict[str, Any]]:
    """Find a suitable user to derive organization_id from.

    Priority:
    - admin@acenta.test if exists
    - otherwise first user that has organization_id
    - otherwise None (seed should not write anything)
    """

    user = await db.users.find_one({"email": "admin@acenta.test"})
    if user and user.get("organization_id"):
        return user

    user = await db.users.find_one({"organization_id": {"$exists": True}})
    if user and user.get("organization_id"):
        return user

    return None


async def run(db) -> None:
    """Seed minimal CRM/booking data for dev/test.

    Creates:
    - 2 customers (linked / unlinked)
    - 2 bookings (one with customer_id, one without)
    - 1-2 deals and tasks for the linked customer
    """

    # Hard guard: do not run in production-like environments
    app_env = os.environ.get("APP_ENV", "development").lower()
    db_name = os.environ.get("DB_NAME", "test_database")
    if app_env == "production" or "prod" in db_name.lower():
        raise RuntimeError("Dev seed cannot run in production environment")

    seed_user = await _get_seed_user(db)
    if not seed_user:
        raise RuntimeError("No suitable user found with organization_id; aborting seed")

    org_id = seed_user["organization_id"]
    user_id = seed_user.get("id") or seed_user.get("_id")

    now = now_utc()

    # 1) Customers
    customers = [
        {
            "id": "cust_seed_linked",
            "name": "Seed M\u00fc\u015fteri (Linked)",
            "type": "person",
            "organization_id": org_id,
            "tags": ["seed", "linked"],
            "contacts": [
                {
                    "type": "email",
                    "value": "seed.linked@example.test",
                    "is_primary": True,
                },
                {
                    "type": "phone",
                    "value": "+90 555 000 0001",
                    "is_primary": False,
                },
            ],
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "cust_seed_unlinked",
            "name": "Seed M\u00fc\u015fteri (Unlinked)",
            "type": "person",
            "organization_id": org_id,
            "tags": ["seed"],
            "contacts": [],
            "created_at": now,
            "updated_at": now,
        },
    ]

    for cust in customers:
        await db.customers.update_one(
            {"organization_id": org_id, "id": cust["id"]},
            {"$set": cust},
            upsert=True,
        )

    # 2) Bookings (one linked, one unlinked)
    bookings = [
        {
            "booking_id": "BKG-SEED-LINKED",
            "customer_id": "cust_seed_linked",
            "status": "CONFIRMED",
            "currency": "TRY",
            "amounts": {"sell": 1000},
        },
        {
            "booking_id": "BKG-SEED-UNLINKED",
            "customer_id": None,
            "status": "CONFIRMED",
            "currency": "TRY",
            "amounts": {"sell": 750},
        },
    ]

    for b in bookings:
        base = {
            "organization_id": org_id,
            "status": b["status"],
            "currency": b["currency"],
            "amounts": b["amounts"],
            "created_at": now,
            "updated_at": now,
        }
        update_doc: Dict[str, Any] = {"$set": base}
        if b["customer_id"]:
            update_doc["$set"]["customer_id"] = b["customer_id"]
        else:
            update_doc.setdefault("$unset", {})["customer_id"] = ""

        await db.bookings.update_one(
            {"organization_id": org_id, "booking_id": b["booking_id"]},
            update_doc,
            upsert=True,
        )

    # 3) Deals for linked customer
    deals = [
        {
            "id": "deal_seed_1",
            "organization_id": org_id,
            "customer_id": "cust_seed_linked",
            "title": "Seed Yaz Sezonu F\u0131rsat\u0131",
            "stage": "new",
            "status": "open",
            "amount": 50000,
            "currency": "TRY",
            "owner_user_id": user_id,
            "created_at": now,
            "updated_at": now,
        }
    ]

    for deal in deals:
        await db.crm_deals.update_one(
            {"organization_id": org_id, "id": deal["id"]},
            {"$set": deal},
            upsert=True,
        )

    # 4) Tasks for linked customer
    tasks = [
        {
            "id": "task_seed_1",
            "organization_id": org_id,
            "owner_user_id": user_id,
            "title": "Seed M\u00fc\u015fteri ile telefon g\u00f6r\u00fc\u015fmesi",
            "status": "open",
            "priority": "high",
            "due_date": now,
            "related_type": "customer",
            "related_id": "cust_seed_linked",
            "created_at": now,
            "updated_at": now,
        }
    ]

    for task in tasks:
        await db.crm_tasks.update_one(
            {"organization_id": org_id, "id": task["id"]},
            {"$set": task},
            upsert=True,
        )

    print("Dev seed completed for org", org_id)


if __name__ == "__main__":
    async def _main() -> None:
        # Note: get_db() returns a Motor database and ensures connection
        db = await get_db()
        await run(db)

    asyncio.run(_main())
