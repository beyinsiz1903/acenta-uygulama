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
