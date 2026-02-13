"""
Comprehensive fake data seeder for ALL screens.
Seeds: tours, partners, hotels, agencies, bookings, reservations, customers,
products, inventory, leads, quotes, CRM deals, CRM tasks, ops cases, ops tasks,
tickets, coupons, campaigns, CMS pages, financial entries, payments,
audit logs, booking events, notifications, b2b announcements, pricing rules, etc.
"""

import asyncio
import uuid
import random
import os
import sys
from datetime import datetime, timedelta, timezone
from bson import ObjectId

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from motor.motor_asyncio import AsyncIOMotorClient


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat()


def _uid():
    return str(uuid.uuid4())


def _past_days(days):
    return _now() - timedelta(days=days)


def _future_days(days):
    return _now() + timedelta(days=days)


# ─── Turkish Realistic Data ──────────────────────────────────────────

FIRST_NAMES = ["Ahmet", "Mehmet", "Ali", "Mustafa", "Hasan", "Hüseyin", "İbrahim", "Emre",
               "Burak", "Oğuz", "Kerem", "Cem", "Barış", "Serkan", "Tolga",
               "Ayşe", "Fatma", "Zeynep", "Elif", "Merve", "Selin", "Deniz", "Ceren",
               "Esra", "Gül", "Pınar", "Naz", "Sibel", "Derya", "Aslı"]

LAST_NAMES = ["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Yıldırım", "Öztürk",
              "Aydın", "Arslan", "Koç", "Erdoğan", "Taş", "Aksoy", "Güneş", "Kurt",
              "Doğan", "Kılıç", "Çetin", "Polat"]

CITIES = ["İstanbul", "Antalya", "İzmir", "Bodrum", "Fethiye", "Kapadokya", "Trabzon",
          "Çeşme", "Kuşadası", "Marmaris", "Alanya", "Belek", "Kemer", "Side", "Dalaman"]

HOTEL_NAMES = [
    "Grand Sapphire Hotel & Spa", "Riviera Palace Resort", "Aegean Breeze Hotel",
    "Ottoman Heritage Hotel", "Blue Lagoon Beach Resort", "Cappadocia Cave Suites",
    "Bosphorus View Hotel", "Mediterranean Pearl Resort", "Pine Valley Hotel",
    "Golden Sand Beach Hotel", "Sultan's Garden Hotel", "Lykia World Antalya",
    "Crystal Sunset Resort", "Titanic Deluxe Belek", "Kaya Palazzo Resort"
]

AGENCY_NAMES = [
    "Ege Tur Seyahat", "Akdeniz Holidays", "Anadolu Travel", "İstanbul Explorer Tours",
    "Türkiye Tatil Merkezi", "Mavi Yolculuk Turizm", "Kapadokya Dream Tours",
    "Olimpos Travel Agency", "Pamukkale Seyahat", "Efes Tourism Group"
]

TOUR_NAMES = [
    ("Kapadokya Balon Turu", "Kapadokya"),
    ("Ege Kıyıları Yat Turu", "Bodrum"),
    ("İstanbul Boğaz Turu", "İstanbul"),
    ("Pamukkale & Hierapolis", "Denizli"),
    ("Antalya Antik Kentler", "Antalya"),
    ("Likya Yolu Yürüyüş Turu", "Fethiye"),
    ("Efes Antik Kenti Turu", "İzmir"),
    ("Karadeniz Yayla Turu", "Trabzon"),
    ("Nemrut Dağı Güneş Turu", "Adıyaman"),
    ("Safranbolu Tarih Turu", "Karabük"),
    ("Göller Bölgesi Doğa Turu", "Isparta"),
    ("Mardin Taş Evler Turu", "Mardin"),
]

ROOM_TYPES = ["Standart Oda", "Deluxe Suite", "Aile Odası", "Ekonomik Oda", "Kral Dairesi",
              "Junior Suite", "Superior Oda", "Penthouse", "Bungalov"]

PARTNER_NAMES = [
    ("TravelPort Turkey", "info@travelport.com.tr"),
    ("HotelBeds Türkiye", "partners@hotelbeds.tr"),
    ("Booking Connect", "api@bookingconnect.com"),
    ("Gezinomi B2B", "b2b@gezinomi.com"),
    ("Tatilsepeti Pro", "pro@tatilsepeti.com"),
    ("Jolly Tur Entegrasyon", "entegrasyon@jollytur.com"),
    ("ETS Tur B2B", "b2b@etstur.com"),
    ("Coral Travel Partners", "partners@coraltravel.com.tr"),
]


async def seed_all():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    # Get org_id from existing user
    admin_user = await db.users.find_one({"email": "admin@acenta.test"})
    if not admin_user:
        admin_user = await db.users.find_one({"roles": {"$in": ["super_admin"]}})
    if not admin_user:
        print("ERROR: No admin user found. Please run the app first.")
        return

    org_id = admin_user["organization_id"]
    user_id = str(admin_user.get("_id", ""))
    user_email = admin_user.get("email", "admin@acenta.test")
    now = _now()

    print(f"Seeding data for org_id: {org_id}")

    # Get existing hotels and agencies
    existing_hotels = await db.hotels.find({"organization_id": org_id}).to_list(100)
    existing_agencies = await db.agencies.find({"organization_id": org_id}).to_list(100)

    hotel_ids = [str(h["_id"]) for h in existing_hotels]
    agency_ids = [str(a["_id"]) for a in existing_agencies]

    # ═══════════════════════════════════════════════════════════════════
    # 1. HOTELS (add more if less than 8)
    # ═══════════════════════════════════════════════════════════════════
    if len(existing_hotels) < 8:
        new_hotels = []
        used_names = {h.get("name") for h in existing_hotels}
        for name in HOTEL_NAMES:
            if name not in used_names and len(hotel_ids) < 10:
                hid = _uid()
                city = random.choice(CITIES)
                h = {
                    "_id": hid,
                    "organization_id": org_id,
                    "name": name,
                    "city": city,
                    "country": "TR",
                    "address": f"{city} Merkez, Sahil Caddesi No: {random.randint(1, 200)}",
                    "phone": f"+90 242 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}",
                    "email": f"info@{name.lower().replace(' ', '').replace('&', '')[:15]}.com",
                    "stars": random.choice([3, 4, 5]),
                    "active": True,
                    "rooms_count": random.randint(50, 300),
                    "created_at": _iso(_past_days(random.randint(30, 365))),
                    "updated_at": _iso(now),
                    "created_by": user_email,
                    "updated_by": user_email,
                }
                new_hotels.append(h)
                hotel_ids.append(hid)
        if new_hotels:
            await db.hotels.insert_many(new_hotels)
            print(f"  ✓ {len(new_hotels)} yeni otel eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 2. AGENCIES (add more if less than 6)
    # ═══════════════════════════════════════════════════════════════════
    if len(existing_agencies) < 6:
        new_agencies = []
        used_names = {a.get("name") for a in existing_agencies}
        for name in AGENCY_NAMES:
            if name not in used_names and len(agency_ids) < 8:
                aid = _uid()
                a = {
                    "_id": aid,
                    "organization_id": org_id,
                    "name": name,
                    "is_active": True,
                    "contact_email": f"info@{name.lower().replace(' ', '')[:12]}.com",
                    "contact_phone": f"+90 212 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}",
                    "city": random.choice(["İstanbul", "Ankara", "İzmir", "Antalya"]),
                    "settings": {"selling_currency": "TRY"},
                    "created_at": _iso(_past_days(random.randint(30, 180))),
                    "updated_at": _iso(now),
                    "created_by": user_email,
                    "updated_by": user_email,
                }
                new_agencies.append(a)
                agency_ids.append(aid)
        if new_agencies:
            await db.agencies.insert_many(new_agencies)
            print(f"  ✓ {len(new_agencies)} yeni acente eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 3. AGENCY-HOTEL LINKS
    # ═══════════════════════════════════════════════════════════════════
    existing_links = await db.agency_hotel_links.find({"organization_id": org_id}).to_list(500)
    existing_link_keys = {(l["agency_id"], l["hotel_id"]) for l in existing_links}
    new_links = []
    for aid in agency_ids:
        # Each agency links to 2-4 random hotels
        linked_hotels = random.sample(hotel_ids, min(random.randint(2, 4), len(hotel_ids)))
        for hid in linked_hotels:
            if (aid, hid) not in existing_link_keys:
                new_links.append({
                    "_id": _uid(),
                    "organization_id": org_id,
                    "agency_id": aid,
                    "hotel_id": hid,
                    "active": True,
                    "commission_type": "percent",
                    "commission_value": random.choice([8.0, 10.0, 12.0, 15.0]),
                    "created_at": _iso(_past_days(random.randint(10, 90))),
                    "updated_at": _iso(now),
                    "created_by": user_email,
                    "updated_by": user_email,
                })
                existing_link_keys.add((aid, hid))
    if new_links:
        await db.agency_hotel_links.insert_many(new_links)
        print(f"  ✓ {len(new_links)} yeni acente-otel bağlantısı eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 4. TOURS
    # ═══════════════════════════════════════════════════════════════════
    existing_tours_count = await db.tours.count_documents({"organization_id": org_id})
    if existing_tours_count < 5:
        tours = []
        for name, dest in TOUR_NAMES:
            tours.append({
                "organization_id": org_id,
                "type": "tour",
                "name": name,
                "name_search": name.lower(),
                "destination": dest,
                "base_price": float(random.choice([1500, 2500, 3500, 5000, 7500, 10000, 15000])),
                "currency": "EUR",
                "status": random.choice(["active", "active", "active", "draft"]),
                "duration_days": random.randint(1, 7),
                "max_participants": random.randint(10, 50),
                "description": f"{name} - Benzersiz bir deneyim için hemen rezervasyon yapın.",
                "created_at": _iso(_past_days(random.randint(5, 120))),
            })
        await db.tours.insert_many(tours)
        print(f"  ✓ {len(tours)} tur eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 5. PARTNERS (Partnership applications)
    # ═══════════════════════════════════════════════════════════════════
    existing_partners_count = await db.partners.count_documents({"organization_id": org_id})
    if existing_partners_count < 3:
        partners = []
        statuses = ["pending", "pending", "approved", "approved", "approved", "blocked", "pending", "approved"]
        for idx, (name, email) in enumerate(PARTNER_NAMES):
            partners.append({
                "organization_id": org_id,
                "name": name,
                "contact_email": email,
                "status": statuses[idx % len(statuses)],
                "api_key_name": f"api_key_{name.lower().replace(' ', '_')[:15]}",
                "default_markup_percent": random.choice([5.0, 8.0, 10.0, 12.0, 15.0]),
                "linked_agency_id": random.choice(agency_ids) if random.random() > 0.3 else None,
                "notes": f"{name} ile partnerlik başvurusu. " + random.choice([
                    "API entegrasyonu tamamlandı.", "Test aşamasında.", "Kontrat bekleniyor.",
                    "Müzakere sürecinde.", "Onay bekliyor."
                ]),
                "created_at": _iso(_past_days(random.randint(5, 90))),
                "updated_at": _iso(_past_days(random.randint(0, 5))),
            })
        await db.partners.insert_many(partners)
        print(f"  ✓ {len(partners)} partner başvurusu eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 6. CUSTOMERS
    # ═══════════════════════════════════════════════════════════════════
    existing_customers = await db.customers.find({"organization_id": org_id}).to_list(100)
    existing_cust_ids = [c.get("id", str(c.get("_id"))) for c in existing_customers]
    if len(existing_customers) < 15:
        new_customers = []
        for i in range(20):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            cid = f"cust_{_uid()[:8]}"
            new_customers.append({
                "id": cid,
                "organization_id": org_id,
                "type": random.choice(["individual", "individual", "corporate"]),
                "name": f"{first} {last}",
                "contacts": [
                    {"type": "email", "value": f"{first.lower()}.{last.lower()}@{random.choice(['gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com'])}", "is_primary": True},
                    {"type": "phone", "value": f"+90 5{random.randint(30, 59)}{random.randint(100, 999)}{random.randint(10, 99)}{random.randint(10, 99)}", "is_primary": False},
                ],
                "tags": random.sample(["VIP", "regular", "corporate", "new", "loyal", "repeat"], k=random.randint(0, 3)),
                "source": "seed",
                "city": random.choice(CITIES),
                "notes": random.choice(["", "Düzenli müşteri", "Kurumsal anlaşma var", "İlk ziyaret", ""]),
                "created_at": _iso(_past_days(random.randint(5, 365))),
                "updated_at": _iso(now),
            })
            existing_cust_ids.append(cid)
        await db.customers.insert_many(new_customers)
        print(f"  ✓ {len(new_customers)} müşteri eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 7. PRODUCTS
    # ═══════════════════════════════════════════════════════════════════
    existing_products = await db.products.find({"organization_id": org_id}).to_list(100)
    product_ids = [str(p.get("_id")) for p in existing_products]
    if len(existing_products) < 8:
        new_products = []
        for i, room_type in enumerate(ROOM_TYPES):
            pid = _uid()
            new_products.append({
                "_id": pid,
                "organization_id": org_id,
                "title": room_type,
                "type": "room",
                "description": f"{room_type} - Konforlu konaklama deneyimi",
                "price": float(random.choice([800, 1200, 1500, 2000, 2500, 3000, 4500, 6000])),
                "currency": "TRY",
                "status": "active",
                "source": "seed",
                "created_at": _iso(_past_days(random.randint(30, 180))),
                "updated_at": _iso(now),
            })
            product_ids.append(pid)
        await db.products.insert_many(new_products)
        print(f"  ✓ {len(new_products)} ürün eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 8. INVENTORY
    # ═══════════════════════════════════════════════════════════════════
    existing_inv_count = await db.inventory.count_documents({"organization_id": org_id})
    if existing_inv_count < 30:
        inventory_items = []
        for pid in product_ids[:6]:
            for day_offset in range(0, 45):
                date = (_now() + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                inventory_items.append({
                    "organization_id": org_id,
                    "product_id": pid,
                    "date": date,
                    "allotment": random.randint(2, 15),
                    "sold": random.randint(0, 5),
                    "blocked": random.randint(0, 2),
                    "price": float(random.randint(800, 5000)),
                    "currency": "TRY",
                    "min_stay": random.choice([1, 1, 1, 2, 3]),
                    "source": "seed",
                    "updated_at": _iso(now),
                })
        # Use bulk upsert to avoid duplicates
        for item in inventory_items:
            await db.inventory.update_one(
                {"organization_id": org_id, "product_id": item["product_id"], "date": item["date"]},
                {"$setOnInsert": item},
                upsert=True,
            )
        print(f"  ✓ {len(inventory_items)} envanter kaydı eklendi/güncellendi")

    # ═══════════════════════════════════════════════════════════════════
    # 9. RESERVATIONS
    # ═══════════════════════════════════════════════════════════════════
    existing_res_count = await db.reservations.count_documents({"organization_id": org_id})
    reservation_ids = []
    if existing_res_count < 10:
        reservations = []
        statuses = ["pending", "pending", "approved", "approved", "paid", "paid", "confirmed", "cancelled", "pending", "approved",
                    "paid", "confirmed", "pending", "approved", "paid"]
        guest_names_used = set()
        for i in range(20):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            guest = f"{first} {last}"
            days_ahead = random.randint(-10, 60)
            checkin = _now() + timedelta(days=days_ahead)
            nights = random.randint(1, 7)
            checkout = checkin + timedelta(days=nights)
            total = random.randint(2000, 25000)
            status = statuses[i % len(statuses)]
            res_id = _uid()
            pnr = f"PNR-{random.randint(100000, 999999)}"
            
            hotel_id = random.choice(hotel_ids) if hotel_ids else None
            agency_id = random.choice(agency_ids) if agency_ids else None
            
            reservations.append({
                "_id": res_id,
                "organization_id": org_id,
                "pnr": pnr,
                "status": status,
                "customer_name": guest,
                "customer_email": f"{first.lower()}.{last.lower()}@gmail.com",
                "customer_phone": f"+90 5{random.randint(30, 59)}{random.randint(1000000, 9999999)}",
                "customer_id": random.choice(existing_cust_ids) if existing_cust_ids and random.random() > 0.3 else None,
                "hotel_id": hotel_id,
                "hotel_name": random.choice(HOTEL_NAMES),
                "agency_id": agency_id,
                "room_type": random.choice(ROOM_TYPES),
                "product_id": random.choice(product_ids) if product_ids else None,
                "checkin": checkin,
                "checkout": checkout,
                "nights": nights,
                "adults": random.randint(1, 3),
                "children": random.randint(0, 2),
                "total": total,
                "cost": int(total * 0.7),
                "commission": int(total * 0.1),
                "currency": "TRY",
                "guests": random.randint(1, 4),
                "notes": random.choice(["", "Erken check-in talep edildi", "Deniz manzarası isteniyor", "VIP misafir", "Havaalanı transferi dahil"]),
                "source": "seed",
                "created_at": _iso(_past_days(random.randint(0, 30))),
                "updated_at": _iso(now),
            })
            reservation_ids.append(res_id)
        try:
            await db.reservations.insert_many(reservations, ordered=False)
        except Exception as e:
            print(f"  ⚠ Reservations partial insert: {e}")
        print(f"  ✓ {len(reservations)} rezervasyon eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 10. BOOKINGS
    # ═══════════════════════════════════════════════════════════════════
    existing_bookings_count = await db.bookings.count_documents({"organization_id": org_id})
    booking_ids = []
    if existing_bookings_count < 10:
        bookings = []
        booking_statuses = ["DRAFT", "PENDING_APPROVAL", "CONFIRMED", "CONFIRMED", "CANCELLED",
                           "PENDING_APPROVAL", "CONFIRMED", "DRAFT", "CONFIRMED", "REFUND_REQUESTED",
                           "CONFIRMED", "PENDING_APPROVAL", "CONFIRMED", "CANCELLED", "CONFIRMED"]
        for i in range(18):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            bid = f"BKG-{random.randint(10000, 99999)}"
            booking_id = _uid()
            days_ahead = random.randint(-15, 60)
            checkin = _now() + timedelta(days=days_ahead)
            checkout = checkin + timedelta(days=random.randint(1, 7))
            sell_amount = random.randint(3000, 30000)
            cost_amount = int(sell_amount * random.uniform(0.6, 0.85))
            status = booking_statuses[i % len(booking_statuses)]

            hotel_id = random.choice(hotel_ids) if hotel_ids else None
            agency_id = random.choice(agency_ids) if agency_ids else None

            bookings.append({
                "_id": booking_id,
                "booking_id": bid,
                "organization_id": org_id,
                "status": status,
                "state": status.lower(),
                "customer_name": f"{first} {last}",
                "customer_email": f"{first.lower()}.{last.lower()}@email.com",
                "customer_phone": f"+90 5{random.randint(30, 59)}{random.randint(1000000, 9999999)}",
                "customer_id": random.choice(existing_cust_ids) if existing_cust_ids else None,
                "hotel_id": hotel_id,
                "hotel_name": random.choice(HOTEL_NAMES),
                "agency_id": agency_id,
                "agency_name": random.choice(AGENCY_NAMES),
                "room_type": random.choice(ROOM_TYPES),
                "check_in": _iso(checkin),
                "check_out": _iso(checkout),
                "nights": (checkout - checkin).days,
                "adults": random.randint(1, 3),
                "children": random.randint(0, 2),
                "currency": "TRY",
                "amounts": {
                    "sell": sell_amount,
                    "cost": cost_amount,
                    "commission": sell_amount - cost_amount,
                    "net": cost_amount,
                },
                "source": random.choice(["B2B", "B2C", "manual", "B2B"]),
                "channel": random.choice(["b2b_portal", "web", "phone", "walk-in"]),
                "payment_status": random.choice(["unpaid", "partial", "paid", "paid", "unpaid"]),
                "notes": random.choice(["", "Özel istek: sessiz oda", "Erken check-in", "Geç check-out", "Transfer dahil"]),
                "submitted_at": _iso(_past_days(random.randint(0, 20))),
                "created_at": _iso(_past_days(random.randint(0, 30))),
                "updated_at": _iso(now),
                "created_by": user_email,
            })
            booking_ids.append(booking_id)
        await db.bookings.insert_many(bookings)
        print(f"  ✓ {len(bookings)} booking eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 11. LEADS
    # ═══════════════════════════════════════════════════════════════════
    existing_leads_count = await db.leads.count_documents({"organization_id": org_id})
    if existing_leads_count < 5:
        leads = []
        lead_statuses = ["new", "contacted", "qualified", "proposal", "won", "lost", "new", "contacted", "qualified", "new"]
        for i in range(12):
            cid = random.choice(existing_cust_ids) if existing_cust_ids else None
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            leads.append({
                "organization_id": org_id,
                "customer_id": cid,
                "customer_name": f"{first} {last}",
                "status": lead_statuses[i % len(lead_statuses)],
                "source": random.choice(["website", "referral", "phone", "social_media", "b2b"]),
                "notes": random.choice([
                    "Web sitesinden form doldurdu",
                    "Telefon ile arandı, teklif istedi",
                    "Referans ile geldi",
                    "Sosyal medya kampanyasından",
                    "B2B partnerden yönlendirildi",
                ]),
                "sort_index": random.randint(1, 100),
                "created_at": _iso(_past_days(random.randint(0, 30))),
                "updated_at": _iso(now),
            })
        await db.leads.insert_many(leads)
        print(f"  ✓ {len(leads)} lead eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 12. QUOTES
    # ═══════════════════════════════════════════════════════════════════
    existing_quotes_count = await db.quotes.count_documents({"organization_id": org_id})
    if existing_quotes_count < 5:
        quotes = []
        quote_statuses = ["draft", "sent", "accepted", "expired", "draft", "sent", "accepted", "sent"]
        for i in range(10):
            cid = random.choice(existing_cust_ids) if existing_cust_ids else None
            pid = random.choice(product_ids) if product_ids else None
            amount = random.randint(2000, 20000)
            quotes.append({
                "organization_id": org_id,
                "customer_id": cid,
                "product_id": pid,
                "product_name": random.choice(ROOM_TYPES),
                "hotel_name": random.choice(HOTEL_NAMES),
                "status": quote_statuses[i % len(quote_statuses)],
                "amount": amount,
                "currency": "TRY",
                "check_in": _iso(_future_days(random.randint(5, 60))),
                "check_out": _iso(_future_days(random.randint(8, 67))),
                "adults": random.randint(1, 3),
                "children": random.randint(0, 2),
                "valid_until": _iso(_future_days(random.randint(3, 14))),
                "notes": random.choice(["", "Özel fiyat uygulandı", "Sezon kampanyası dahil", "Erken rezervasyon indirimi"]),
                "created_at": _iso(_past_days(random.randint(0, 20))),
                "updated_at": _iso(now),
            })
        await db.quotes.insert_many(quotes)
        print(f"  ✓ {len(quotes)} teklif eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 13. CRM DEALS
    # ═══════════════════════════════════════════════════════════════════
    existing_deals_count = await db.crm_deals.count_documents({"organization_id": org_id})
    deal_ids = []
    if existing_deals_count < 5:
        deals = []
        deal_stages = ["new", "contacted", "proposal", "negotiation", "won", "lost", "new", "proposal", "won", "negotiation"]
        deal_titles = [
            "Yaz Sezonu Grup Rezervasyonu", "Kurumsal Toplantı Paketi", "Düğün Organizasyonu",
            "Konferans Rezervasyonu", "Balayı Paketi", "Hafta Sonu Konaklama",
            "Festival Katılım Paketi", "Kış Tatili Grubu", "Şirket Yıl Sonu Kutlaması",
            "Doğum Günü Organizasyonu"
        ]
        for i in range(10):
            did = f"deal_{_uid()[:8]}"
            stage = deal_stages[i % len(deal_stages)]
            status = "won" if stage == "won" else ("lost" if stage == "lost" else "open")
            deals.append({
                "id": did,
                "organization_id": org_id,
                "customer_id": random.choice(existing_cust_ids) if existing_cust_ids else None,
                "title": deal_titles[i % len(deal_titles)],
                "amount": random.choice([5000, 10000, 15000, 25000, 50000, 75000, 100000]),
                "currency": "TRY",
                "stage": stage,
                "status": status,
                "owner_user_id": user_id,
                "next_action_at": _iso(_future_days(random.randint(1, 14))),
                "source": "seed",
                "created_at": _iso(_past_days(random.randint(1, 60))),
                "updated_at": _iso(now),
            })
            deal_ids.append(did)
        await db.crm_deals.insert_many(deals)
        print(f"  ✓ {len(deals)} CRM deal eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 14. CRM TASKS
    # ═══════════════════════════════════════════════════════════════════
    existing_tasks_count = await db.crm_tasks.count_documents({"organization_id": org_id})
    if existing_tasks_count < 5:
        tasks = []
        task_titles = [
            "Müşteriye teklif gönder", "Fiyat güncelle", "Oda durumu kontrol et",
            "Depozito takibi", "Check-in hazırlığı", "Müşteri geri bildirimi al",
            "Sözleşme gönder", "Ödeme hatırlatması", "Rezervasyon onayla", "İade işlemi",
            "Fatura gönder", "Takip araması yap", "Sosyal medya paylaşımı", "Rapor hazırla"
        ]
        for i in range(15):
            tasks.append({
                "id": f"task_{_uid()[:8]}",
                "organization_id": org_id,
                "deal_id": random.choice(deal_ids) if deal_ids and random.random() > 0.3 else None,
                "customer_id": random.choice(existing_cust_ids) if existing_cust_ids and random.random() > 0.3 else None,
                "title": task_titles[i % len(task_titles)],
                "due_date": _iso(_future_days(random.randint(-5, 14))),
                "due_at": _iso(_future_days(random.randint(-5, 14))),
                "status": random.choice(["open", "open", "open", "done", "open", "done"]),
                "priority": random.choice(["low", "normal", "normal", "high"]),
                "assignee_user_id": user_id,
                "owner_user_id": user_id,
                "related_type": random.choice(["customer", "deal", "booking"]),
                "related_id": random.choice(existing_cust_ids) if existing_cust_ids else None,
                "source": "seed",
                "created_at": _iso(_past_days(random.randint(0, 20))),
                "updated_at": _iso(now),
            })
        await db.crm_tasks.insert_many(tasks)
        print(f"  ✓ {len(tasks)} CRM task eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 15. OPS CASES
    # ═══════════════════════════════════════════════════════════════════
    existing_cases_count = await db.ops_cases.count_documents({"organization_id": org_id})
    if existing_cases_count < 5:
        cases = []
        case_titles = [
            "Oda temizlik şikayeti", "Fatura sorunu", "Erken check-out talebi",
            "Oda değişikliği talebi", "Gürültü şikayeti", "Klima arızası",
            "Minibar fiyat itirazı", "Havuz kazası bildirimi", "Kayıp eşya bildirimi",
            "Transfer gecikmesi"
        ]
        for i in range(10):
            cid = f"case_{_uid()[:8]}"
            cases.append({
                "_id": cid,
                "case_id": cid,
                "organization_id": org_id,
                "title": case_titles[i % len(case_titles)],
                "description": f"Misafir {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)} tarafından bildirilen konu.",
                "status": random.choice(["open", "open", "in_progress", "resolved", "open"]),
                "priority": random.choice(["low", "medium", "high", "critical"]),
                "category": random.choice(["complaint", "request", "incident", "feedback"]),
                "booking_id": random.choice(booking_ids) if booking_ids else None,
                "hotel_id": random.choice(hotel_ids) if hotel_ids else None,
                "assignee_email": user_email,
                "source": "seed",
                "created_at": _iso(_past_days(random.randint(0, 14))),
                "updated_at": _iso(now),
            })
        await db.ops_cases.insert_many(cases)
        print(f"  ✓ {len(cases)} operasyon vakası eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 16. OPS TASKS
    # ═══════════════════════════════════════════════════════════════════
    existing_ops_tasks_count = await db.ops_tasks.count_documents({"organization_id": org_id})
    if existing_ops_tasks_count < 5:
        ops_tasks = []
        ops_task_titles = [
            "Müşteri şikayeti takibi", "Rezervasyon onay bekleniyor", "Ödeme kontrolü",
            "Otel ile iletişim kur", "Acente komisyon hesaplaması", "İade işlemi başlat",
            "Fatura düzenleme", "Transfer ayarlaması", "VIP misafir hazırlığı",
            "Sözleşme yenileme hatırlatması"
        ]
        for i in range(12):
            ops_tasks.append({
                "organization_id": org_id,
                "entity_type": random.choice(["booking", "refund_case", "reservation", "complaint"]),
                "entity_id": random.choice(booking_ids) if booking_ids else _uid(),
                "booking_id": random.choice(booking_ids) if booking_ids else None,
                "task_type": random.choice(["custom", "follow_up", "approval", "review"]),
                "title": ops_task_titles[i % len(ops_task_titles)],
                "description": f"Bu görev otomatik oluşturulmuştur. Acil takip gerektirir.",
                "status": random.choice(["open", "open", "in_progress", "done", "open"]),
                "priority": random.choice(["low", "normal", "high", "urgent"]),
                "due_at": _iso(_future_days(random.randint(-3, 10))),
                "sla_hours": random.choice([4, 8, 24, 48]),
                "is_overdue": random.choice([False, False, False, True]),
                "assignee_email": user_email,
                "tags": random.sample(["urgent", "vip", "finance", "complaint", "follow-up"], k=random.randint(0, 2)),
                "meta": {},
                "created_at": _iso(_past_days(random.randint(0, 10))),
                "updated_at": _iso(now),
                "created_by_email": user_email,
                "updated_by_email": user_email,
            })
        await db.ops_tasks.insert_many(ops_tasks)
        print(f"  ✓ {len(ops_tasks)} operasyon görevi eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 17. TICKETS
    # ═══════════════════════════════════════════════════════════════════
    existing_tickets_count = await db.tickets.count_documents({"organization_id": org_id})
    if existing_tickets_count < 3:
        tickets = []
        for i in range(8):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            ticket_code = f"TKT-{random.randint(100000, 999999)}"
            event_date = _iso(_future_days(random.randint(1, 30)))
            tickets.append({
                "organization_id": org_id,
                "tenant_id": org_id,
                "ticket_code": ticket_code,
                "reservation_id": random.choice(reservation_ids) if reservation_ids else _uid(),
                "product_name": random.choice(TOUR_NAMES)[0],
                "customer_name": f"{first} {last}",
                "customer_email": f"{first.lower()}.{last.lower()}@gmail.com",
                "customer_phone": f"+90 5{random.randint(30, 59)}{random.randint(1000000, 9999999)}",
                "event_date": event_date,
                "seat_info": f"Koltuk {random.randint(1, 50)}",
                "notes": random.choice(["", "VIP misafir", "Grup lideri", "Çocuklu aile"]),
                "status": random.choice(["active", "active", "checked_in", "active", "cancelled"]),
                "checked_in_at": None,
                "created_by": user_email,
                "created_at": _iso(_past_days(random.randint(0, 14))),
                "updated_at": _iso(now),
            })
        await db.tickets.insert_many(tickets)
        print(f"  ✓ {len(tickets)} bilet eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 18. COUPONS
    # ═══════════════════════════════════════════════════════════════════
    existing_coupons_count = await db.coupons.count_documents({"organization_id": org_id})
    if existing_coupons_count < 3:
        coupons = []
        coupon_data = [
            ("SUMMER25", "PERCENT", 25, "B2B"),
            ("WELCOME10", "PERCENT", 10, "BOTH"),
            ("EARLYBIRD", "PERCENT", 15, "B2C"),
            ("VIP500", "AMOUNT", 500, "B2B"),
            ("HOLIDAY20", "PERCENT", 20, "BOTH"),
            ("LASTMIN30", "PERCENT", 30, "B2C"),
            ("LOYAL100", "AMOUNT", 100, "B2B"),
        ]
        for code, dtype, value, scope in coupon_data:
            coupons.append({
                "organization_id": org_id,
                "code": code,
                "discount_type": dtype,
                "value": float(value),
                "scope": scope,
                "min_total": float(random.choice([0, 1000, 2000, 5000])),
                "usage_limit": random.choice([10, 50, 100, None]),
                "usage_count": random.randint(0, 15),
                "per_customer_limit": random.choice([1, 2, 5, None]),
                "valid_from": _past_days(10),
                "valid_to": _future_days(random.randint(30, 180)),
                "active": random.choice([True, True, True, False]),
                "created_at": _past_days(random.randint(5, 60)),
                "updated_at": now,
            })
        await db.coupons.insert_many(coupons)
        print(f"  ✓ {len(coupons)} kupon eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 19. CAMPAIGNS
    # ═══════════════════════════════════════════════════════════════════
    existing_campaigns_count = await db.campaigns.count_documents({"organization_id": org_id})
    if existing_campaigns_count < 2:
        campaigns = []
        campaign_data = [
            ("Yaz Erken Rezervasyon", "yaz-erken-rez", "Yaz sezonu için %25'e varan erken rezervasyon indirimleri", ["B2B", "B2C"]),
            ("Kış Tatili Kampanyası", "kis-tatili", "Kış tatili için özel fırsatlar. Kayak merkezleri ve termal oteller.", ["B2C"]),
            ("B2B Partner Özel", "b2b-partner-ozel", "B2B partnerlerimize özel indirimler ve komisyon avantajları.", ["B2B"]),
            ("Bayram Fırsatları", "bayram-firsatlari", "Bayram tatili için kaçırılmayacak fırsatlar!", ["B2B", "B2C"]),
            ("Balayı Paketi", "balayi-paketi", "Yeni evli çiftlere özel romantik konaklama paketleri.", ["B2C"]),
        ]
        for name, slug, desc, channels in campaign_data:
            campaigns.append({
                "organization_id": org_id,
                "name": name,
                "slug": slug,
                "description": desc,
                "active": random.choice([True, True, False]),
                "channels": channels,
                "valid_from": _iso(_past_days(random.randint(0, 30))),
                "valid_to": _iso(_future_days(random.randint(30, 180))),
                "coupon_codes": random.sample(["SUMMER25", "WELCOME10", "EARLYBIRD", "VIP500"], k=random.randint(0, 2)),
                "created_at": _iso(_past_days(random.randint(5, 60))),
                "updated_at": _iso(now),
            })
        await db.campaigns.insert_many(campaigns)
        print(f"  ✓ {len(campaigns)} kampanya eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 20. CMS PAGES
    # ═══════════════════════════════════════════════════════════════════
    existing_cms_count = await db.cms_pages.count_documents({"organization_id": org_id})
    if existing_cms_count < 2:
        cms_pages = []
        pages_data = [
            ("hakkimizda", "Hakkımızda", "page", "<h1>Hakkımızda</h1><p>Türkiye'nin önde gelen turizm platformu olarak 2015 yılından bu yana hizmet vermekteyiz.</p>"),
            ("gizlilik-politikasi", "Gizlilik Politikası", "page", "<h1>Gizlilik Politikası</h1><p>Kişisel verileriniz KVKK kapsamında korunmaktadır.</p>"),
            ("iletisim", "İletişim", "page", "<h1>İletişim</h1><p>Bize her zaman ulaşabilirsiniz. Tel: +90 212 555 00 00</p>"),
            ("yaz-firsatlari", "Yaz Fırsatları", "landing", "<h1>Yaz 2025 Fırsatları</h1><p>Bu yaz kaçırılmayacak tatil fırsatları!</p>"),
            ("sss", "Sıkça Sorulan Sorular", "page", "<h1>SSS</h1><p>Sıkça sorulan sorular ve cevapları.</p>"),
        ]
        for slug, title, kind, body in pages_data:
            cms_pages.append({
                "organization_id": org_id,
                "slug": slug,
                "title": title,
                "body": body,
                "kind": kind,
                "published": True,
                "seo_title": title,
                "seo_description": f"{title} - Detaylı bilgi için sayfamızı ziyaret edin.",
                "linked_campaign_slug": "",
                "created_at": _iso(_past_days(random.randint(10, 90))),
                "updated_at": _iso(now),
            })
        await db.cms_pages.insert_many(cms_pages)
        print(f"  ✓ {len(cms_pages)} CMS sayfası eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 21. B2B ANNOUNCEMENTS
    # ═══════════════════════════════════════════════════════════════════
    existing_ann_count = await db.b2b_announcements.count_documents({"organization_id": org_id})
    if existing_ann_count < 2:
        announcements = []
        ann_data = [
            ("Yeni Otel Portföyü Eklendi", "5 yeni otel portföyümüze eklenmiştir. Detaylar için otel kataloğumuzu inceleyiniz."),
            ("Sistem Bakımı Bildirimi", "25 Temmuz 2025 saat 02:00-04:00 arası planlı sistem bakımı yapılacaktır."),
            ("Yaz Sezonu Komisyon Güncelleme", "Yaz sezonu için komisyon oranları güncellenmiştir. Yeni oranlar 1 Ağustos'tan itibaren geçerlidir."),
            ("Yeni Ödeme Yöntemi: Havale/EFT", "Artık havale ve EFT ile de ödeme yapabilirsiniz. Banka bilgileri profil sayfanızda mevcuttur."),
        ]
        for title, body in ann_data:
            announcements.append({
                "organization_id": org_id,
                "title": title,
                "body": body,
                "audience": "all",
                "agency_id": None,
                "is_active": True,
                "valid_from": _iso(_past_days(random.randint(0, 10))),
                "valid_until": _iso(_future_days(random.randint(30, 90))),
                "created_at": _iso(_past_days(random.randint(0, 15))),
                "created_by": user_email,
            })
        await db.b2b_announcements.insert_many(announcements)
        print(f"  ✓ {len(announcements)} B2B duyurusu eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 22. BOOKING FINANCIAL ENTRIES
    # ═══════════════════════════════════════════════════════════════════
    existing_fin_count = await db.booking_financial_entries.count_documents({"organization_id": org_id})
    if existing_fin_count < 5:
        fin_entries = []
        for bid in (booking_ids[:10] if booking_ids else []):
            hotel_id = random.choice(hotel_ids) if hotel_ids else None
            agency_id = random.choice(agency_ids) if agency_ids else None
            sell = random.randint(3000, 20000)
            cost = int(sell * 0.7)
            commission = sell - cost
            month = random.choice(["2025-06", "2025-07", "2025-08", "2025-09"])
            fin_entries.append({
                "organization_id": org_id,
                "booking_id": bid,
                "hotel_id": hotel_id,
                "agency_id": agency_id,
                "type": "booking",
                "month": month,
                "sell_amount": sell,
                "cost_amount": cost,
                "commission_amount": commission,
                "currency": "TRY",
                "settlement_status": random.choice(["pending", "pending", "settled", "invoiced"]),
                "created_at": _iso(_past_days(random.randint(0, 30))),
                "updated_at": _iso(now),
            })
        if fin_entries:
            await db.booking_financial_entries.insert_many(fin_entries)
            print(f"  ✓ {len(fin_entries)} finansal kayıt eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 23. PAYMENTS
    # ═══════════════════════════════════════════════════════════════════
    existing_payments_count = await db.payments.count_documents({"organization_id": org_id})
    if existing_payments_count < 5:
        payments = []
        for i in range(12):
            amount = random.randint(1000, 15000)
            payments.append({
                "organization_id": org_id,
                "reservation_id": random.choice(reservation_ids) if reservation_ids else _uid(),
                "booking_id": random.choice(booking_ids) if booking_ids else None,
                "amount": amount,
                "currency": "TRY",
                "method": random.choice(["credit_card", "bank_transfer", "cash", "credit_card"]),
                "status": random.choice(["completed", "completed", "pending", "completed", "failed"]),
                "reference": f"PAY-{random.randint(100000, 999999)}",
                "notes": random.choice(["", "Kredi kartı ile ödeme", "Banka transferi", "Nakit ödeme"]),
                "payer_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                "created_at": _iso(_past_days(random.randint(0, 30))),
                "updated_at": _iso(now),
            })
        await db.payments.insert_many(payments)
        print(f"  ✓ {len(payments)} ödeme kaydı eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 24. AUDIT LOGS
    # ═══════════════════════════════════════════════════════════════════
    existing_audit_count = await db.audit_logs.count_documents({"organization_id": org_id})
    if existing_audit_count < 10:
        audit_logs = []
        actions = [
            ("booking.created", "booking"), ("booking.confirmed", "booking"),
            ("booking.cancelled", "booking"), ("reservation.created", "reservation"),
            ("payment.received", "payment"), ("customer.created", "customer"),
            ("hotel.updated", "hotel"), ("agency.created", "agency"),
            ("user.login", "user"), ("settings.updated", "settings"),
            ("coupon.created", "coupon"), ("deal.stage_changed", "deal"),
        ]
        for i in range(15):
            action, target_type = actions[i % len(actions)]
            audit_logs.append({
                "organization_id": org_id,
                "action": action,
                "actor": {
                    "actor_type": "user",
                    "actor_id": user_id,
                    "email": user_email,
                    "roles": ["super_admin"],
                },
                "target": {
                    "type": target_type,
                    "id": _uid()[:12],
                },
                "ip": f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
                "user_agent": "Mozilla/5.0",
                "meta": {"source": "seed"},
                "created_at": _iso(_past_days(random.randint(0, 14))),
            })
        await db.audit_logs.insert_many(audit_logs)
        print(f"  ✓ {len(audit_logs)} denetim kaydı eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 25. BOOKING EVENTS
    # ═══════════════════════════════════════════════════════════════════
    existing_events_count = await db.booking_events.count_documents({"organization_id": org_id})
    if existing_events_count < 5:
        events = []
        event_types = [
            "booking.created", "booking.confirmed", "booking.payment_received",
            "booking.cancelled", "booking.modified", "booking.checked_in",
            "booking.checked_out", "booking.whatsapp_clicked"
        ]
        for i in range(15):
            bid = random.choice(booking_ids) if booking_ids else _uid()
            events.append({
                "organization_id": org_id,
                "booking_id": bid,
                "entity_id": bid,
                "event_type": event_types[i % len(event_types)],
                "payload": {
                    "actor_email": user_email,
                    "source": "seed",
                },
                "delivered": random.choice([True, True, False]),
                "created_at": _iso(_past_days(random.randint(0, 14))),
            })
        await db.booking_events.insert_many(events)
        print(f"  ✓ {len(events)} booking event eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 26. NOTIFICATIONS
    # ═══════════════════════════════════════════════════════════════════
    existing_notif_count = await db.notifications.count_documents({"organization_id": org_id})
    if existing_notif_count < 3:
        notifications = []
        notif_data = [
            ("Yeni Rezervasyon", "Ahmet Yılmaz için yeni rezervasyon oluşturuldu.", "booking"),
            ("Ödeme Alındı", "BKG-12345 numaralı booking için ödeme alındı.", "payment"),
            ("Onay Bekliyor", "3 adet rezervasyon onayınızı bekliyor.", "approval"),
            ("Müşteri Şikayeti", "Yeni bir müşteri şikayeti oluşturuldu.", "case"),
            ("Komisyon Raporu", "Haziran ayı komisyon raporu hazır.", "report"),
            ("Sistem Güncellemesi", "Sistem başarıyla güncellendi.", "system"),
            ("İade Talebi", "BKG-54321 için iade talebi oluşturuldu.", "refund"),
            ("Partner Başvurusu", "Yeni partner başvurusu alındı.", "partner"),
        ]
        for title, body, category in notif_data:
            notifications.append({
                "organization_id": org_id,
                "user_id": user_id,
                "title": title,
                "body": body,
                "category": category,
                "is_read": random.choice([True, False, False]),
                "created_at": _iso(_past_days(random.randint(0, 10))),
            })
        await db.notifications.insert_many(notifications)
        print(f"  ✓ {len(notifications)} bildirim eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 27. EMAIL OUTBOX
    # ═══════════════════════════════════════════════════════════════════
    existing_email_count = await db.email_outbox.count_documents({"organization_id": org_id})
    if existing_email_count < 3:
        emails = []
        email_subjects = [
            "Rezervasyon Onayı - PNR-123456",
            "Ödeme Makbuzu - BKG-12345",
            "Hoş Geldiniz - Yeni Hesap",
            "Şifre Sıfırlama Talebi",
            "Aylık Rapor - Haziran 2025",
            "İade İşlemi Tamamlandı",
        ]
        for i, subject in enumerate(email_subjects):
            emails.append({
                "organization_id": org_id,
                "booking_id": random.choice(booking_ids) if booking_ids and random.random() > 0.3 else None,
                "to": f"{random.choice(FIRST_NAMES).lower()}.{random.choice(LAST_NAMES).lower()}@gmail.com",
                "subject": subject,
                "status": random.choice(["sent", "sent", "failed", "pending", "sent"]),
                "template": random.choice(["booking_confirmation", "payment_receipt", "welcome", "report"]),
                "retry_count": random.choice([0, 0, 0, 1, 2]),
                "next_retry_at": _iso(_future_days(1)) if random.random() > 0.8 else None,
                "created_at": _iso(_past_days(random.randint(0, 14))),
                "sent_at": _iso(_past_days(random.randint(0, 14))) if random.random() > 0.2 else None,
            })
        await db.email_outbox.insert_many(emails)
        print(f"  ✓ {len(emails)} e-posta kaydı eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 28. SETTLEMENTS
    # ═══════════════════════════════════════════════════════════════════
    existing_sett_count = await db.settlements.count_documents({"organization_id": org_id})
    if existing_sett_count < 3:
        settlements = []
        for i in range(6):
            hotel_id = random.choice(hotel_ids) if hotel_ids else None
            agency_id = random.choice(agency_ids) if agency_ids else None
            total = random.randint(10000, 100000)
            settlements.append({
                "organization_id": org_id,
                "hotel_id": hotel_id,
                "agency_id": agency_id,
                "period": random.choice(["2025-05", "2025-06", "2025-07"]),
                "total_amount": total,
                "commission_amount": int(total * 0.1),
                "net_amount": int(total * 0.9),
                "currency": "TRY",
                "status": random.choice(["pending", "approved", "paid", "pending"]),
                "booking_count": random.randint(3, 20),
                "notes": "",
                "created_at": _iso(_past_days(random.randint(5, 45))),
                "updated_at": _iso(now),
            })
        await db.settlements.insert_many(settlements)
        print(f"  ✓ {len(settlements)} mutabakat kaydı eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 29. B2B FUNNEL (Applications)
    # ═══════════════════════════════════════════════════════════════════
    existing_funnel_count = await db.b2b_applications.count_documents({"organization_id": org_id})
    if existing_funnel_count < 3:
        applications = []
        app_data = [
            ("Ege Turizm Ltd.", "pending", "İzmir"),
            ("Akdeniz Seyahat A.Ş.", "approved", "Antalya"),
            ("Marmara Travel", "pending", "İstanbul"),
            ("Kapadokya Tours", "approved", "Nevşehir"),
            ("Güneydoğu Holidays", "rejected", "Gaziantep"),
            ("Trakya Seyahat", "pending", "Edirne"),
            ("Doğu Express Turizm", "approved", "Erzurum"),
        ]
        for name, status, city in app_data:
            applications.append({
                "organization_id": org_id,
                "company_name": name,
                "contact_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                "contact_email": f"info@{name.lower().replace(' ', '').replace('.', '').replace('ş', 's').replace('ı', 'i')[:12]}.com",
                "contact_phone": f"+90 {random.randint(212, 542)} {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}",
                "city": city,
                "status": status,
                "notes": random.choice(["TÜRSAB belgeli", "Yeni başvuru", "Referans ile geldi", "Web formundan başvurdu"]),
                "monthly_booking_volume": random.choice([10, 25, 50, 100, 200]),
                "created_at": _iso(_past_days(random.randint(5, 60))),
                "updated_at": _iso(now),
            })
        await db.b2b_applications.insert_many(applications)
        print(f"  ✓ {len(applications)} B2B başvurusu eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 30. PRICING RULES (additional)
    # ═══════════════════════════════════════════════════════════════════
    existing_rules_count = await db.pricing_rules.count_documents({"organization_id": org_id})
    if existing_rules_count < 4:
        rules = []
        rule_data = [
            ("Kış Sezonu İndirimi", "discount_percent", 15.0, 300),
            ("VIP Acente Markupı", "markup_percent", 8.0, 250),
            ("Tur Ürünleri Komisyonu", "markup_percent", 12.0, 150),
            ("Erken Rezervasyon", "discount_percent", 20.0, 350),
        ]
        for notes, action_type, value, priority in rule_data:
            rules.append({
                "organization_id": org_id,
                "status": "active",
                "priority": priority,
                "scope": {"product_type": "hotel"},
                "validity": {"from": "2025-01-01", "to": "2026-12-31"},
                "action": {"type": action_type, "value": value},
                "notes": notes,
                "created_at": _iso(_past_days(random.randint(5, 60))),
                "updated_at": _iso(now),
                "created_by_email": user_email,
            })
        await db.pricing_rules.insert_many(rules)
        print(f"  ✓ {len(rules)} fiyatlandırma kuralı eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 31. WEBPOS PAYMENTS & LEDGER
    # ═══════════════════════════════════════════════════════════════════
    existing_webpos_count = await db.webpos_payments.count_documents({"organization_id": org_id})
    if existing_webpos_count < 3:
        webpos_payments = []
        webpos_ledger = []
        for i in range(8):
            pay_id = _uid()
            amount = random.choice([500, 1000, 1500, 2000, 3000, 5000])
            webpos_payments.append({
                "_id": pay_id,
                "organization_id": org_id,
                "amount": amount,
                "currency": "TRY",
                "method": random.choice(["cash", "credit_card", "bank_transfer"]),
                "reference": f"WP-{random.randint(100000, 999999)}",
                "note": random.choice(["Nakit ödeme", "Kredi kartı ile", "Havale", "EFT"]),
                "status": random.choice(["completed", "completed", "pending"]),
                "source": "seed",
                "created_at": _iso(_past_days(random.randint(0, 30))),
            })
            webpos_ledger.append({
                "_id": _uid(),
                "organization_id": org_id,
                "type": "debit",
                "amount": amount,
                "currency": "TRY",
                "reference_type": "payment",
                "reference_id": pay_id,
                "description": f"WebPOS ödeme - {amount} TRY",
                "source": "seed",
                "created_at": _iso(_past_days(random.randint(0, 30))),
            })
        await db.webpos_payments.insert_many(webpos_payments)
        await db.webpos_ledger.insert_many(webpos_ledger)
        print(f"  ✓ {len(webpos_payments)} WebPOS ödeme + {len(webpos_ledger)} muhasebe kaydı eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 32. HOTEL INTEGRATIONS
    # ═══════════════════════════════════════════════════════════════════
    existing_integrations_count = await db.hotel_integrations.count_documents({"organization_id": org_id})
    if existing_integrations_count < 2:
        integrations = []
        for hid in hotel_ids[:4]:
            integrations.append({
                "organization_id": org_id,
                "hotel_id": hid,
                "kind": random.choice(["channel_manager", "pms", "ota"]),
                "provider": random.choice(["Paximum", "SiteMinder", "RateGain", "HotelRunner"]),
                "status": random.choice(["active", "active", "error", "active"]),
                "last_sync_at": _iso(_past_days(random.randint(0, 3))),
                "config": {"api_key": "***hidden***"},
                "created_at": _iso(_past_days(random.randint(10, 90))),
                "updated_at": _iso(now),
            })
        # Use upsert to avoid duplicates
        for intg in integrations:
            await db.hotel_integrations.update_one(
                {"organization_id": org_id, "hotel_id": intg["hotel_id"], "kind": intg["kind"]},
                {"$setOnInsert": intg},
                upsert=True,
            )
        print(f"  ✓ {len(integrations)} otel entegrasyonu eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 33. INBOX MESSAGES
    # ═══════════════════════════════════════════════════════════════════
    existing_inbox_count = await db.inbox_messages.count_documents({"organization_id": org_id})
    if existing_inbox_count < 3:
        inbox_messages = []
        inbox_data = [
            ("Yeni rezervasyon onay bekliyor", "booking", "BKG-12345 numaralı rezervasyon onayınızı beklemektedir."),
            ("İade talebi oluşturuldu", "refund", "Müşteri Elif Demir iade talebinde bulunmuştur."),
            ("Partner başvurusu", "partner", "TravelPort Turkey partner başvurusu değerlendirmenizi bekliyor."),
            ("Ödeme hatırlatması", "payment", "3 adet ödeme bugün vadesi gelen fatura mevcut."),
            ("Otel güncelleme", "hotel", "Grand Sapphire Hotel fiyat güncellemesi gönderdi."),
        ]
        for title, category, body in inbox_data:
            inbox_messages.append({
                "organization_id": org_id,
                "user_id": user_id,
                "title": title,
                "body": body,
                "category": category,
                "is_read": random.choice([True, False, False]),
                "priority": random.choice(["normal", "high", "normal"]),
                "created_at": _iso(_past_days(random.randint(0, 7))),
            })
        await db.inbox_messages.insert_many(inbox_messages)
        print(f"  ✓ {len(inbox_messages)} gelen kutusu mesajı eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 34. CRM ACTIVITIES / NOTES
    # ═══════════════════════════════════════════════════════════════════
    existing_activities_count = await db.crm_activities.count_documents({"organization_id": org_id})
    if existing_activities_count < 3:
        activities = []
        activity_data = [
            ("call", "Müşteri ile telefon görüşmesi yapıldı. Teklif istedi."),
            ("email", "Fiyat teklifi e-posta ile gönderildi."),
            ("meeting", "Ofiste yüz yüze toplantı yapıldı."),
            ("note", "Müşteri VIP statüsüne yükseltildi."),
            ("call", "Müşteri arayarak ödeme bilgisi sordu."),
            ("email", "Rezervasyon onay e-postası gönderildi."),
        ]
        for atype, note in activity_data:
            activities.append({
                "organization_id": org_id,
                "customer_id": random.choice(existing_cust_ids) if existing_cust_ids else None,
                "type": atype,
                "note": note,
                "user_id": user_id,
                "user_email": user_email,
                "created_at": _iso(_past_days(random.randint(0, 20))),
            })
        await db.crm_activities.insert_many(activities)
        print(f"  ✓ {len(activities)} CRM aktivitesi eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # 35. B2B AGENCIES SUMMARY DATA  
    # ═══════════════════════════════════════════════════════════════════
    # Ensure all agencies have proper data for B2B dashboard
    for aid in agency_ids:
        agency = await db.agencies.find_one({"_id": aid, "organization_id": org_id})
        if agency and not agency.get("stats"):
            await db.agencies.update_one(
                {"_id": aid},
                {"$set": {
                    "stats": {
                        "total_bookings": random.randint(5, 100),
                        "total_revenue": random.randint(50000, 500000),
                        "active_reservations": random.randint(1, 15),
                        "last_booking_at": _iso(_past_days(random.randint(0, 7))),
                    },
                    "credit_limit": random.choice([50000, 100000, 200000, 500000]),
                    "credit_used": random.randint(0, 50000),
                }}
            )
    print(f"  ✓ Acente istatistikleri güncellendi")

    # ═══════════════════════════════════════════════════════════════════
    # 36. SETTLEMENT RUNS
    # ═══════════════════════════════════════════════════════════════════
    existing_runs_count = await db.settlement_runs.count_documents({"organization_id": org_id})
    if existing_runs_count < 2:
        runs = []
        for i in range(4):
            runs.append({
                "organization_id": org_id,
                "period": f"2025-0{random.randint(4, 7)}",
                "status": random.choice(["completed", "pending", "in_progress"]),
                "total_bookings": random.randint(10, 50),
                "total_amount": random.randint(50000, 300000),
                "total_commission": random.randint(5000, 30000),
                "currency": "TRY",
                "created_at": _iso(_past_days(random.randint(5, 45))),
                "updated_at": _iso(now),
                "created_by": user_email,
            })
        await db.settlement_runs.insert_many(runs)
        print(f"  ✓ {len(runs)} mutabakat çalıştırması eklendi")

    # ═══════════════════════════════════════════════════════════════════
    # DONE
    # ═══════════════════════════════════════════════════════════════════
    print("\n✅ Tüm fake data başarıyla eklendi! Ekranları kontrol edebilirsiniz.")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_all())
