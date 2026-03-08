from __future__ import annotations

import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.demo_seed_service import HOTEL_BLUEPRINTS, TOUR_BLUEPRINTS


TRIAL_SOURCE = "trial_signup_seed"

CUSTOMER_FIRST_NAMES = [
    "Ayşe",
    "Mehmet",
    "Zeynep",
    "Ali",
    "Elif",
    "Can",
    "Merve",
    "Burak",
    "Selin",
    "Emre",
]

CUSTOMER_LAST_NAMES = [
    "Yılmaz",
    "Kaya",
    "Demir",
    "Çelik",
    "Arslan",
    "Aydın",
    "Koç",
    "Şahin",
    "Yıldız",
    "Öztürk",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", cleaned) or "trial-agency"


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{uuid.uuid5(uuid.NAMESPACE_DNS, value)}"


def _customer_identity(slug: str, index: int) -> tuple[str, str, str]:
    first = CUSTOMER_FIRST_NAMES[index % len(CUSTOMER_FIRST_NAMES)]
    last = CUSTOMER_LAST_NAMES[(index * 3) % len(CUSTOMER_LAST_NAMES)]
    name = f"{first} {last}"
    local_part = re.sub(r"[^a-z0-9]", "", f"{first}.{last}".lower()) or f"guest{index + 1}"
    email = f"{local_part}.{slug}.{index + 1:02d}@trial.demo"
    phone = f"+90 5{500000000 + index:09d}"
    return name, email, phone


async def seed_trial_signup_workspace(
    db: AsyncIOMotorDatabase,
    *,
    organization_id: str,
    tenant_id: str,
    user_id: str,
    company_name: str,
    admin_name: str,
    admin_email: str,
) -> dict[str, Any]:
    slug = _slugify(company_name)[:24]
    agency_id = _stable_id("trial-agency", tenant_id)
    seeded_at = _now()
    rng = random.Random(f"trial-signup:{tenant_id}")

    await db.agencies.update_one(
        {"_id": agency_id, "organization_id": organization_id},
        {
            "$set": {
                "_id": agency_id,
                "organization_id": organization_id,
                "tenant_id": tenant_id,
                "name": company_name,
                "discount_percent": 0,
                "commission_percent": 12.0,
                "status": "active",
                "is_active": True,
                "settings": {"selling_currency": "TRY"},
                "source": TRIAL_SOURCE,
                "updated_at": seeded_at,
                "updated_by": admin_email,
            },
            "$setOnInsert": {
                "created_at": seeded_at,
                "created_by": admin_email,
            },
        },
        upsert=True,
    )

    tours: list[dict[str, Any]] = []
    for index, blueprint in enumerate(TOUR_BLUEPRINTS[:5]):
        tour_id = _stable_id("trial-tour", f"{tenant_id}:{blueprint['name']}")
        created_at = seeded_at - timedelta(days=30 - (index * 3))
        await db.tours.update_one(
            {"_id": tour_id, "organization_id": organization_id},
            {
                "$set": {
                    "_id": tour_id,
                    "organization_id": organization_id,
                    "tenant_id": tenant_id,
                    "type": "tour",
                    "name": blueprint["name"],
                    "name_search": blueprint["name"].lower(),
                    "description": blueprint["description"],
                    "destination": blueprint["destination"],
                    "departure_city": blueprint["departure_city"],
                    "category": blueprint["category"],
                    "base_price": blueprint["base_price"],
                    "currency": blueprint["currency"],
                    "status": "active",
                    "duration_days": blueprint["duration_days"],
                    "max_participants": blueprint["max_participants"],
                    "includes": blueprint["includes"],
                    "excludes": blueprint["excludes"],
                    "highlights": blueprint["highlights"],
                    "source": TRIAL_SOURCE,
                    "updated_at": seeded_at,
                    "updated_by": admin_email,
                },
                "$setOnInsert": {
                    "created_at": created_at,
                    "created_by": admin_email,
                },
            },
            upsert=True,
        )
        tours.append(
            {
                "_id": tour_id,
                "name": blueprint["name"],
                "currency": blueprint["currency"],
                "base_price": float(blueprint["base_price"]),
            }
        )

    products: list[dict[str, Any]] = []
    for tour in tours:
        product_id = _stable_id("trial-product", f"{tenant_id}:{tour['_id']}")
        await db.products.update_one(
            {"_id": product_id, "organization_id": organization_id},
            {
                "$set": {
                    "_id": product_id,
                    "organization_id": organization_id,
                    "tenant_id": tenant_id,
                    "title": tour["name"],
                    "type": "tour",
                    "description": f"{tour['name']} için trial başlangıç ürünü.",
                    "tour_id": tour["_id"],
                    "status": "active",
                    "source": TRIAL_SOURCE,
                    "updated_at": seeded_at,
                    "updated_by": admin_email,
                },
                "$setOnInsert": {
                    "created_at": seeded_at,
                    "created_by": admin_email,
                },
            },
            upsert=True,
        )
        await db.rate_plans.update_one(
            {"organization_id": organization_id, "product_id": product_id},
            {
                "$set": {
                    "organization_id": organization_id,
                    "tenant_id": tenant_id,
                    "product_id": product_id,
                    "name": f"{tour['name']} Trial Fiyatı",
                    "currency": tour["currency"],
                    "base_price": tour["base_price"],
                    "seasons": [],
                    "actions": [],
                    "source": TRIAL_SOURCE,
                    "updated_at": seeded_at,
                    "updated_by": admin_email,
                },
                "$setOnInsert": {
                    "created_at": seeded_at,
                    "created_by": admin_email,
                },
            },
            upsert=True,
        )
        products.append({"_id": product_id, "title": tour["name"]})

    hotels: list[dict[str, Any]] = []
    for index, blueprint in enumerate(HOTEL_BLUEPRINTS[:5]):
        hotel_id = _stable_id("trial-hotel", f"{tenant_id}:{blueprint['name']}")
        await db.hotels.update_one(
            {"_id": hotel_id, "organization_id": organization_id},
            {
                "$set": {
                    "_id": hotel_id,
                    "organization_id": organization_id,
                    "tenant_id": tenant_id,
                    "name": blueprint["name"],
                    "city": blueprint["city"],
                    "country": blueprint["country"],
                    "stars": blueprint["stars"],
                    "address": blueprint["address"],
                    "phone": blueprint["phone"],
                    "email": blueprint["email"],
                    "description": blueprint["description"],
                    "active": True,
                    "source": TRIAL_SOURCE,
                    "updated_at": seeded_at,
                    "updated_by": admin_email,
                },
                "$setOnInsert": {
                    "created_at": seeded_at - timedelta(days=45 - (index * 4)),
                    "created_by": admin_email,
                },
            },
            upsert=True,
        )
        await db.agency_hotel_links.update_one(
            {"organization_id": organization_id, "agency_id": agency_id, "hotel_id": hotel_id},
            {
                "$set": {
                    "organization_id": organization_id,
                    "agency_id": agency_id,
                    "hotel_id": hotel_id,
                    "active": True,
                    "commission_type": "percent",
                    "commission_value": 12.0,
                    "source": TRIAL_SOURCE,
                    "updated_at": seeded_at,
                    "updated_by": admin_email,
                },
                "$setOnInsert": {
                    "_id": _stable_id("trial-hotel-link", f"{agency_id}:{hotel_id}"),
                    "created_at": seeded_at,
                    "created_by": admin_email,
                },
            },
            upsert=True,
        )
        hotels.append({"_id": hotel_id, "name": blueprint["name"]})

    customers: list[dict[str, Any]] = []
    for index in range(20):
        customer_id = _stable_id("trial-customer", f"{tenant_id}:{index + 1}")
        customer_name, customer_email, phone = _customer_identity(slug, index)
        created_at = seeded_at - timedelta(days=60 - index)
        await db.customers.update_one(
            {"_id": customer_id, "organization_id": organization_id},
            {
                "$set": {
                    "_id": customer_id,
                    "organization_id": organization_id,
                    "tenant_id": tenant_id,
                    "name": customer_name,
                    "email": customer_email,
                    "phone": phone,
                    "city": rng.choice(["İstanbul", "Antalya", "İzmir", "Nevşehir", "Denizli"]),
                    "market": "TR" if index < 14 else "DE",
                    "notes": f"{company_name} trial hesabı için örnek müşteri kaydı.",
                    "source": TRIAL_SOURCE,
                    "updated_at": seeded_at,
                    "updated_by": admin_email,
                },
                "$setOnInsert": {
                    "created_at": created_at,
                    "created_by": admin_email,
                },
            },
            upsert=True,
        )
        customers.append({"_id": customer_id, "name": customer_name, "email": customer_email, "phone": phone})

    reservation_statuses = [
        "confirmed",
        "paid",
        "pending",
        "confirmed",
        "paid",
        "pending",
        "cancelled",
        "confirmed",
        "paid",
        "pending",
    ]

    for index in range(30):
        reservation_id = _stable_id("trial-reservation", f"{tenant_id}:{index + 1}")
        product = products[index % len(products)]
        tour = tours[index % len(tours)]
        customer = customers[index % len(customers)]
        travel_date = (seeded_at + timedelta(days=5 + (index % 9), weeks=index // 10)).date().isoformat()
        status = reservation_statuses[index % len(reservation_statuses)]
        pax = (index % 4) + 1
        total_price = round(float(tour["base_price"]) * pax, 2)
        paid_amount = total_price if status == "paid" else (round(total_price * 0.5, 2) if status == "confirmed" else 0.0)
        created_at = seeded_at - timedelta(days=25 - (index % 18), hours=index % 9)
        reservation_doc = {
            "_id": reservation_id,
            "organization_id": organization_id,
            "tenant_id": tenant_id,
            "pnr": f"PNR-{slug[:4].upper()}-{index + 1:04d}",
            "voucher_no": f"VCH-{slug[:4].upper()}-{index + 1:04d}",
            "idempotency_key": f"trial:{tenant_id}:reservation:{index + 1}",
            "product_id": product["_id"],
            "customer_id": customer["_id"],
            "tour_id": tour["_id"],
            "tour_name": tour["name"],
            "product_title": product["title"],
            "customer_name": customer["name"],
            "customer_email": customer["email"],
            "customer_phone": customer["phone"],
            "guest_name": customer["name"],
            "guest_email": customer["email"],
            "guest_phone": customer["phone"],
            "start_date": travel_date,
            "dates": [travel_date],
            "check_in": travel_date,
            "check_out": travel_date,
            "travel_date": travel_date,
            "pax": pax,
            "status": status,
            "currency": tour["currency"],
            "total_price": total_price,
            "discount_amount": 0.0,
            "commission_amount": round(total_price * 0.12, 2),
            "paid_amount": paid_amount,
            "channel": "direct" if index % 2 == 0 else "b2b",
            "agency_id": agency_id,
            "agency_name": company_name,
            "market": "TR" if index < 20 else "DE",
            "notes": "Trial başlangıç verisi",
            "payment_status": "paid" if status == "paid" else ("partially_paid" if paid_amount else "unpaid"),
            "source": TRIAL_SOURCE,
            "updated_at": seeded_at,
            "updated_by": admin_email,
        }
        if status == "confirmed":
            reservation_doc["confirmed_at"] = created_at + timedelta(hours=2)
            reservation_doc["confirmed_by"] = admin_email
        if status == "cancelled":
            reservation_doc["status_history"] = [
                {
                    "from_status": "confirmed",
                    "to_status": "cancelled",
                    "changed_by": admin_email,
                    "changed_at": seeded_at.isoformat(),
                    "reason": "Trial örnek veri tarih değişikliği.",
                }
            ]

        await db.reservations.update_one(
            {"_id": reservation_id, "organization_id": organization_id},
            {
                "$set": reservation_doc,
                "$setOnInsert": {
                    "created_at": created_at,
                    "created_by": admin_email,
                },
            },
            upsert=True,
        )

    counts = {
        "customers": 20,
        "reservations": 30,
        "tours": 5,
        "hotels": 5,
        "products": 5,
    }

    await db.demo_seed_runs.update_one(
        {"tenant_id": tenant_id},
        {
            "$set": {
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "seeded_at": seeded_at,
                "seeded_by": user_id,
                "seeded_by_name": admin_name,
                "source": TRIAL_SOURCE,
                "mode": "trial_signup",
                "counts": counts,
            }
        },
        upsert=True,
    )

    return counts