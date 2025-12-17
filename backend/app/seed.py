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
                "roles": ["admin"],
                "created_at": now_utc(),
                "updated_at": now_utc(),
                "is_active": True,
            }
        )

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

    dg = await db.discount_groups.find_one({"organization_id": org_id, "name": "B2B İndirim"})
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
