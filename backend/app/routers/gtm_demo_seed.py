from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth import require_roles
from app.db import get_db
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/demo", tags=["gtm-demo-seed"])


SEED_RATE: dict[str, tuple[int, datetime]] = {}
SEED_LIMIT = 3
SEED_VERSION = 2
DEMO_SOURCE = "demo_seed"

TOUR_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "name": "Kapadokya Balon Turu",
        "destination": "Kapadokya",
        "departure_city": "İstanbul",
        "category": "Kültür",
        "base_price": 4850.0,
        "duration_days": 2,
        "max_participants": 18,
        "description": "Balon manzarası, Göreme ve butik deneyim odaklı yüksek dönüşümlü kültür turu.",
        "highlights": ["Göreme", "Uçhisar", "Gün doğumu manzarası"],
    },
    {
        "name": "Pamukkale Termal Kaçamak",
        "destination": "Denizli",
        "departure_city": "İzmir",
        "category": "Doğa",
        "base_price": 3650.0,
        "duration_days": 1,
        "max_participants": 22,
        "description": "Travertenler ve termal deneyim odaklı günübirlik satış vitrini.",
        "highlights": ["Pamukkale", "Hierapolis", "Termal havuz"],
    },
    {
        "name": "Efes & Şirince Rotası",
        "destination": "İzmir",
        "departure_city": "İzmir",
        "category": "Tarih",
        "base_price": 3290.0,
        "duration_days": 1,
        "max_participants": 20,
        "description": "Cruise ve kültür segmentinde güçlü dönüşüm sağlayan antik kent rotası.",
        "highlights": ["Efes", "Şirince", "Celsus Kütüphanesi"],
    },
    {
        "name": "İstanbul Boğaz Premium",
        "destination": "İstanbul",
        "departure_city": "İstanbul",
        "category": "Şehir",
        "base_price": 2950.0,
        "duration_days": 1,
        "max_participants": 28,
        "description": "Şehir demosu için boğaz hattı ve premium fotoğraf rotaları içerir.",
        "highlights": ["Ortaköy", "Rumeli Hisarı", "Boğaz turu"],
    },
    {
        "name": "Antalya Tekne & Koylar",
        "destination": "Antalya",
        "departure_city": "Antalya",
        "category": "Deniz",
        "base_price": 3425.0,
        "duration_days": 1,
        "max_participants": 26,
        "description": "Yaz sezonu satış demoları için koy rotaları ve yüzme molaları sunar.",
        "highlights": ["Kaleiçi", "Koy rotası", "Tam gün deneyim"],
    },
]

HOTEL_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "name": "Cappadocia Cave Hotel",
        "city": "Nevşehir",
        "country": "TR",
        "stars": 5,
        "description": "Balayı ve butik deneyim odaklı mağara otel.",
    },
    {
        "name": "Pamukkale Thermal Hotel",
        "city": "Denizli",
        "country": "TR",
        "stars": 4,
        "description": "Termal havuz ve wellness konseptiyle sağlık turizmine uygun tesis.",
    },
    {
        "name": "Ephesus Boutique Hotel",
        "city": "İzmir",
        "country": "TR",
        "stars": 4,
        "description": "Kültür turları sonrası konaklama için uygun butik otel.",
    },
    {
        "name": "Istanbul Bosphorus Hotel",
        "city": "İstanbul",
        "country": "TR",
        "stars": 5,
        "description": "MICE ve premium şehir konaklaması için boğaz hattında konumlu otel.",
    },
    {
        "name": "Antalya Beach Resort",
        "city": "Antalya",
        "country": "TR",
        "stars": 5,
        "description": "Yaz charter satışları için güçlü resort ürün.",
    },
]

CUSTOMER_NAMES = [
    "Ayşe Demir",
    "Ahmet Yılmaz",
    "Elif Kaya",
    "Mehmet Çelik",
    "Zeynep Aydın",
    "Can Şahin",
    "Selin Arslan",
    "Mert Koç",
    "Derya Özkan",
    "Burak Kılıç",
    "Gizem Aksoy",
    "Emre Karaca",
    "Seda Tunç",
    "Onur Polat",
    "Pelin Şimşek",
    "Cem Yurt",
    "Deniz Erdem",
    "Nazlı Güneş",
    "Umut Sarı",
    "Ece Öztürk",
]


class DemoSeedRequest(BaseModel):
    mode: str = Field(default="light", pattern="^(light|full)$")
    with_finance: bool = True
    with_crm: bool = True
    force: bool = False


class DemoSeedResponse(BaseModel):
    ok: bool
    already_seeded: bool = False
    counts: dict[str, int] = Field(default_factory=dict)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _build_seed_code(prefix: str, index: int) -> str:
    return f"{prefix}-{index + 1:03d}-{uuid.uuid4().hex[:6].upper()}"


def _check_seed_rate(user_id: str) -> None:
    from app.errors import AppError

    now = _now()
    entry = SEED_RATE.get(user_id)
    if not entry:
        SEED_RATE[user_id] = (1, now)
        return

    count, window_start = entry
    if (now - window_start).total_seconds() >= 60:
        SEED_RATE[user_id] = (1, now)
        return

    if count >= SEED_LIMIT:
        raise AppError(429, "rate_limited", "Çok fazla demo seed isteği gönderildi. Lütfen biraz bekleyin.", {})

    SEED_RATE[user_id] = (count + 1, window_start)


async def _resolve_tenant_id(user: dict[str, Any], db) -> str:
    tenant_id = user.get("tenant_id")
    org_id = user.get("organization_id")
    if tenant_id:
        return str(tenant_id)

    tenant = await db.tenants.find_one({"organization_id": org_id}, {"_id": 1}, sort=[("created_at", 1)])
    if tenant and tenant.get("_id") is not None:
        return str(tenant.get("_id"))

    tenant_id = str(uuid.uuid4())
    await db.tenants.insert_one(
        {
            "_id": tenant_id,
            "organization_id": org_id,
            "name": f"Tenant {org_id}",
            "status": "active",
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    logger.info("Auto-created tenant %s for org %s", tenant_id, org_id)
    return tenant_id


async def _resolve_agency_id(user: dict[str, Any], db) -> str | None:
    if user.get("agency_id"):
        return str(user.get("agency_id"))

    org_id = user.get("organization_id")
    agency = await db.agencies.find_one({"organization_id": org_id}, {"_id": 1}, sort=[("created_at", 1)])
    if agency and agency.get("_id") is not None:
        return str(agency.get("_id"))

    user_with_agency = await db.users.find_one(
        {"organization_id": org_id, "agency_id": {"$exists": True, "$ne": None}},
        {"agency_id": 1},
        sort=[("created_at", 1)],
    )
    if user_with_agency and user_with_agency.get("agency_id"):
        return str(user_with_agency.get("agency_id"))

    return None


async def _cleanup_demo_documents(db, org_id: str, tenant_id: str) -> None:
    cleanup_plan = {
        "agency_hotel_links": {"organization_id": org_id, "source": DEMO_SOURCE},
        "crm_deals": {"organization_id": org_id, "source": DEMO_SOURCE},
        "crm_tasks": {"organization_id": org_id, "source": DEMO_SOURCE},
        "customers": {"organization_id": org_id, "source": DEMO_SOURCE},
        "hotels": {"organization_id": org_id, "source": DEMO_SOURCE},
        "inventory": {"organization_id": org_id, "source": DEMO_SOURCE},
        "ops_cases": {"organization_id": org_id, "source": DEMO_SOURCE},
        "products": {"organization_id": org_id, "source": DEMO_SOURCE},
        "rate_plans": {"organization_id": org_id, "source": DEMO_SOURCE},
        "reservations": {"organization_id": org_id, "source": DEMO_SOURCE},
        "tours": {"organization_id": org_id, "source": DEMO_SOURCE},
        "webpos_ledger": {"organization_id": org_id, "source": DEMO_SOURCE},
        "webpos_payments": {"organization_id": org_id, "source": DEMO_SOURCE},
    }

    for collection_name, query in cleanup_plan.items():
        await db[collection_name].delete_many(query)

    await db.demo_seed_runs.delete_many({"tenant_id": tenant_id})


async def _has_stale_demo_documents(db, org_id: str) -> bool:
    for collection_name in ("hotels", "tours", "products", "customers", "reservations"):
        if await db[collection_name].count_documents({"organization_id": org_id, "source": DEMO_SOURCE}, limit=1):
            return True
    return False


def _build_hotels(org_id: str, tenant_id: str, source_tag: str, count: int) -> list[dict[str, Any]]:
    hotels: list[dict[str, Any]] = []
    for index, blueprint in enumerate(HOTEL_BLUEPRINTS[:count]):
        hotel_id = f"demo-hotel-{uuid.uuid4().hex[:12]}"
        hotels.append(
            {
                "_id": hotel_id,
                "organization_id": org_id,
                "tenant_id": tenant_id,
                "name": blueprint["name"],
                "city": blueprint["city"],
                "country": blueprint["country"],
                "stars": blueprint["stars"],
                "description": blueprint["description"],
                "active": True,
                "source": DEMO_SOURCE,
                "source_tag": source_tag,
                "created_at": _now() - timedelta(days=60 - (index * 3)),
                "updated_at": _now(),
            }
        )
    return hotels


def _build_agency_hotel_links(
    org_id: str,
    agency_id: str | None,
    admin_email: str,
    hotels: list[dict[str, Any]],
    source_tag: str,
) -> list[dict[str, Any]]:
    if not agency_id:
        return []

    now = _now()
    return [
        {
            "_id": f"demo-link-{uuid.uuid4().hex[:12]}",
            "organization_id": org_id,
            "agency_id": agency_id,
            "hotel_id": hotel["_id"],
            "active": True,
            "commission_type": "percent",
            "commission_value": 12.0,
            "sales_mode": "free_sale",
            "source": DEMO_SOURCE,
            "source_tag": source_tag,
            "created_at": now,
            "updated_at": now,
            "created_by": admin_email,
            "updated_by": admin_email,
        }
        for hotel in hotels
    ]


def _build_tours(org_id: str, tenant_id: str, source_tag: str, count: int) -> list[dict[str, Any]]:
    tours: list[dict[str, Any]] = []
    for index, blueprint in enumerate(TOUR_BLUEPRINTS[:count]):
        tours.append(
            {
                "_id": ObjectId(),
                "organization_id": org_id,
                "tenant_id": tenant_id,
                "type": "tour",
                "name": blueprint["name"],
                "description": blueprint["description"],
                "destination": blueprint["destination"],
                "departure_city": blueprint["departure_city"],
                "category": blueprint["category"],
                "base_price": blueprint["base_price"],
                "currency": "TRY",
                "status": "active",
                "duration_days": blueprint["duration_days"],
                "max_participants": blueprint["max_participants"],
                "highlights": blueprint["highlights"],
                "includes": ["Transfer", "Rehberlik", "Program dahil hizmetler"],
                "excludes": ["Kişisel harcamalar"],
                "images": [],
                "cover_image": "",
                "source": DEMO_SOURCE,
                "source_tag": source_tag,
                "created_at": _now() - timedelta(days=45 - (index * 2)),
                "updated_at": _now(),
            }
        )
    return tours


def _build_products(
    org_id: str,
    tenant_id: str,
    admin_email: str,
    tours: list[dict[str, Any]],
    source_tag: str,
) -> list[dict[str, Any]]:
    now = _now()
    return [
        {
            "_id": ObjectId(),
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "title": tour["name"],
            "type": "tour",
            "description": tour.get("description") or "",
            "tour_id": tour["_id"],
            "source": DEMO_SOURCE,
            "source_tag": source_tag,
            "created_at": now,
            "updated_at": now,
            "created_by": admin_email,
            "updated_by": admin_email,
        }
        for tour in tours
    ]


def _build_rate_plans(
    org_id: str,
    admin_email: str,
    products: list[dict[str, Any]],
    tours: list[dict[str, Any]],
    source_tag: str,
) -> list[dict[str, Any]]:
    now = _now()
    rate_plans: list[dict[str, Any]] = []
    for index, product in enumerate(products):
        tour = tours[index]
        rate_plans.append(
            {
                "_id": ObjectId(),
                "organization_id": org_id,
                "product_id": product["_id"],
                "name": f"{tour['name']} Standart Fiyat",
                "currency": "TRY",
                "base_price": float(tour.get("base_price") or 0),
                "seasons": [],
                "actions": [],
                "source": DEMO_SOURCE,
                "source_tag": source_tag,
                "created_at": now,
                "updated_at": now,
                "created_by": admin_email,
                "updated_by": admin_email,
            }
        )
    return rate_plans


def _build_inventory(
    org_id: str,
    admin_email: str,
    products: list[dict[str, Any]],
    tours: list[dict[str, Any]],
    source_tag: str,
) -> list[dict[str, Any]]:
    now = _now()
    base_day = now + timedelta(days=3)
    inventory_docs: list[dict[str, Any]] = []
    for index, product in enumerate(products):
        tour = tours[index]
        for offset in range(6):
            travel_date = (base_day + timedelta(days=(index * 2) + (offset * 4))).date().isoformat()
            inventory_docs.append(
                {
                    "_id": ObjectId(),
                    "organization_id": org_id,
                    "product_id": product["_id"],
                    "date": travel_date,
                    "capacity_total": int(tour.get("max_participants") or 20),
                    "capacity_available": max(int(tour.get("max_participants") or 20) - 4, 4),
                    "price": float(tour.get("base_price") or 0),
                    "restrictions": {"closed": False, "cta": False, "ctd": False},
                    "source": DEMO_SOURCE,
                    "source_tag": source_tag,
                    "created_at": now,
                    "updated_at": now,
                    "created_by": admin_email,
                    "updated_by": admin_email,
                }
            )
    return inventory_docs


def _build_customers(org_id: str, tenant_id: str, admin_email: str, count: int, source_tag: str) -> list[dict[str, Any]]:
    now = _now()
    customers: list[dict[str, Any]] = []
    for index, name in enumerate(CUSTOMER_NAMES[:count]):
        slug = name.lower().replace(" ", ".").replace("ç", "c").replace("ş", "s").replace("ı", "i").replace("ğ", "g").replace("ö", "o").replace("ü", "u")
        customers.append(
            {
                "_id": ObjectId(),
                "organization_id": org_id,
                "tenant_id": tenant_id,
                "name": name,
                "email": f"{slug}.{index + 1:02d}@demo.test",
                "phone": f"+90 5{random.randint(300000000, 599999999)}",
                "notes": "Demo müşteri kaydı",
                "city": random.choice(["İstanbul", "Antalya", "İzmir", "Denizli", "Nevşehir"]),
                "source": DEMO_SOURCE,
                "source_tag": source_tag,
                "created_at": now - timedelta(days=30 - min(index, 25)),
                "updated_at": now,
                "created_by": admin_email,
                "updated_by": admin_email,
            }
        )
    return customers


def _build_reservations(
    org_id: str,
    tenant_id: str,
    agency_id: str | None,
    agency_name: str | None,
    admin_email: str,
    products: list[dict[str, Any]],
    tours: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    count: int,
    source_tag: str,
) -> list[dict[str, Any]]:
    rng = random.Random(f"demo-reservations:{tenant_id}")
    now = _now()
    statuses = ["pending", "confirmed", "paid", "pending", "confirmed", "cancelled"]
    reservations: list[dict[str, Any]] = []

    for index in range(count):
        product = products[index % len(products)]
        tour = tours[index % len(tours)]
        customer = customers[index % len(customers)]
        status = statuses[index % len(statuses)]
        pax = rng.randint(1, 4)
        travel_date = (now + timedelta(days=5 + index)).date().isoformat()
        base_price = float(tour.get("base_price") or 0)
        total_price = round(base_price * pax, 2)
        paid_amount = total_price if status == "paid" else (round(total_price * 0.4, 2) if status == "confirmed" else 0.0)
        reservation = {
            "_id": ObjectId(),
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "pnr": _build_seed_code("DMO", index),
            "voucher_no": _build_seed_code("VCH", index),
            "idempotency_key": f"{source_tag}:reservation:{index + 1}",
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
            "end_date": None,
            "dates": [travel_date],
            "check_in": travel_date,
            "check_out": travel_date,
            "travel_date": travel_date,
            "pax": pax,
            "status": status,
            "currency": "TRY",
            "total_price": total_price,
            "price_items": [
                {
                    "date": travel_date,
                    "unit_price": base_price,
                    "pax": pax,
                    "total": total_price,
                }
            ],
            "discount_amount": 0.0,
            "commission_amount": round(total_price * 0.12, 2),
            "paid_amount": paid_amount,
            "channel": "b2b" if agency_id and index % 3 == 0 else "direct",
            "agency_id": agency_id,
            "agency_name": agency_name,
            "payment_status": "paid" if status == "paid" else ("partially_paid" if paid_amount else "unpaid"),
            "source": DEMO_SOURCE,
            "source_tag": source_tag,
            "created_at": now - timedelta(days=rng.randint(1, 28), hours=rng.randint(1, 10)),
            "updated_at": now,
            "created_by": admin_email,
            "updated_by": admin_email,
        }
        if status == "confirmed":
            reservation["confirmed_at"] = now - timedelta(days=1)
            reservation["confirmed_by"] = admin_email
        if status == "cancelled":
            reservation["status_history"] = [
                {
                    "from_status": "confirmed",
                    "to_status": "cancelled",
                    "changed_by": admin_email,
                    "changed_at": (now - timedelta(hours=12)).isoformat(),
                    "reason": "Demo senaryosu için iptal edildi.",
                }
            ]
        reservations.append(reservation)
    return reservations


def _build_payments_and_ledger(
    org_id: str,
    tenant_id: str,
    source_tag: str,
    reservations: list[dict[str, Any]],
    count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    now = _now()
    payments: list[dict[str, Any]] = []
    ledger_entries: list[dict[str, Any]] = []
    for index, reservation in enumerate(reservations[:count]):
        amount = round(float(reservation.get("total_price") or 0) * 0.4, 2)
        payment_id = f"demo-pay-{uuid.uuid4().hex[:12]}"
        payments.append(
            {
                "_id": payment_id,
                "tenant_id": tenant_id,
                "organization_id": org_id,
                "reservation_id": reservation["_id"],
                "amount": amount,
                "currency": "TRY",
                "method": random.choice(["cash", "credit_card", "bank_transfer"]),
                "reference": _build_seed_code("PAY", index),
                "note": "Demo ödeme",
                "status": "completed",
                "source": DEMO_SOURCE,
                "source_tag": source_tag,
                "created_at": now - timedelta(days=index),
            }
        )
        ledger_entries.append(
            {
                "_id": f"demo-ledger-{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "organization_id": org_id,
                "type": "debit",
                "amount": amount,
                "currency": "TRY",
                "reference_type": "payment",
                "reference_id": payment_id,
                "description": "Demo ödeme kaydı",
                "source": DEMO_SOURCE,
                "source_tag": source_tag,
                "created_at": now - timedelta(days=index),
            }
        )
    return payments, ledger_entries


def _build_cases(org_id: str, tenant_id: str, reservations: list[dict[str, Any]], source_tag: str, count: int) -> list[dict[str, Any]]:
    titles = [
        "Check-in saati teyidi",
        "Fatura talebi",
        "Otel notu güncellemesi",
        "Transfer koordinasyonu",
        "Misafir bilgi teyidi",
        "Tarih değişiklik isteği",
    ]
    now = _now()
    cases: list[dict[str, Any]] = []
    for index in range(count):
        reservation = reservations[index % len(reservations)]
        case_id = f"demo-case-{uuid.uuid4().hex[:12]}"
        cases.append(
            {
                "_id": case_id,
                "case_id": case_id,
                "organization_id": org_id,
                "tenant_id": tenant_id,
                "booking_id": str(reservation["_id"]),
                "title": titles[index % len(titles)],
                "status": "open" if index % 2 == 0 else "in_progress",
                "priority": random.choice(["low", "medium", "high"]),
                "source": DEMO_SOURCE,
                "source_tag": source_tag,
                "created_at": now - timedelta(days=index),
                "updated_at": now,
            }
        )
    return cases


def _build_crm_deals(
    org_id: str,
    tenant_id: str,
    user_id: str,
    customers: list[dict[str, Any]],
    source_tag: str,
    count: int,
) -> list[dict[str, Any]]:
    stages = ["lead", "contacted", "proposal", "won"]
    titles = [
        "Kurumsal grup talebi",
        "Yaz sezonu premium paket",
        "Hafta sonu şehir kaçamağı",
        "Kültür turu upsell fırsatı",
    ]
    now = _now()
    deals: list[dict[str, Any]] = []
    for index in range(count):
        stage = stages[index % len(stages)]
        deals.append(
            {
                "id": f"demo-deal-{uuid.uuid4().hex[:12]}",
                "organization_id": org_id,
                "tenant_id": tenant_id,
                "customer_id": customers[index % len(customers)]["_id"],
                "title": titles[index % len(titles)],
                "amount": random.choice([12000, 18000, 24000, 36000]),
                "currency": "TRY",
                "stage": stage,
                "status": "won" if stage == "won" else "open",
                "owner_user_id": user_id,
                "source": DEMO_SOURCE,
                "source_tag": source_tag,
                "created_at": now - timedelta(days=index + 2),
                "updated_at": now,
            }
        )
    return deals


def _build_crm_tasks(
    org_id: str,
    tenant_id: str,
    user_id: str,
    deals: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    source_tag: str,
    count: int,
) -> list[dict[str, Any]]:
    titles = [
        "Teklif paylaş",
        "Misafir bilgisi teyit et",
        "Ödeme takibini yap",
        "Otel notunu güncelle",
        "Tur kontenjanını kontrol et",
        "Upsell fırsatını ara",
    ]
    now = _now()
    tasks: list[dict[str, Any]] = []
    for index in range(count):
        tasks.append(
            {
                "id": f"demo-task-{uuid.uuid4().hex[:12]}",
                "organization_id": org_id,
                "tenant_id": tenant_id,
                "deal_id": deals[index % len(deals)]["id"] if deals else None,
                "customer_id": customers[index % len(customers)]["_id"],
                "title": titles[index % len(titles)],
                "status": "done" if index % 4 == 0 else "open",
                "priority": random.choice(["low", "normal", "high"]),
                "assignee_user_id": user_id,
                "owner_user_id": user_id,
                "due_at": now + timedelta(days=index + 1),
                "due_date": now + timedelta(days=index + 1),
                "source": DEMO_SOURCE,
                "source_tag": source_tag,
                "created_at": now - timedelta(days=index),
                "updated_at": now,
            }
        )
    return tasks


async def _insert_many_if_any(collection, docs: list[dict[str, Any]]) -> None:
    if docs:
        await collection.insert_many(docs, ordered=True)


@router.post("/seed", response_model=DemoSeedResponse)
async def seed_demo_data(
    body: DemoSeedRequest,
    request: Request,
    db=Depends(get_db),
    user=Depends(require_roles(["super_admin"])),
):
    """Tenant scoped demo data seed for dashboard, hotels, tours and reservations."""

    user_id = str(user.get("id") or user.get("_id") or user.get("email"))
    org_id = str(user.get("organization_id"))
    tenant_id = await _resolve_tenant_id(user, db)
    agency_id = await _resolve_agency_id(user, db)

    _check_seed_rate(user_id)

    existing_run = await db.demo_seed_runs.find_one({"tenant_id": tenant_id})
    stale_demo_docs = await _has_stale_demo_documents(db, org_id)
    legacy_seed_run = bool(existing_run and existing_run.get("seed_version") != SEED_VERSION)

    if body.force or legacy_seed_run or (stale_demo_docs and not existing_run):
        await _cleanup_demo_documents(db, org_id, tenant_id)
        existing_run = None

    if existing_run and not body.force:
        return DemoSeedResponse(ok=True, already_seeded=True, counts=existing_run.get("counts", {}))

    admin_email = user.get("email") or "demo@seed.test"
    agency_name = None
    if agency_id:
        agency_doc = await db.agencies.find_one({"organization_id": org_id, "_id": agency_id}, {"name": 1})
        agency_name = agency_doc.get("name") if agency_doc else None

    mode_config = {
        "light": {
            "hotels": 5,
            "tours": 5,
            "customers": 10,
            "reservations": 12,
            "payments": 4,
            "cases": 3,
            "deals": 4,
            "tasks": 8,
        },
        "full": {
            "hotels": 5,
            "tours": 5,
            "customers": 20,
            "reservations": 30,
            "payments": 8,
            "cases": 6,
            "deals": 8,
            "tasks": 16,
        },
    }[body.mode]

    source_tag = f"tenant-demo:{tenant_id}:{uuid.uuid4().hex[:8]}"

    hotels = _build_hotels(org_id, tenant_id, source_tag, mode_config["hotels"])
    agency_hotel_links = _build_agency_hotel_links(org_id, agency_id, admin_email, hotels, source_tag)
    tours = _build_tours(org_id, tenant_id, source_tag, mode_config["tours"])
    products = _build_products(org_id, tenant_id, admin_email, tours, source_tag)
    rate_plans = _build_rate_plans(org_id, admin_email, products, tours, source_tag)
    inventory_docs = _build_inventory(org_id, admin_email, products, tours, source_tag)
    customers = _build_customers(org_id, tenant_id, admin_email, mode_config["customers"], source_tag)
    reservations = _build_reservations(
        org_id,
        tenant_id,
        agency_id,
        agency_name,
        admin_email,
        products,
        tours,
        customers,
        mode_config["reservations"],
        source_tag,
    )

    await _insert_many_if_any(db.hotels, hotels)
    await _insert_many_if_any(db.agency_hotel_links, agency_hotel_links)
    await _insert_many_if_any(db.tours, tours)
    await _insert_many_if_any(db.products, products)
    await _insert_many_if_any(db.rate_plans, rate_plans)
    await _insert_many_if_any(db.inventory, inventory_docs)
    await _insert_many_if_any(db.customers, customers)
    await _insert_many_if_any(db.reservations, reservations)

    counts = {
        "hotels": len(hotels),
        "tours": len(tours),
        "products": len(products),
        "customers": len(customers),
        "reservations": len(reservations),
        "inventory": len(inventory_docs),
    }

    if body.with_finance:
        payments, ledger_entries = _build_payments_and_ledger(
            org_id,
            tenant_id,
            source_tag,
            reservations,
            mode_config["payments"],
        )
        await _insert_many_if_any(db.webpos_payments, payments)
        await _insert_many_if_any(db.webpos_ledger, ledger_entries)
        counts["payments"] = len(payments)
        counts["ledger_entries"] = len(ledger_entries)

    cases = _build_cases(org_id, tenant_id, reservations, source_tag, mode_config["cases"])
    await _insert_many_if_any(db.ops_cases, cases)
    counts["cases"] = len(cases)

    if body.with_crm:
        deals = _build_crm_deals(org_id, tenant_id, user_id, customers, source_tag, mode_config["deals"])
        tasks = _build_crm_tasks(org_id, tenant_id, user_id, deals, customers, source_tag, mode_config["tasks"])
        await _insert_many_if_any(db.crm_deals, deals)
        await _insert_many_if_any(db.crm_tasks, tasks)
        counts["deals"] = len(deals)
        counts["tasks"] = len(tasks)

    await db.demo_seed_runs.update_one(
        {"tenant_id": tenant_id},
        {
            "$set": {
                "tenant_id": tenant_id,
                "organization_id": org_id,
                "mode": body.mode,
                "counts": counts,
                "seed_version": SEED_VERSION,
                "seeded_at": _now(),
                "seeded_by": user_id,
                "source": DEMO_SOURCE,
            }
        },
        upsert=True,
    )

    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": user_id,
                "email": user.get("email"),
                "roles": user.get("roles", []),
            },
            request=request,
            action="demo.seed_run",
            target_type="demo_seed",
            target_id=tenant_id,
            meta={"mode": body.mode, "counts": counts, "seed_version": SEED_VERSION},
        )
    except Exception as exc:  # pragma: no cover - best effort only
        logger.warning("Audit log failed for demo seed: %s", exc)

    return DemoSeedResponse(ok=True, already_seeded=False, counts=counts)
