# Syroce — Yeni Nesil Acente İşletim Sistemi

> Tur, otel, uçak ve B2B satış yapan acenteler için rezervasyon, operasyon, tedarikçi ve finans akışını tek yerden yöneten acente bulut otomasyonu.

---

## Nedir?

Syroce, farklı ürün tipleri satan acentelerin ortak operasyon sistemidir. Tekliften rezervasyona, operasyondan tedarikçiye, B2B dağıtımdan mutabakata kadar tüm süreçleri tek platformda birleştirir.

**Bu sistem:**
- Tek bir satış tipine değil, **çok ürünlü acente yapısına** hitap eder
- Hotel/PMS mantığı ana kimlik değil, **rezervasyon kontrol katmanıdır**
- B2B alanı yan özellik değil, **büyüme ve dağıtım katmanıdır**
- Finance/mutabakat alanı muhasebe eklentisi değil, **operasyon tamamlayıcısıdır**

## Kimin İçin?

| Profil | Kullanım Senaryosu |
|--------|---------------------|
| **Küçük Acenteler** | Excel'den dijitale geçiş, temel rezervasyon ve müşteri yönetimi |
| **Büyüyen Acenteler** | Çoklu tedarikçi, operasyon takibi, finansal kontrol |
| **B2B Dağıtım Ağları** | Acente-acente arası satış, mutabakat, komisyon yönetimi |
| **Çok Ürünlü Operasyonlar** | Tur + otel + uçak tek panelde, multi-currency, multi-supplier |
| **Enterprise Yapılar** | White-label, gelişmiş RBAC, onay akışları, kurumsal yönetişim |

---

## Modül Yapısı

### Çekirdek
Her müşteride aktif, platformun iskeletini oluşturur.

| Modül | Sorumluluk |
|-------|------------|
| **Identity & Tenant** | Multi-tenant izolasyon, kullanıcı/rol yönetimi, ayarlar |
| **Auth** | JWT + session tabanlı kimlik doğrulama, 2FA, token yönetimi |
| **Booking** | Unified state machine ile rezervasyon lifecycle yönetimi |
| **Finance** | Faturalama, ödemeler, mutabakat, muhasebe defteri, döviz |
| **Supplier** | Tedarikçi adapter'ları, sağlık izleme, circuit breaker |
| **CRM** | Müşteri yönetimi, satış fırsatları, görevler, aktivite takibi |

### Destekleyici Çekirdek
Operasyonel derinlik sağlar. Bazı müşteriler için kritik öneme sahiptir.

| Modül | Sorumluluk |
|-------|------------|
| **Operations** | Vaka yönetimi, görev dağıtımı, olay takibi |
| **Inventory** | Stok/oda yönetimi, müsaitlik, allocasyon, envanter senkronizasyonu |
| **Pricing** | Kural tabanlı fiyatlandırma, çok katmanlı fiyat grafiği, teklif motoru |
| **Reservation Control** | PMS benzeri operasyon disiplini, Google Sheets entegrasyonu |

### Extension
Feature flag ile kontrol edilen, bağımsız genişleme modülleri.

| Modül | Sorumluluk |
|-------|------------|
| **B2B Network** | Acente-acente arası satış ağı, dağıtım, exchange |
| **Marketplace** | Pazar yeri, public storefront, online checkout |
| **Enterprise** | Kurumsal yönetişim, audit trail, onay akışları, GDPR |
| **Partner Graph** | İş ortağı ilişki ağı, komisyon zinciri |
| **Reporting** | Gelişmiş raporlar, analitik, yönetim panosu |
| **Mobile BFF** | Mobil uygulama backend-for-frontend |
| **Webhooks** | HMAC imzalı webhook delivery, retry, circuit breaker |
| **AI Assistant** | Yapay zeka destekli asistan |

---

## Teknik Mimari

```
                    ┌─────────────────────────────────┐
                    │        React Frontend            │
                    │   Shadcn/UI + Tailwind + RQ      │
                    └──────────────┬──────────────────┘
                                   │ HTTPS
                    ┌──────────────▼──────────────────┐
                    │        FastAPI Backend            │
                    │   /api/v1/  (canonical)           │
                    │   /api/     (legacy + deprecation) │
                    ├──────────────────────────────────┤
                    │  Middleware: Tenant │ RBAC │ Rate  │
                    │  Envelope │ Versioning │ CORS     │
                    ├──────────────────────────────────┤
                    │  11 Domain Modules (DDD)          │
                    │  100+ Service Layer                │
                    │  20+ Repository Layer              │
                    └──────┬───────────────┬───────────┘
                           │               │
                ┌──────────▼───┐   ┌───────▼──────────┐
                │   MongoDB    │   │  Redis (3 DB)     │
                │   (Motor)    │   │  0: Cache          │
                │              │   │  1: Celery Broker   │
                └──────────────┘   │  2: Celery Results  │
                                   └───────┬──────────┘
                                           │
                                   ┌───────▼──────────┐
                                   │  Celery Workers   │
                                   │  Outbox Consumer  │
                                   │  Beat Scheduler   │
                                   └──────────────────┘
```

### Event-Driven Architecture

```
Domain Event → outbox_events (MongoDB)
                    ↓ (5s poll)
              Outbox Consumer (Celery Beat)
                    ↓
              Dispatch Table (13 event types)
                    ↓
    ┌──────────┬──────────┬──────────┬──────────┬──────────┐
    │Notification│ Email  │ Billing  │Reporting │ Webhook  │
    │ Consumer  │Consumer │Consumer  │Consumer  │ Consumer │
    └──────────┴──────────┴──────────┴──────────┴──────────┘
```

### API Standartları

**Response Envelope:**
```json
{
  "ok": true,
  "data": { ... },
  "meta": {
    "trace_id": "abc-123",
    "timestamp": "2026-02-01T12:00:00Z",
    "latency_ms": 45,
    "api_version": "v1"
  }
}
```

**Versiyonlama:**
- Canonical: `GET /api/v1/bookings`
- Legacy: `GET /api/bookings` (deprecation header ile)

---

## Kurulum

### Gereksinimler
- Python 3.11+
- Node.js 18+
- MongoDB 6+
- Redis 7+

### Backend
```bash
cd backend
cp .env.example .env          # Ortam değişkenlerini düzenle
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001
```

### Frontend
```bash
cd frontend
cp .env.example .env          # REACT_APP_BACKEND_URL ayarla
yarn install
yarn start                     # Port 3000
```

### Worker (Celery)
```bash
cd backend
celery -A app.infrastructure.celery_app worker --loglevel=info
celery -A app.infrastructure.celery_app beat --loglevel=info
```

---

## Ortam Değişkenleri

| Değişken | Konum | Açıklama |
|----------|-------|----------|
| `MONGO_URL` | backend/.env | MongoDB bağlantı URL'i |
| `DB_NAME` | backend/.env | Veritabanı adı |
| `REDIS_URL` | backend/.env | Redis bağlantı URL'i |
| `JWT_SECRET` | backend/.env | JWT imzalama anahtarı |
| `REACT_APP_BACKEND_URL` | frontend/.env | API base URL |

---

## Auth & Tenant Modeli

### Kimlik Doğrulama
- **JWT Token:** Bearer token ile API erişimi
- **Session:** HTTP-only cookie ile web oturum yönetimi
- **2FA:** TOTP tabanlı iki faktörlü doğrulama (Enterprise)

### Multi-Tenant İzolasyon
- Her HTTP isteğinde tenant bağlamı çözümlenir
- Tüm veritabanı sorguları `organization_id` filtresi ile çalışır
- Middleware seviyesinde zorunlu — by-pass edilemez
- Admin kullanıcıları cross-tenant erişim yetkisine sahiptir

### Rol Yapısı
| Rol | Kapsam | Erişim |
|-----|--------|--------|
| `super_admin` | Platform | Tüm organizasyonlar ve sistem ayarları |
| `agency_admin` | Organizasyon | Kendi organizasyonu, kullanıcı ve ayar yönetimi |
| `agent` | Organizasyon | Satış ve operasyon ekranları |
| `finance` | Organizasyon | Finans ve mutabakat ekranları |
| `hotel` | Organizasyon | Otel/tedarikçi ekranları |
| `b2b_partner` | B2B | B2B portal ve mutabakat |

---

## Entegrasyon Yaklaşımı

### Tedarikçi Adapter Mimarisi
Yeni tedarikçi eklemek için `app/suppliers/adapters/` altına adapter sınıfı oluşturulur. Her adapter ortak interface'i uygular:
- `search()` — Ürün/oda arama
- `book()` — Rezervasyon oluşturma
- `confirm()` — Rezervasyon onaylama
- `cancel()` — İptal

Mevcut adapter'lar: Paximum, RateHawk

### Webhook Entegrasyonu
Dış sistemlere event iletimi için productized webhook altyapısı:
- HMAC-SHA256 ile imzalanmış payload
- Exponential backoff ile 6 deneme retry
- Per-subscription circuit breaker
- 10 desteklenen event tipi

### Muhasebe Entegrasyonu
- Parasut e-fatura push
- Genel muhasebe senkronizasyonu

---

## Proje Yapısı

```
/app
├── backend/
│   ├── app/
│   │   ├── modules/          # Domain modülleri (DDD bounded contexts)
│   │   │   ├── auth/         # Kimlik doğrulama
│   │   │   ├── identity/     # Kullanıcı & organizasyon
│   │   │   ├── tenant/       # Multi-tenant izolasyon
│   │   │   ├── booking/      # Rezervasyon motoru
│   │   │   ├── finance/      # Finans
│   │   │   ├── supplier/     # Tedarikçi yönetimi
│   │   │   ├── crm/          # Müşteri ilişkileri
│   │   │   ├── b2b/          # B2B ağı
│   │   │   ├── operations/   # Operasyon merkezi
│   │   │   ├── enterprise/   # Kurumsal yönetişim
│   │   │   ├── system/       # Sistem altyapısı
│   │   │   └── mobile/       # Mobil BFF
│   │   ├── routers/          # HTTP route tanımları (~120 router)
│   │   ├── services/         # İş mantığı katmanı (~150 servis)
│   │   ├── repositories/     # Veritabanı erişim katmanı
│   │   ├── infrastructure/   # Celery, Redis, Event Bus
│   │   ├── middleware/       # Request/Response ara katman
│   │   ├── suppliers/        # Tedarikçi adapter'ları
│   │   ├── constants/        # Sabitler, feature flag, plan matrisi
│   │   ├── bootstrap/        # Uygulama başlatma, router registry
│   │   └── schemas/          # Pydantic modelleri
│   ├── tests/                # Backend test suite (~180 test dosyası)
│   └── server.py             # API entrypoint
├── frontend/
│   ├── src/
│   │   ├── pages/            # Sayfa bileşenleri (~120 sayfa)
│   │   ├── components/       # Paylaşılan bileşenler
│   │   ├── features/         # Feature-bazlı modüller
│   │   ├── nav/              # Navigasyon tanımları
│   │   ├── routes/           # Route yapılandırması
│   │   ├── lib/              # Utility & API istemcileri
│   │   ├── hooks/            # React hook'ları
│   │   └── contexts/         # React context'leri
│   └── public/
├── docs/                     # Proje dokümantasyonu
│   ├── MODULE_MAP.md         # Modül haritası ve sahiplik
│   └── ...
└── memory/                   # PRD, CHANGELOG, ROADMAP
    ├── PRD.md
    ├── CHANGELOG.md
    └── ROADMAP.md
```

---

## Test

```bash
cd backend
pytest                         # Tüm test suite
pytest tests/test_booking_*.py # Booking testleri
pytest -x                      # İlk hatada dur
```

Test altyapısı:
- **Framework:** pytest + anyio (async)
- **Mock:** respx (HTTP), unittest.mock
- **Coverage:** ~180 test dosyası
- **Retry:** AutoReconnect/ConnectionReset için otomatik 2 tekrar

---

## Ticari Paketler

| | Starter | Pro | Enterprise |
|--|---------|-----|------------|
| **Hedef** | Küçük acenteler | Büyüyen acenteler | Büyük operasyonlar |
| **Fiyat** | 990 TRY/ay | 2.490 TRY/ay | 6.990 TRY/ay |
| **Kullanıcı** | 3 | 10 | Sınırsız |
| **Aylık Rez.** | 100 | 500 | Sınırsız |
| **Modüller** | Dashboard, Rez., CRM, Envanter, Raporlar | + Muhasebe, WebPOS, İş Ortakları, Ops | + B2B Dağıtım, Tüm modüller |

---

*Syroce — Yeni nesil acente işletim sistemi.*
