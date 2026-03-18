# ACENTA BULUT OTOMASYONU — STRATEJİK ANALİZ & BÜYÜME PLANI

**Tarih:** 2026-03-19
**Analiz Seviyesi:** Enterprise SaaS Architect
**Mevcut Durum:** 7/10 → Hedef: 9/10

---

## 1. EXECUTIVE SUMMARY

Bu proje, Türkiye turizm sektöründe ciddi bir boşluğu dolduracak potansiyele sahip bir B2B SaaS acenta bulut otomasyonu. Ancak mevcut haliyle **"her şeyi yapan ama hiçbirini mükemmel yapmayan"** bir ürün konumunda.

**157K satır backend kodu, 236 router dosyası, 226 frontend sayfası** — bu ölçek, kontrol edilmezse teknik borç kara deliğine dönüşür.

**En kritik 3 bulgu:**
1. **Booking state machine tutarsızlığı** — 3 ayrı yerde 3 farklı state machine tanımlı. Bu, finansal işlemlerde veri kaybına neden olabilir.
2. **Mimari sprawl** — Modüller arasında net sınır yok. Tek bir FastAPI uygulamasında 236 router var. Bu, deploy, test ve scale edilemez.
3. **Ürün odaksızlığı** — CRM, PMS, B2B Marketplace, E-Fatura, WebPOS, Storefront, Tour Management, Campaign Engine... Hepsi yarım. Hiçbiri "WOW" seviyesinde değil.

**Sonuç:** Bu ürünü 9/10'a çıkarmak için en az %30'unu **kesmeli**, kalanını **birleştirmeli** ve çekirdek 3 modülü **mükemmelleştirmelisin**.

---

## 2. EN KRİTİK 10 AKSİYON

| # | Aksiyon | Etki | Süre | Öncelik |
|---|---------|------|------|---------|
| 1 | **Tek Booking State Machine'e geç** — 3 ayrı tanımı birleştir | Veri tutarlılığı, finansal güvenlik | 1 hafta | P0 |
| 2 | **Ürün kapsamını kes** — Core 3 modüle odaklan (Booking + Supplier + Finance) | Ürün netliği, geliştirme hızı | Anlık karar | P0 |
| 3 | **Domain Boundary çiz** — 5 bounded context tanımla | Mimari netlik | 2 hafta | P0 |
| 4 | **Router consolidation** — 236 router'ı domain bazlı 15-20'ye indir | Bakım kolaylığı, startup performansı | 2 hafta | P1 |
| 5 | **Event Bus'ı production-grade yap** — Outbox pattern + guaranteed delivery | Veri kaybı önleme | 2 hafta | P1 |
| 6 | **Multi-tenant izolasyonunu güçlendir** — Database-level isolation | Enterprise güvenlik, SOC2 uyumu | 3 hafta | P1 |
| 7 | **API versiyonlama** — /api/v1/ prefix ile geri uyumluluk | Enterprise satılabilirlik | 1 hafta | P1 |
| 8 | **Async job queue** — Celery/Redis ile ağır işlemleri ayır | Performans, ölçeklenme | 2 hafta | P1 |
| 9 | **Webhook sistemi kur** — Outbound event notification | Enterprise entegrasyon | 2 hafta | P2 |
| 10 | **Audit log'u compliance-ready yap** — Immutable, hash-chain | SOC2, KVKK | 1 hafta | P2 |

---

## 3. DETAYLI ANALİZ

---

### 3.1. ÜRÜN STRATEJİSİ (EN KRİTİK)

#### Bu ürün TAM OLARAK kime satılmalı?

**ICP (Ideal Customer Profile):**
- **Segment:** Türkiye'de otel satışı yapan outbound/inbound B2B acenteler
- **Büyüklük:** 5-50 çalışan arası
- **Aylık reservation hacmi:** 100-5.000 booking/ay
- **Mevcut durum:** Excel + WhatsApp + birden fazla supplier portal ile çalışıyor
- **Ağrı noktası:** Her supplier için ayrı portal, fiyat karşılaştırması manuel, finans takibi yok
- **Karar verici:** Acenta sahibi veya operasyon müdürü
- **Bütçe:** 500-3.000 TL/ay (50-300 USD/ay)

**1 Cümlelik Positioning:**
> "Tek panelden tüm supplier'lara bağlan, fiyat karşılaştır, rezervasyon yap, finansını takip et."

**Bu ürün neden alınır?**
Acente, 5 farklı supplier portalına giriş yapmak yerine tek panelden arama yapabilir, en iyi fiyatı görebilir ve booking yapabilir. Arkasında finans, settlement ve operasyon otomatik yürür.

#### Ürün Paketlemesi

**Kesilecek/Ertelenecek modüller (şu an değer üretmiyor):**

| Modül | Karar | Gerekçe |
|-------|-------|---------|
| WebPOS | ERTELE | B2B odağıyla uyumsuz, ayrı ürün olmalı |
| Storefront/Public Pages | ERTELE | B2C kanalı — ayrı ürün olmalı |
| Tour Management | ERTELE | Farklı vertical, ayrı ürün |
| Campaign Engine | ERTELE | Premature optimization, müşteri yokken kampanya anlamsız |
| CMS Pages | ERTELE | B2B SaaS'ta gereksiz |
| AI Assistant | ERTELE | Gimmick, core değer değil |
| PMS Integration (Hotel-side) | ERTELE | Hotel management ayrı bir ürün |
| SEO Router | ERTELE | B2B ürününe SEO gereksiz |
| Stress Testing Router | KES | Production'da olmamalı |
| Demo Scale UI Proof | KES | Dev aracı, production'da olmamalı |

**Kalacak Core Modüller:**

```
TIER 1 — ÇEKIRÇEK (Core - Her planda)
├── Supplier Hub (Paximum, RateHawk, Hotelbeds, Juniper)
│   ├── Multi-supplier arama
│   ├── Fiyat karşılaştırma
│   └── Unified booking
├── Booking Management (OMS)
│   ├── Order lifecycle
│   ├── Booking state machine
│   └── Voucher generation
└── Finance Core
    ├── Settlement tracking
    ├── Commission calculation
    └── Basic reporting

TIER 2 — PROFESSIONAL (Mid-tier)
├── B2B Network
│   ├── Agency-to-agency sales
│   ├── Inventory sharing
│   └── B2B marketplace
├── CRM
│   ├── Customer management
│   ├── Deal pipeline
│   └── Activity timeline
└── Advanced Finance
    ├── E-Fatura entegrasyonu
    ├── Multi-currency
    └── Credit exposure

TIER 3 — ENTERPRISE (Premium)
├── RBAC & Approval Workflows
├── Audit Logs (SOC2 compliant)
├── API Keys & Webhooks
├── White-label
├── Multi-tenant management
└── Accounting integration (Parasut, etc.)
```

**Pricing Önerisi:**

| Plan | Fiyat | Hedef |
|------|-------|-------|
| **Starter** | 499 TL/ay | 1-5 kullanıcı, 2 supplier, Tier 1 |
| **Professional** | 1.499 TL/ay | 10 kullanıcı, tüm supplier'lar, Tier 1+2 |
| **Enterprise** | 3.999 TL/ay | Sınırsız kullanıcı, Tier 1+2+3 |
| **Custom** | Görüşme ile | On-premise, özel entegrasyon |

---

### 3.2. MİMARİ REFAKTOR PLANI

#### Mevcut Yapı — Sorunlar

```
MEVCUT DURUM (Big Ball of Mud):

FastAPI (TEK UYGULAMA)
├── 236 router dosyası (!)
├── ~200 service dosyası
├── 30+ middleware katmanı
├── 3 FARKLI booking state machine
├── Servisler birbirini direkt import ediyor
├── Her yeni özellik router_registry.py'ye manual ekleme
└── 157K satır Python (!)
```

**En tehlikeli sorunlar:**

1. **3 Farklı State Machine:**
   - `app/domain/booking_state_machine.py` → draft/quoted/booked/hold
   - `app/constants/booking_statuses.py` → draft/pending/confirmed/rejected
   - `app/suppliers/state_machine.py` → draft/search_completed/price_validated/hold_created/payment_pending/...
   - `app/services/booking_lifecycle.py` → PENDING/CONFIRMED/CANCELLED (string based)
   
   Bunlar birbirinden BAĞIMSIZ çalışıyor. Bir booking hem `confirmed` hem `price_validated` olabilir. **Bu finansal felaket.**

2. **Circular import riski:** Service'ler birbirini direkt import ediyor, dependency injection yok.

3. **Router sprawl:** 236 dosya, her biri 50-500 satır. Aynı domain'e ait endpoint'ler 5+ dosyaya dağılmış.

#### Hedef Mimari — Modular Monolith

```
HEDEF DURUM (Modular Monolith):

FastAPI
├── modules/
│   ├── booking/           ← Bounded Context #1
│   │   ├── router.py      (tek router, tüm booking endpoint'leri)
│   │   ├── service.py     (iş mantığı)
│   │   ├── repository.py  (veri erişim)
│   │   ├── models.py      (domain modelleri + TEK state machine)
│   │   ├── events.py      (domain event tanımları)
│   │   └── schemas.py     (API request/response)
│   │
│   ├── supplier/          ← Bounded Context #2
│   │   ├── router.py
│   │   ├── service.py     (aggregation, routing)
│   │   ├── adapters/      (paximum, ratehawk, hotelbeds)
│   │   ├── models.py      (offer, availability)
│   │   ├── cache.py       (offer cache)
│   │   └── schemas.py
│   │
│   ├── finance/           ← Bounded Context #3
│   │   ├── router.py
│   │   ├── settlement_service.py
│   │   ├── commission_engine.py
│   │   ├── ledger.py
│   │   └── schemas.py
│   │
│   ├── crm/               ← Bounded Context #4
│   │   ├── router.py
│   │   ├── service.py
│   │   └── schemas.py
│   │
│   └── identity/          ← Bounded Context #5
│       ├── router.py      (auth, users, tenants, RBAC)
│       ├── tenant_service.py
│       └── auth_service.py
│
├── shared/
│   ├── event_bus.py       (outbox pattern)
│   ├── middleware/
│   ├── database.py
│   └── config.py
│
└── infrastructure/
    ├── redis.py
    ├── celery.py
    └── monitoring.py
```

#### Domain Boundary Kuralları

```
MODÜLLER ARASI İLETİŞİM KURALLARI:

1. Booking modülü Finance modülünü DIREKT ÇAĞIRAMAZ
   → Event yayınlar: "booking.confirmed" 
   → Finance modülü subscribe olup settlement oluşturur

2. Supplier modülü Booking modülünü DIREKT ÇAĞIRAMAZ  
   → Supplier response döner
   → Booking modülü sonucu işler

3. Modüller arası tek paylaşılan: shared/ altındaki interface'ler

4. Her modülün kendi repository'si var, başka modülün collection'ına direkt erişemez
```

#### Refactor Adım Planı (Kırılmadan, İncremental)

**Adım 1 — State Machine Birleştirme (Hafta 1)**
```
TEK STATE MACHINE:

draft → pending_supplier → supplier_confirmed → payment_pending → 
payment_completed → confirmed → voucher_issued

Side paths:
  confirmed → amendment_requested → amended → confirmed
  confirmed → cancellation_requested → cancelled → refund_pending → refunded
  ANY → failed

Supplier-specific sub-states:
  pending_supplier.paximum_on_request
  pending_supplier.ratehawk_pending
  (Supplier adapter'lar kendi sub-state'lerini yönetir)
```

Implementasyon:
- `booking_statuses.py`, `booking_state_machine.py`, `suppliers/state_machine.py` → tek `modules/booking/models.py`
- Migration script: mevcut booking'lerin state'lerini yeni state'lere map et
- Tüm service'lerdeki referansları güncelle

**Adım 2 — Router Consolidation (Hafta 2-3)**
```
Mevcut 236 router → 15-20 domain router

Örnek birleştirme:
  admin_b2b_agencies.py + admin_b2b_announcements.py + admin_b2b_discounts.py + 
  admin_b2b_funnel.py + admin_b2b_marketplace.py + admin_b2b_pricing.py + 
  admin_b2b_visibility.py + b2b.py + b2b_announcements.py + b2b_bookings.py + 
  b2b_bookings_list.py + b2b_events.py + b2b_exchange.py + b2b_hotels_search.py + 
  b2b_marketplace_booking.py + b2b_network_bookings.py + b2b_portal.py + b2b_quotes.py
  
  → modules/b2b/router.py (TEK dosya, section'lara bölünmüş)
```

**Adım 3 — Event-Driven Decoupling (Hafta 3-4)**
- Sheet writeback hook'larını `booking_lifecycle.py`'den çıkar
- Event bus'a subscribe et
- Outbox pattern implementasyonu (aşağıda detay)

**Adım 4 — Module Extraction (Hafta 5-8)**
- Her modülü kendi dizinine taşı
- Interface tanımla (Protocol class'lar)
- Integration testleri yaz

**Future Microservice Adayları:**
1. `supplier/` — Bağımsız deploy, farklı scaling
2. `finance/` — Compliance gereksinimleri nedeniyle izole
3. `identity/` — Auth ve tenant management

---

### 3.3. SCALABILITY & INFRA

#### Queue Sistemi

**Karar: Celery + Redis (Broker) + MongoDB (Result Backend)**

Neden Kafka değil:
- Booking hacmi yıllık 100K-1M arası. Kafka over-engineering.
- Celery + Redis, mevcut stack'le uyumlu.
- MongoDB zaten mevcut, result backend olarak kullanılabilir.

**Async olması gereken işler:**

| İş | Mevcut | Hedef | Öncelik |
|----|--------|-------|---------|
| Supplier search aggregation | Sync | Async (fanout → merge) | P0 |
| PDF voucher generation | Sync | Async queue | P1 |
| Settlement calculation | Sync | Async batch | P1 |
| Email/SMS notification | Sync (in-process) | Async queue | P1 |
| Sheet writeback | Sync (hook inside lifecycle) | Async event handler | P1 |
| Report generation | Sync | Async queue | P2 |
| E-Fatura push | Sync | Async queue | P2 |
| Accounting sync | Cron | Event-triggered async | P2 |

**Celery Task Tanımı:**
```python
# tasks/supplier_tasks.py
@celery.task(bind=True, max_retries=3, default_retry_delay=5)
def search_supplier(self, supplier_name: str, search_params: dict):
    """Fan-out: Her supplier için paralel search."""
    
# tasks/notification_tasks.py  
@celery.task(bind=True, max_retries=5)
def send_booking_confirmation(self, booking_id: str, channel: str):
    """Email + SMS notification."""

# tasks/finance_tasks.py
@celery.task
def calculate_settlement(booking_id: str):
    """Booking onaylandığında settlement hesapla."""
```

#### DB Optimizasyonu

**Mevcut sorun:** Tüm collection'lar aynı MongoDB database'de, index stratejisi dağınık.

**Yapılacaklar:**

1. **Compound index audit:**
```javascript
// Booking aramaları için:
db.bookings.createIndex({
  "organization_id": 1, 
  "status": 1, 
  "check_in": 1
})

// Settlement aramaları için:
db.settlement_ledger.createIndex({
  "seller_tenant_id": 1, 
  "period": 1, 
  "status": 1
})

// Event replay için:
db.domain_events.createIndex({
  "organization_id": 1, 
  "event_type": 1, 
  "timestamp": -1
})
```

2. **Read replica kullan** — Dashboard ve raporlama sorguları read replica'ya yönlendir.

3. **Collection partitioning** — Yüksek hacimli collection'lar (events, audit_logs) için TTL index + archiving.

#### Multi-Tenant İzolasyon Güçlendirme

**Mevcut durum:** `organization_id` field'ı ile "soft" izolasyon. Middleware seviyesinde tenant resolution.

**Sorunlar:**
- Bir query'de `organization_id` filtreyi unutursan, cross-tenant data leak.
- Auto-repair membership (tenant_middleware.py line 59-61) — production'da tehlikeli.
- Tenant context `ContextVar` ile taşınıyor ama repository seviyesinde zorunlu değil.

**Çözüm — 3 katmanlı izolasyon:**

```
Katman 1: Middleware (mevcut) — Request bazlı tenant resolution
Katman 2: Repository Guard — Her query'ye otomatik organization_id filtresi
Katman 3: Database (opsiyonel) — Tenant başına collection prefix
```

```python
# Katman 2 implementasyonu:
class TenantAwareRepository:
    def __init__(self, db, collection_name: str, tenant_id: str):
        self._collection = db[collection_name]
        self._tenant_id = tenant_id
    
    def _apply_tenant_filter(self, query: dict) -> dict:
        """Her query'ye otomatik tenant filtresi ekle."""
        return {**query, "organization_id": self._tenant_id}
    
    async def find_one(self, query: dict, **kwargs):
        return await self._collection.find_one(
            self._apply_tenant_filter(query), **kwargs
        )
    
    async def find(self, query: dict, **kwargs):
        return self._collection.find(
            self._apply_tenant_filter(query), **kwargs
        )
```

#### Cache Stratejisi

```
CACHE HİYERARŞİSİ:

L0: In-memory (functools.lru_cache) → Config, feature flags, plan matrix
    TTL: Uygulama restart'a kadar
    
L1: Redis → Supplier offer cache, session cache, rate limit counters
    TTL: Offer'lar için expiresOn, session için 8 saat
    
L2: MongoDB → Query result cache (dashboard aggregations, report data)
    TTL: 5-15 dakika

CACHE INVALIDATION:
- Event-driven: booking.confirmed → invalidate dashboard cache
- TTL-based: Offer cache'ler supplier'ın belirlediği TTL ile expire
- Manual: Admin panel'den "Cache Temizle" butonu (mevcut)
```

---

### 3.4. DOMAIN MODEL & DATA CONSISTENCY

#### Unified Booking Model

**Mevcut 3 farklı booking temsili:**

```
booking_state_machine.py:  draft → quoted → booked → cancel_requested
booking_statuses.py:       draft → pending → confirmed → rejected
suppliers/state_machine.py: draft → search_completed → price_validated → ...
booking_lifecycle.py:      BOOKING_CREATED → BOOKING_CONFIRMED → BOOKING_CANCELLED
```

**Bu kaos nasıl düzeltilir?**

**TEK BİRLEŞİK MODEL:**

```python
class BookingStatus(str, Enum):
    # Creation
    DRAFT = "draft"
    
    # Supplier interaction
    QUOTED = "quoted"                    # Supplier'dan fiyat alındı
    AVAILABILITY_CONFIRMED = "avail_ok"  # Fiyat + müsaitlik doğrulandı
    
    # Payment
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_COMPLETED = "payment_completed"
    
    # Supplier confirmation  
    PENDING_SUPPLIER = "pending_supplier"  # Supplier'a booking gönderildi
    CONFIRMED = "confirmed"                # Supplier onayladı
    ON_REQUEST = "on_request"              # Supplier manuel onay bekliyor
    
    # Fulfillment
    VOUCHER_ISSUED = "voucher_issued"
    CHECKED_IN = "checked_in"
    COMPLETED = "completed"
    
    # Cancellation/Refund
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    
    # Error
    FAILED = "failed"
    REJECTED = "rejected"
```

#### State Flow

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
DRAFT ──→ QUOTED ──→ AVAIL_OK ──→ PAYMENT_PENDING ──→ PAYMENT_COMPLETED
                                                              │
                    ┌─────────────────────────────────────────┘
                    │
              PENDING_SUPPLIER ──→ CONFIRMED ──→ VOUCHER_ISSUED ──→ COMPLETED
                    │                   │
                    ├→ ON_REQUEST ───────┘
                    │
                    └→ REJECTED / FAILED
                    
CANCEL PATH:
  CONFIRMED ──→ CANCEL_REQUESTED ──→ CANCELLED ──→ REFUND_PENDING ──→ REFUNDED
```

#### Veri Doğruluğu Stratejisi

**Problem 1: Booking + Finance senkronizasyon**

Mevcut: `booking_lifecycle.py` içinde inline hook'lar (sheet writeback, status update). Finance settlement'ı ayrı çağrılıyor.

**Çözüm: Transactional Outbox Pattern**

```python
async def confirm_booking(booking_id: str):
    async with await get_db().client.start_session() as session:
        async with session.start_transaction():
            # 1. Booking status güncelle
            await db.bookings.update_one(
                {"_id": booking_id},
                {"$set": {"status": "confirmed"}},
                session=session
            )
            
            # 2. Outbox'a event yaz (AYNI TRANSACTİON)
            await db.outbox_events.insert_one({
                "event_type": "booking.confirmed",
                "payload": {"booking_id": booking_id},
                "status": "pending",
                "created_at": now_utc()
            }, session=session)
    
    # 3. Outbox processor (ayrı worker) event'i publish eder
    # → Finance settlement oluşturur
    # → Sheet writeback yapar
    # → Notification gönderir
```

**Avantaj:** Booking güncellemesi ve event yayınlama ATOMIK. Event kaybolmaz.

**Problem 2: Supplier booking ile OMS booking senkronizasyonu**

Mevcut: `paximum_service.py` supplier booking yaratıyor, `order_service.py` OMS order yaratıyor. İkisi bağımsız.

**Çözüm:**
```
OMS Order (parent)
  └── Booking Item (child) ← Supplier booking response
      ├── supplier_ref: "PAX-12345"
      ├── supplier_status: "Confirmed" (raw supplier status)
      ├── oms_status: "confirmed" (mapped via status_mapping.py)
      └── financial_snapshot: {cost, sell, margin}
```

Her booking item, supplier tarafındaki durumu ve OMS tarafındaki durumu AYRI tutar. `status_mapping.py` bu ikisini senkronize eder.

**Problem 3: Race condition — aynı offer'a iki ayrı booking**

**Çözüm: Distributed Lock + Offer Reservation**
```python
async def reserve_offer(offer_id: str, booking_id: str):
    lock_key = f"offer_lock:{offer_id}"
    # Redis SETNX ile atomic lock
    acquired = await redis.set(lock_key, booking_id, nx=True, ex=120)
    if not acquired:
        raise OfferAlreadyReservedException()
    return True
```

---

### 3.5. ENTERPRISE & SATILABİLİRLİK

#### API Versiyonlama

**Mevcut:** Versiyon yok. Tüm endpoint'ler `/api/...` altında.

**Yapılacak:**

```python
# Phase 1: Prefix-based versioning
app.include_router(booking_router, prefix="/api/v1/bookings")

# Phase 2: Header-based versioning (gelecek)
# Accept: application/vnd.acenta.v2+json
```

**Versiyonlama kuralı:**
- Breaking change = yeni versiyon (v2)
- Additive change = mevcut versiyonda (v1'e yeni field ekle)
- Eski versiyon 12 ay desteklenir, sonra deprecated

**API Standardı:**

```json
// Başarılı yanıt
{
  "data": { ... },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-03-19T10:00:00Z"
  }
}

// Hata yanıtı
{
  "error": {
    "code": "BOOKING_NOT_FOUND",
    "message": "Booking bulunamadı",
    "details": { "booking_id": "..." },
    "request_id": "req_abc123"
  }
}

// Liste yanıtı
{
  "data": [ ... ],
  "pagination": {
    "total": 150,
    "page": 1,
    "per_page": 20,
    "total_pages": 8
  }
}
```

#### Webhook Sistemi

```python
# Webhook subscription model
{
    "webhook_id": "wh_xxx",
    "tenant_id": "t_xxx",
    "url": "https://customer.com/webhook",
    "events": ["booking.confirmed", "booking.cancelled"],
    "secret": "whsec_xxx",  # HMAC imzalama için
    "status": "active",
    "created_at": "..."
}

# Delivery mechanism
async def deliver_webhook(webhook_id: str, event: dict):
    """Exponential backoff ile webhook teslimi."""
    # 1. Payload oluştur
    # 2. HMAC-SHA256 ile imzala (X-Webhook-Signature header)
    # 3. POST gönder
    # 4. Başarısızsa 5 retry (1s, 5s, 30s, 5m, 30m)
    # 5. 5 başarısız denemeden sonra webhook'u disable et
```

#### Audit Log — Compliance Ready

**Mevcut:** `audit_log_repository.py` + `enterprise_audit.py` var ama hash-chain yok.

**Yapılacak:**

```python
# Immutable, hash-chain audit log
{
    "audit_id": "aud_xxx",
    "tenant_id": "t_xxx",
    "actor": {"id": "u_xxx", "email": "...", "ip": "..."},
    "action": "booking.status_changed",
    "resource": {"type": "booking", "id": "b_xxx"},
    "before": {"status": "draft"},
    "after": {"status": "confirmed"},
    "timestamp": "...",
    "prev_hash": "sha256_of_previous_entry",
    "hash": "sha256(prev_hash + payload)"  # Tamper-proof chain
}
```

#### Enterprise Checklist

| Özellik | Mevcut | Hedef | Durum |
|---------|--------|-------|-------|
| Multi-tenant data isolation | Soft (field-based) | Hard (repo-level guard) | YAPILMALI |
| RBAC | Var (middleware) | Role + Permission + Resource | REFACTOR |
| 2FA/MFA | Var (TOTP) | TOTP + SMS | OK |
| API Key Management | Var | Var + Rate Limiting per key | İYİLEŞTİR |
| Webhook System | YOK | Outbound webhooks + HMAC | YAPILMALI |
| API Versioning | YOK | /api/v1/ prefix | YAPILMALI |
| Audit Trail | Var | Immutable hash-chain | İYİLEŞTİR |
| SSO/SAML | YOK | SAML 2.0 | GELECEK |
| Data Export (GDPR) | Var (GDPR router) | Var | OK |
| SLA Monitoring | Var | Var + Alerting | İYİLEŞTİR |
| Backup/Restore | Var (admin_system_backups) | Var + Tested restore | İYİLEŞTİR |
| Encryption at Rest | MongoDB default | Explicit field encryption | YAPILMALI |

#### Güvenlik Planı

1. **KVKK Uyumu:**
   - Kişisel veri envanteri çıkar (müşteri, misafir, çalışan)
   - Veri silme/anonimize mekanizması (GDPR router mevcut, genişlet)
   - Açık rıza yönetimi

2. **PCI-DSS (ödeme kartı verisi):**
   - Kart bilgisi ASLA backend'de tutma
   - Stripe/iyzico token'lama ile ödeme
   - Mevcut yapı uygun, sadece dokümante et

3. **Penetration Test:**
   - Auto-repair membership → kapat veya logla
   - CORS wildcard (*) → production'da kısıtla
   - Rate limiting → tüm auth endpoint'lere uygula

---

## 4. 90 GÜNLÜK ROADMAP

### GÜN 1-30: TEMEL İYİLEŞTİRME (Foundation)

**Hafta 1-2:**
- [ ] Tek Booking State Machine implementasyonu
- [ ] Migration script (mevcut booking'leri yeni state'lere taşı)
- [ ] booking_lifecycle.py → outbox pattern'e geçiş başlangıcı
- [ ] Ürün kapsamı kararı (kesilecek modüller listesi)

**Hafta 3-4:**
- [ ] Router consolidation (236 → 20)
- [ ] Domain boundary tanımları (5 bounded context)
- [ ] API response standardizasyonu (data/error/pagination)
- [ ] Multi-tenant repository guard implementasyonu

### GÜN 31-60: PRODUCTION READINESS (Hardening)

**Hafta 5-6:**
- [ ] Celery + Redis async job queue kurulumu
- [ ] Supplier search fan-out (async paralel arama)
- [ ] Event Bus → Outbox Pattern dönüşümü
- [ ] API versiyonlama (/api/v1/)

**Hafta 7-8:**
- [ ] Webhook sistemi kurulumu
- [ ] Audit log hash-chain implementasyonu
- [ ] Database index audit & optimization
- [ ] Cache hierarchy implementasyonu (L0/L1/L2)

### GÜN 61-90: MARKET READINESS (Growth)

**Hafta 9-10:**
- [ ] Supplier Quote Comparator (multi-supplier fiyat karşılaştırma)
- [ ] Unified Booking UI (tek ekrandan arama → booking)
- [ ] Settlement otomasyonu (booking.confirmed → auto settlement)
- [ ] Pricing tier implementasyonu (Starter/Pro/Enterprise)

**Hafta 11-12:**
- [ ] Hotelbeds adapter implementasyonu
- [ ] Juniper adapter implementasyonu
- [ ] Pilot müşteri onboarding flow
- [ ] Documentation (API docs, user guide)
- [ ] Load testing (100 concurrent users, 1000 req/s)

---

## ÖZET

Bu ürünün potansiyeli çok yüksek. Türkiye turizm sektöründe **gerçek bir pain point**'i çözüyor. Ama mevcut haliyle:

1. **Çok geniş** — Her şeyi yapıyor, hiçbirini mükemmel yapmıyor
2. **Mimari olarak kırılgan** — 3 state machine, 236 router, modül sınırı yok
3. **Ölçeklenemez** — Sync işlemler, in-memory event bus

**7/10 → 9/10 formülü:**
- **%30 kes** (gereksiz modüller)
- **%40 birleştir** (router consolidation, state machine unification)
- **%30 güçlendir** (event bus, async jobs, multi-tenant isolation)

Bu belge bir "ne yapılabilir" listesi değil, bir **execution plan**'dır. Her madde uygulanabilir ve ölçülebilir.
