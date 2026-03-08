from __future__ import annotations

import random
import re
import uuid
import zlib
from datetime import datetime, timedelta, timezone
from typing import Any

from faker import Faker
from pymongo.database import Database

from app.auth import hash_password


TOUR_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "name": "Kapadokya Turu",
        "destination": "Kapadokya",
        "departure_city": "İstanbul",
        "category": "Kültür",
        "base_price": 4850.0,
        "currency": "TRY",
        "duration_days": 2,
        "max_participants": 18,
        "description": "Balon izleme, Göreme Açık Hava Müzesi ve bölgenin en güçlü satış demolarından biri için ideal butik kültür turu.",
        "includes": ["Profesyonel rehberlik", "Müze girişleri", "Öğle yemeği", "Transfer"],
        "excludes": ["Balon uçuşu", "Kişisel harcamalar"],
        "highlights": ["Gün doğumu balon manzarası", "Göreme", "Uçhisar"],
    },
    {
        "name": "Pamukkale Turu",
        "destination": "Pamukkale",
        "departure_city": "İzmir",
        "category": "Doğa & Kültür",
        "base_price": 3650.0,
        "currency": "TRY",
        "duration_days": 1,
        "max_participants": 24,
        "description": "Travertenler, Hierapolis kalıntıları ve termal deneyim içeren yüksek dönüşüm potansiyelli günübirlik tur.",
        "includes": ["Rehberlik", "Ulaşım", "Müze girişleri"],
        "excludes": ["Akşam yemeği", "Kişisel harcamalar"],
        "highlights": ["Pamukkale travertenleri", "Hierapolis", "Termal havuz"],
    },
    {
        "name": "Efes Antik Kent Turu",
        "destination": "Selçuk",
        "departure_city": "İzmir",
        "category": "Tarih",
        "base_price": 3290.0,
        "currency": "TRY",
        "duration_days": 1,
        "max_participants": 20,
        "description": "Cruise yolcuları ve yabancı pazar için çok güçlü bir satış vitrini sunan antik kent turu.",
        "includes": ["Lisanslı rehber", "Transfer", "Giriş biletleri"],
        "excludes": ["İçecekler"],
        "highlights": ["Celsus Kütüphanesi", "Mermer Cadde", "Artemis Tapınağı"],
    },
    {
        "name": "İstanbul Boğaz Turu",
        "destination": "İstanbul",
        "departure_city": "İstanbul",
        "category": "Şehir Deneyimi",
        "base_price": 2950.0,
        "currency": "TRY",
        "duration_days": 1,
        "max_participants": 30,
        "description": "Boğaz hattı, tarihi yarımada panoraması ve fotoğraf odaklı rota ile şehir demosu için vitrinde güçlü seçenek.",
        "includes": ["Tekne turu", "Rehberlik", "Atıştırmalık ikram"],
        "excludes": ["Otel transferi"],
        "highlights": ["Dolmabahçe panoraması", "Ortaköy", "Rumeli Hisarı"],
    },
    {
        "name": "Antalya Tekne Turu",
        "destination": "Antalya",
        "departure_city": "Antalya",
        "category": "Deniz & Eğlence",
        "base_price": 3425.0,
        "currency": "TRY",
        "duration_days": 1,
        "max_participants": 28,
        "description": "Yaz sezonu satış demoları için yüksek talep gören koy rotaları ve yüzme molaları içeren tekne turu.",
        "includes": ["Öğle yemeği", "Yüzme molaları", "Tekne hizmeti"],
        "excludes": ["İçecekler", "Su sporları"],
        "highlights": ["Kaleiçi çıkışı", "Koy rotası", "Tam gün deniz deneyimi"],
    },
]


HOTEL_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "name": "Cappadocia Cave Hotel",
        "city": "Nevşehir",
        "country": "TR",
        "stars": 5,
        "address": "Göreme Kasabası, Aydınlı Mah. No:18 Nevşehir",
        "phone": "+90 384 271 44 10",
        "email": "sales@cappadociacavehotel.demo",
        "description": "Balayı ve butik deneyim odaklı mağara otel.",
    },
    {
        "name": "Pamukkale Thermal Hotel",
        "city": "Denizli",
        "country": "TR",
        "stars": 4,
        "address": "Karahayıt Mah. Termal Cad. No:7 Denizli",
        "phone": "+90 258 271 22 40",
        "email": "sales@pamukkalethermal.demo",
        "description": "Termal havuz ve wellness konseptiyle sağlık turizmine uygun tesis.",
    },
    {
        "name": "Ephesus Boutique Hotel",
        "city": "İzmir",
        "country": "TR",
        "stars": 4,
        "address": "Selçuk Merkez, İstasyon Cad. No:21 İzmir",
        "phone": "+90 232 892 11 88",
        "email": "sales@ephesusboutique.demo",
        "description": "Kültür turları ve cruise sonrası konaklama için uygun butik otel.",
    },
    {
        "name": "Istanbul Bosphorus Hotel",
        "city": "İstanbul",
        "country": "TR",
        "stars": 5,
        "address": "Beşiktaş, Çırağan Cad. No:42 İstanbul",
        "phone": "+90 212 327 45 90",
        "email": "sales@istanbulbosphorus.demo",
        "description": "MICE ve premium şehir konaklaması için boğaz hattında konumlu otel.",
    },
    {
        "name": "Antalya Beach Resort",
        "city": "Antalya",
        "country": "TR",
        "stars": 5,
        "address": "Lara Sahil Yolu, Kundu No:55 Antalya",
        "phone": "+90 242 352 67 80",
        "email": "sales@antalyabeachresort.demo",
        "description": "Aile, deniz-kum-güneş ve yaz charter satışları için güçlü resort ürün.",
    },
]


MARKETS: list[dict[str, str]] = [
    {"code": "TR", "label": "Türkiye"},
    {"code": "DE", "label": "Almanya"},
]


AVAILABILITY_TEMPLATES: list[dict[str, Any]] = [
    {"room_type": "Standard", "price": 4100.0, "allotment": 8, "stop_sale": False},
    {"room_type": "Deluxe", "price": 5350.0, "allotment": 5, "stop_sale": False},
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value) or "demo-agency"


def _stable_uuid(namespace: str, value: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{namespace}:{value}"))


def _temporary_password(slug: str) -> str:
    suffix = zlib.crc32(slug.encode("utf-8")) % 10000
    stem = slug.replace("-", "")[:8].title() or "Demo"
    return f"{stem}!{suffix:04d}"


def _admin_email(slug: str) -> str:
    return f"admin@{slug}.demo.test"


def _seed_rng(slug: str) -> random.Random:
    return random.Random(f"demo-seed:{slug}")


def _faker_pool(slug: str) -> dict[str, Faker]:
    seed = zlib.crc32(slug.encode("utf-8"))
    faker_tr = Faker("tr_TR")
    faker_de = Faker("de_DE")
    faker_en = Faker("en_GB")
    faker_tr.seed_instance(seed)
    faker_de.seed_instance(seed + 11)
    faker_en.seed_instance(seed + 29)
    return {"TR": faker_tr, "DE": faker_de, "EN": faker_en}


def _org_doc(agency_name: str, slug: str, org_id: str) -> dict[str, Any]:
    now = _now()
    return {
        "name": agency_name,
        "slug": f"demo-{slug}",
        "settings": {"currency": "TRY"},
        "plan": "pro",
        "features": {"b2b_pro": True},
        "updated_at": now,
    }




def _tenant_doc(agency_name: str, slug: str, org_id: str, tenant_id: str) -> dict[str, Any]:
    now = _now()
    return {
        "organization_id": org_id,
        "name": agency_name,
        "slug": f"demo-{slug}",
        "tenant_key": f"demo-{slug}",
        "status": "active",
        "is_active": True,
        "onboarding_completed": True,
        "updated_at": now,
    }


def create_demo_agency(db: Database, agency_name: str) -> dict[str, Any]:
    slug = _slugify(agency_name)
    org_id = _stable_uuid("demo-org", slug)
    tenant_id = _stable_uuid("demo-tenant", slug)
    agency_id = _stable_uuid("demo-agency", slug)
    admin_email = _admin_email(slug)
    temporary_password = _temporary_password(slug)

    db.organizations.update_one(
        {"_id": org_id},
        {
            "$set": {
                **_org_doc(agency_name, slug, org_id),
                "updated_at": _now(),
            },
            "$setOnInsert": {"created_at": _now()},
        },
        upsert=True,
    )

    db.tenants.update_one(
        {"_id": tenant_id},
        {
            "$set": {
                **_tenant_doc(agency_name, slug, org_id, tenant_id),
                "updated_at": _now(),
            },
            "$setOnInsert": {"created_at": _now()},
        },
        upsert=True,
    )

    agency_doc = {
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "name": agency_name,
        "discount_percent": 6.0,
        "commission_percent": 12.0,
        "status": "active",
        "is_active": True,
        "settings": {"selling_currency": "TRY"},
        "updated_at": _now(),
        "created_by": admin_email,
        "updated_by": admin_email,
    }
    db.agencies.update_one(
        {"_id": agency_id, "organization_id": org_id},
        {
            "$set": {**agency_doc, "updated_at": _now()},
            "$setOnInsert": {"created_at": _now()},
        },
        upsert=True,
    )

    db.tenant_capabilities.update_one(
        {"tenant_id": tenant_id},
        {
            "$set": {
                "tenant_id": tenant_id,
                "plan": "pro",
                "add_ons": [],
                "updated_at": _now(),
            },
            "$setOnInsert": {"created_at": _now()},
        },
        upsert=True,
    )

    trial_end = _now() + timedelta(days=14)
    db.subscriptions.update_one(
        {"tenant_id": tenant_id, "org_id": org_id},
        {
            "$set": {
                "tenant_id": tenant_id,
                "org_id": org_id,
                "plan": "pro",
                "status": "trialing",
                "billing_cycle": "monthly",
                "billing_enabled": False,
                "trial_start": _now(),
                "trial_end": trial_end,
                "period_start": _now(),
                "period_end": trial_end,
                "updated_at": _now(),
            },
            "$setOnInsert": {
                "_id": _stable_uuid("demo-subscription", slug),
                "created_at": _now(),
            },
        },
        upsert=True,
    )

    return {
        "slug": slug,
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "agency_id": agency_id,
        "agency_name": agency_name,
        "admin_email": admin_email,
        "temporary_password": temporary_password,
    }


def create_demo_user(db: Database, context: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    user_doc = {
        "organization_id": context["organization_id"],
        "tenant_id": context["tenant_id"],
        "agency_id": context["agency_id"],
        "email": context["admin_email"],
        "name": f"{context['agency_name']} Admin",
        "password_hash": hash_password(context["temporary_password"]),
        "roles": ["super_admin", "agency_admin"],
        "is_active": True,
        "updated_at": now,
    }
    db.users.update_one(
        {"organization_id": context["organization_id"], "email": context["admin_email"]},
        {
            "$set": user_doc,
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    user = db.users.find_one({"organization_id": context["organization_id"], "email": context["admin_email"]})
    if not user:
        raise RuntimeError("Demo admin user could not be created")

    db.memberships.update_one(
        {"user_id": str(user["_id"]), "tenant_id": context["tenant_id"]},
        {
            "$set": {
                "user_id": str(user["_id"]),
                "tenant_id": context["tenant_id"],
                "role": "admin",
                "status": "active",
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    return {"id": str(user["_id"]), "email": context["admin_email"], "temporary_password": context["temporary_password"]}


def seed_tours(db: Database, context: dict[str, Any]) -> list[dict[str, Any]]:
    tours: list[dict[str, Any]] = []
    for index, blueprint in enumerate(TOUR_BLUEPRINTS):
        created_at = _now() - timedelta(days=45 - (index * 4))
        update_doc = {
            "organization_id": context["organization_id"],
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
            "cover_image": "",
            "images": [],
            "itinerary": [
                f"{blueprint['destination']} karşılama ve başlangıç programı",
                "Bölgesel öne çıkan duraklarda rehberli gezi",
                "Misafir alışveriş / serbest zaman",
            ],
            "includes": blueprint["includes"],
            "excludes": blueprint["excludes"],
            "highlights": blueprint["highlights"],
            "updated_at": _now(),
        }
        db.tours.update_one(
            {"organization_id": context["organization_id"], "name": blueprint["name"]},
            {
                "$set": update_doc,
                "$setOnInsert": {"created_at": created_at},
            },
            upsert=True,
        )
        saved = db.tours.find_one({"organization_id": context["organization_id"], "name": blueprint["name"]})
        if not saved:
            raise RuntimeError(f"Tour could not be created: {blueprint['name']}")
        tours.append(saved)
    return tours


def _product_blueprint_for_tour(tour: dict[str, Any]) -> dict[str, Any]:
    return {
        "organization_id": tour["organization_id"],
        "title": tour["name"],
        "type": "tour",
        "description": tour.get("description"),
        "tour_id": tour["_id"],
        "updated_at": _now(),
        "created_by": "seed_demo_data",
        "updated_by": "seed_demo_data",
    }


def seed_supporting_products(db: Database, context: dict[str, Any], tours: list[dict[str, Any]]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for tour in tours:
        db.products.update_one(
            {"organization_id": context["organization_id"], "title": tour["name"], "type": "tour"},
            {
                "$set": {
                    **_product_blueprint_for_tour(tour),
                    "updated_at": _now(),
                },
                "$setOnInsert": {"created_at": _now()},
            },
            upsert=True,
        )
        product = db.products.find_one({"organization_id": context["organization_id"], "title": tour["name"], "type": "tour"})
        if not product:
            raise RuntimeError(f"Supporting product could not be created for {tour['name']}")
        products.append(product)

        db.rate_plans.update_one(
            {"organization_id": context["organization_id"], "product_id": product["_id"]},
            {
                "$set": {
                    "organization_id": context["organization_id"],
                    "product_id": product["_id"],
                    "name": f"{tour['name']} Standart Fiyat",
                    "currency": tour.get("currency") or "TRY",
                    "base_price": float(tour.get("base_price") or 0),
                    "seasons": [],
                    "actions": [],
                    "updated_at": _now(),
                    "updated_by": context["admin_email"],
                },
                "$setOnInsert": {
                    "created_at": _now(),
                    "created_by": context["admin_email"],
                },
            },
            upsert=True,
        )
    return products


def seed_hotels(db: Database, context: dict[str, Any]) -> list[dict[str, Any]]:
    hotels: list[dict[str, Any]] = []
    for index, blueprint in enumerate(HOTEL_BLUEPRINTS):
        hotel_id = _stable_uuid("demo-hotel", f"{context['slug']}:{blueprint['name']}")
        db.hotels.update_one(
            {"_id": hotel_id, "organization_id": context["organization_id"]},
            {
                "$set": {
                    "_id": hotel_id,
                    "organization_id": context["organization_id"],
                    "tenant_id": context["tenant_id"],
                    "name": blueprint["name"],
                    "city": blueprint["city"],
                    "country": blueprint["country"],
                    "stars": blueprint["stars"],
                    "address": blueprint["address"],
                    "phone": blueprint["phone"],
                    "email": blueprint["email"],
                    "description": blueprint["description"],
                    "active": True,
                    "updated_at": _now(),
                    "updated_by": context["admin_email"],
                },
                "$setOnInsert": {
                    "created_at": _now() - timedelta(days=120 - (index * 7)),
                    "created_by": context["admin_email"],
                },
            },
            upsert=True,
        )
        hotel = db.hotels.find_one({"_id": hotel_id, "organization_id": context["organization_id"]})
        if not hotel:
            raise RuntimeError(f"Hotel could not be created: {blueprint['name']}")
        hotels.append(hotel)

        db.agency_hotel_links.update_one(
            {
                "organization_id": context["organization_id"],
                "agency_id": context["agency_id"],
                "hotel_id": hotel_id,
            },
            {
                "$set": {
                    "organization_id": context["organization_id"],
                    "agency_id": context["agency_id"],
                    "hotel_id": hotel_id,
                    "active": True,
                    "commission_type": "percent",
                    "commission_value": 12.0,
                    "updated_at": _now(),
                    "updated_by": context["admin_email"],
                },
                "$setOnInsert": {
                    "_id": _stable_uuid("demo-agency-hotel-link", f"{context['agency_id']}:{hotel_id}"),
                    "created_at": _now(),
                    "created_by": context["admin_email"],
                },
            },
            upsert=True,
        )
    return hotels


def seed_customers(db: Database, context: dict[str, Any]) -> list[dict[str, Any]]:
    rng = _seed_rng(context["slug"])
    fakers = _faker_pool(context["slug"])
    customers: list[dict[str, Any]] = []

    for index in range(20):
        market = MARKETS[0] if index < 12 else MARKETS[1]
        faker = fakers["TR"] if market["code"] == "TR" else fakers["DE" if index % 2 == 0 else "EN"]
        name = faker.name()
        local_part = re.sub(r"[^a-z0-9]", "", name.lower().replace(" ", "."))[:18] or f"guest{index+1}"
        email = f"{local_part}.{context['slug'][:10]}.{index+1:02d}@demo.test"
        phone_prefix = "+90" if market["code"] == "TR" else "+49"
        phone = f"{phone_prefix}{rng.randint(5000000000, 5999999999)}"
        city = rng.choice(["İstanbul", "Antalya", "İzmir", "Nevşehir", "Denizli"])
        notes = f"{market['label']} pazarında teklif veren demo müşteri. İlgi alanı: {rng.choice(['kültür turu', 'yaz tatili', 'hafta sonu kaçamağı', 'premium şehir turu'])}."

        db.customers.update_one(
            {"organization_id": context["organization_id"], "email": email},
            {
                "$set": {
                    "organization_id": context["organization_id"],
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "notes": notes,
                    "city": city,
                    "market": market["code"],
                    "updated_at": _now(),
                    "updated_by": context["admin_email"],
                },
                "$setOnInsert": {
                    "created_at": _now() - timedelta(days=90 - index),
                    "created_by": context["admin_email"],
                },
            },
            upsert=True,
        )
        customer = db.customers.find_one({"organization_id": context["organization_id"], "email": email})
        if not customer:
            raise RuntimeError(f"Customer could not be created: {email}")
        customers.append(customer)
    return customers


def _inventory_departure_dates(base_day: datetime, item_count: int = 6) -> list[str]:
    return [(base_day + timedelta(days=offset * 4)).date().isoformat() for offset in range(item_count)]


def seed_product_inventory(db: Database, context: dict[str, Any], tours: list[dict[str, Any]], products: list[dict[str, Any]]) -> None:
    base_day = _now() + timedelta(days=4)
    for index, product in enumerate(products):
        tour = tours[index]
        for date_str in _inventory_departure_dates(base_day, 6):
            capacity_total = int(tour.get("max_participants") or 20)
            capacity_available = max(capacity_total - 6, 4)
            db.inventory.update_one(
                {"organization_id": context["organization_id"], "product_id": product["_id"], "date": date_str},
                {
                    "$set": {
                        "organization_id": context["organization_id"],
                        "product_id": product["_id"],
                        "date": date_str,
                        "capacity_total": capacity_total,
                        "capacity_available": capacity_available,
                        "price": float(tour.get("base_price") or 0),
                        "restrictions": {"closed": False, "cta": False, "ctd": False},
                        "source": "demo_seed",
                        "updated_at": _now(),
                        "updated_by": context["admin_email"],
                    },
                    "$setOnInsert": {
                        "created_at": _now(),
                        "created_by": context["admin_email"],
                    },
                },
                upsert=True,
            )


def seed_reservations(
    db: Database,
    context: dict[str, Any],
    tours: list[dict[str, Any]],
    products: list[dict[str, Any]],
    customers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rng = _seed_rng(f"{context['slug']}:reservations")
    reservations: list[dict[str, Any]] = []
    status_cycle = [
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
    base_day = _now() + timedelta(days=5)
    markets = ["TR"] * 18 + ["DE"] * 12

    for index in range(30):
        product = products[index % len(products)]
        tour = tours[index % len(tours)]
        customer = customers[index % len(customers)]
        market = markets[index]
        pax = rng.randint(1, 5)
        travel_date = (base_day + timedelta(days=index % 10, weeks=index // 10)).date().isoformat()
        base_price = float(tour.get("base_price") or 0)
        total_price = round(base_price * pax, 2)
        paid_amount = total_price if status_cycle[index % len(status_cycle)] == "paid" else round(total_price * rng.choice([0.0, 0.25, 0.5]), 2)
        status = status_cycle[index % len(status_cycle)]
        created_at = _now() - timedelta(days=rng.randint(2, 60), hours=rng.randint(1, 12))
        notes = rng.choice(
            [
                "Havalimanı transferi talep edildi.",
                "İngilizce rehber tercih edildi.",
                "VIP misafir karşılama istendi.",
                "Vejetaryen öğle yemeği notu alındı.",
                "",
            ]
        )
        reservation_payload = {
            "organization_id": context["organization_id"],
            "pnr": f"PNR-{context['slug'][:4].upper()}-{index + 1:04d}",
            "voucher_no": f"VCH-{context['slug'][:4].upper()}-{index + 1:04d}",
            "idempotency_key": f"demo:{context['slug']}:reservation:{index + 1}",
            "product_id": product["_id"],
            "customer_id": customer["_id"],
            "tour_id": tour["_id"],
            "tour_name": tour.get("name"),
            "product_title": product.get("title"),
            "customer_name": customer.get("name"),
            "customer_email": customer.get("email"),
            "customer_phone": customer.get("phone"),
            "guest_name": customer.get("name"),
            "guest_email": customer.get("email"),
            "guest_phone": customer.get("phone"),
            "start_date": travel_date,
            "end_date": None,
            "dates": [travel_date],
            "check_in": travel_date,
            "check_out": travel_date,
            "travel_date": travel_date,
            "pax": pax,
            "status": status,
            "currency": tour.get("currency") or "TRY",
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
            "channel": "b2b" if index % 3 == 0 else "direct",
            "agency_id": context["agency_id"],
            "agency_name": context["agency_name"],
            "market": market,
            "notes": notes,
            "payment_status": "paid" if status == "paid" else ("partially_paid" if paid_amount else "unpaid"),
            "created_at": created_at,
            "updated_at": _now(),
            "created_by": context["admin_email"],
            "updated_by": context["admin_email"],
        }
        if status == "confirmed":
            reservation_payload["confirmed_at"] = created_at + timedelta(hours=3)
            reservation_payload["confirmed_by"] = context["admin_email"]
        if status == "cancelled":
            reservation_payload["status_history"] = [
                {
                    "from_status": "confirmed",
                    "to_status": "cancelled",
                    "changed_by": context["admin_email"],
                    "changed_at": (_now() - timedelta(days=1)).isoformat(),
                    "reason": "Müşteri tarih değişikliği talep etti.",
                }
            ]

        db.reservations.update_one(
            {"organization_id": context["organization_id"], "idempotency_key": reservation_payload["idempotency_key"]},
            {
                "$set": {k: v for k, v in reservation_payload.items() if k != "created_at"},
                "$setOnInsert": {"created_at": created_at},
            },
            upsert=True,
        )
        saved = db.reservations.find_one(
            {"organization_id": context["organization_id"], "idempotency_key": reservation_payload["idempotency_key"]}
        )
        if not saved:
            raise RuntimeError(f"Reservation could not be created: {reservation_payload['idempotency_key']}")
        reservations.append(saved)
    return reservations


def seed_availability(db: Database, context: dict[str, Any], hotels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    availability_records: list[dict[str, Any]] = []
    start_day = _now() + timedelta(days=3)

    for hotel_index, hotel in enumerate(hotels):
        db.hotel_portfolio_sources.update_one(
            {
                "tenant_id": context["tenant_id"],
                "hotel_id": hotel["_id"],
                "agency_id": context["agency_id"],
                "source_type": "google_sheets",
            },
            {
                "$set": {
                    "organization_id": context["organization_id"],
                    "tenant_id": context["tenant_id"],
                    "hotel_id": hotel["_id"],
                    "hotel_name": hotel.get("name"),
                    "agency_id": context["agency_id"],
                    "agency_name": context["agency_name"],
                    "source_type": "google_sheets",
                    "sheet_id": f"demo-sheet-{hotel_index + 1}",
                    "sheet_tab": "Müsaitlik",
                    "writeback_tab": "Rezervasyonlar",
                    "mapping": {"date": "date", "room_type": "room_type", "price": "price", "allotment": "allotment"},
                    "sync_enabled": True,
                    "sync_interval_minutes": 5,
                    "last_sync_at": _now(),
                    "last_sync_status": "success",
                    "last_error": None,
                    "status": "active",
                    "updated_at": _now(),
                    "created_by": context["admin_email"],
                },
                "$setOnInsert": {
                    "_id": _stable_uuid("demo-sheet-connection", f"{context['tenant_id']}:{hotel['_id']}"),
                    "created_at": _now(),
                },
            },
            upsert=True,
        )

        for template_index, template in enumerate(AVAILABILITY_TEMPLATES):
            date_str = (start_day + timedelta(days=template_index + hotel_index)).date().isoformat()
            record = {
                "tenant_id": context["tenant_id"],
                "hotel_id": hotel["_id"],
                "date": date_str,
                "room_type": template["room_type"],
                "price": template["price"] + (hotel_index * 150),
                "allotment": template["allotment"] + (hotel_index % 3),
                "stop_sale": template["stop_sale"],
                "source": "demo_seed",
                "updated_at": _now(),
                "updated_by": context["admin_email"],
            }
            db.hotel_inventory_snapshots.update_one(
                {
                    "tenant_id": context["tenant_id"],
                    "hotel_id": hotel["_id"],
                    "date": date_str,
                    "room_type": template["room_type"],
                },
                {
                    "$set": record,
                    "$setOnInsert": {
                        "_id": _stable_uuid("demo-availability", f"{hotel['_id']}:{date_str}:{template['room_type']}"),
                        "created_at": _now(),
                    },
                },
                upsert=True,
            )
            availability_records.append(record)
    return availability_records


def reset_demo_data(db: Database, agency_name: str) -> None:
    slug = _slugify(agency_name)
    org_id = _stable_uuid("demo-org", slug)
    tenant_id = _stable_uuid("demo-tenant", slug)
    agency_id = _stable_uuid("demo-agency", slug)

    org_scoped_collections = [
        "agencies",
        "agency_hotel_links",
        "customers",
        "hotel_portfolio_sources",
        "hotels",
        "inventory",
        "memberships",
        "products",
        "rate_plans",
        "reservations",
        "tours",
        "users",
    ]
    tenant_scoped_collections = [
        "hotel_inventory_snapshots",
        "sheet_sync_runs",
        "tenant_capabilities",
        "tenant_entitlements",
        "tenant_features",
        "tenant_settings",
    ]

    for collection_name in org_scoped_collections:
        collection = db[collection_name]
        if collection_name == "memberships":
            collection.delete_many({"tenant_id": tenant_id})
            continue
        if collection_name == "agency_hotel_links":
            collection.delete_many({"organization_id": org_id, "agency_id": agency_id})
            continue
        if collection_name == "hotel_portfolio_sources":
            collection.delete_many({"tenant_id": tenant_id, "agency_id": agency_id})
            continue
        collection.delete_many({"organization_id": org_id})

    for collection_name in tenant_scoped_collections:
        db[collection_name].delete_many({"tenant_id": tenant_id})

    db.tenants.delete_one({"_id": tenant_id})
    db.organizations.delete_one({"_id": org_id})


def seed_demo_dataset(db: Database, agency_name: str, reset: bool = False) -> dict[str, Any]:
    if reset:
        reset_demo_data(db, agency_name)

    context = create_demo_agency(db, agency_name)
    user_info = create_demo_user(db, context)
    tours = seed_tours(db, context)
    products = seed_supporting_products(db, context, tours)
    hotels = seed_hotels(db, context)
    customers = seed_customers(db, context)
    seed_product_inventory(db, context, tours, products)
    reservations = seed_reservations(db, context, tours, products, customers)
    availability = seed_availability(db, context, hotels)

    return {
        "agency_name": context["agency_name"],
        "admin_email": user_info["email"],
        "temporary_password": user_info["temporary_password"],
        "organization_id": context["organization_id"],
        "tenant_id": context["tenant_id"],
        "agency_id": context["agency_id"],
        "counts": {
            "tours": len(tours),
            "hotels": len(hotels),
            "customers": len(customers),
            "reservations": len(reservations),
            "availability": len(availability),
        },
    }
