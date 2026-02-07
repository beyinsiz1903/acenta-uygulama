# 🏗️ PLATFORM TEKNİK RAPOR — Uçtan Uca Analiz
> Tarih: 7 Şubat 2026 | Versiyon: Enterprise Ops-Ready

---

## 📊 GENEL BAKIŞ (Sayılarla)

| Metrik | Değer |
|--------|-------|
| **Backend Python Kod** | 98.374 satır |
| **Frontend JS/JSX Kod** | 68.052 satır |
| **Toplam Kod** | ~166.400 satır |
| **API Endpoint** | 590 |
| **Backend Router** | 166 dosya |
| **Backend Service** | 142 dosya |
| **Frontend Sayfa** | 149 |
| **Frontend Bileşen** | 75 |
| **MongoDB Koleksiyon** | 98 |
| **Veritabanı İndex** | ~300+ |
| **Backend Unit Test** | 100 dosya |
| **E2E Playwright Test** | 27 spec |
| **Doküman** | 9 md dosya |

---

## 🔧 BACKEND MİMARİ

### Tech Stack
- **Framework:** FastAPI 0.110 + Starlette 0.37
- **Runtime:** Python 3.11, Uvicorn 0.25
- **Database:** MongoDB (Motor 3.3 async driver, PyMongo 4.5)
- **Auth:** JWT (PyJWT), bcrypt (passlib)
- **Scheduler:** APScheduler 3.11 (AsyncIO)
- **Payments:** Stripe 14.1
- **PDF:** WeasyPrint 67, ReportLab 4.4
- **Analytics:** Pandas 2.3, NumPy 2.4
- **2FA:** PyOTP 2.9
- **HTTP Client:** httpx 0.28, aiohttp 3.13
- **Testing:** Pytest 9.0, Playwright 1.57

### Katmanlı Mimari

```
┌─────────────────────────────────────────┐
│              MIDDLEWARE                   │
│  CorrelationId → StructuredLogging →     │
│  RateLimit → IPWhitelist → Tenant        │
├─────────────────────────────────────────┤
│              ROUTERS (166)               │
│  Auth │ Admin │ B2B │ Ops │ Public │ CRM │
├─────────────────────────────────────────┤
│              SERVICES (142)              │
│  Business logic, domain rules, providers │
├─────────────────────────────────────────┤
│              DATA LAYER                  │
│  MongoDB (98 collections, 300+ indexes)  │
├─────────────────────────────────────────┤
│              SCHEDULER                   │
│  APScheduler (billing, integrity, uptime)│
└─────────────────────────────────────────┘
```

### Middleware Zinciri (5 katman)
1. **CorrelationIdMiddleware** — Her request'e UUID, response header'da `X-Request-Id`
2. **StructuredLoggingMiddleware** — JSON structured log + request_logs + perf sampling (%5) + slow request (>1s) alert + exception aggregation
3. **RateLimitMiddleware** — MongoDB-backed, path-based rate limiting (login, export vs.)
4. **IPWhitelistMiddleware** — Tenant-level IP kısıtlaması
5. **TenantResolutionMiddleware** — X-Tenant-Id header / host / subdomain bazlı tenant çözümleme

---

## 📦 MODÜLLER (Detaylı)

### 1. AUTH & SECURITY
| Özellik | Durum | Endpoint |
|---------|-------|----------|
| JWT Login/Register | ✅ | POST /api/auth/login, /register |
| Password Reset | ✅ | POST /api/auth/password-reset |
| RBAC v2 (granüler) | ✅ | GET/POST /api/admin/rbac/* |
| 2FA (TOTP) | ✅ | POST /api/2fa/setup, /verify, /disable |
| IP Whitelist | ✅ | GET/POST /api/admin/ip-whitelist |
| Password Policy | ✅ | Service-level enforcement |
| Feature Flags | ✅ | Plan-based + org override |
| Rate Limiting | ✅ | MongoDB TTL-based |

### 2. MULTI-TENANT
| Özellik | Durum | Detay |
|---------|-------|-------|
| Tenant Resolution | ✅ | Header / Host / Subdomain |
| Tenant Isolation | ✅ | organization_id bazlı |
| Tenant Health | ✅ | trial/active/overdue dashboard |
| Tenant Features | ✅ | Plan + override bazlı feature toggle |
| SaaS Tenants CRUD | ✅ | /api/admin/tenants/* |
| White-label | ✅ | Logo, renk, domain konfigürasyonu |

### 3. CRM
| Özellik | Durum | Endpoint |
|---------|-------|----------|
| Customers 360 | ✅ | /api/crm/customers |
| Duplicate Detection | ✅ | /api/crm/customers/duplicates |
| Deals Pipeline | ✅ | /api/crm/deals (DnD destekli) |
| Tasks | ✅ | /api/crm/tasks |
| Activities | ✅ | /api/crm/activities |
| Events | ✅ | /api/crm/events |
| Notes | ✅ | /api/crm/notes |
| Timeline | ✅ | /api/crm/timeline |
| Customer Inbox | ✅ | /api/crm/customer-inbox |

### 4. BOOKING & RESERVATIONS
| Özellik | Durum | Detay |
|---------|-------|-------|
| Booking Lifecycle | ✅ | State machine (draft→confirmed→cancelled) |
| Booking Amendments | ✅ | Quote + confirm (increase/decrease/zero delta) |
| Booking Events | ✅ | Event sourcing pattern |
| Booking Financials | ✅ | Multi-currency, FX |
| Booking Payments | ✅ | Stripe + mock TR POS |
| Reservations | ✅ | /api/reservations |
| Vouchers (PDF) | ✅ | WeasyPrint PDF generation |
| Public My Booking | ✅ | Token-based self-service portal |

### 5. B2B NETWORK
| Özellik | Durum | Detay |
|---------|-------|-------|
| B2B Portal | ✅ | Ayrı login + layout |
| B2B Quotes | ✅ | Quote request + pricing |
| B2B Bookings | ✅ | Acenta bazlı booking |
| B2B Cancel | ✅ | İptal workflow |
| B2B Announcements | ✅ | Acenta duyuruları |
| B2B Discounts | ✅ | Acenta özel indirimler |
| B2B Marketplace | ✅ | Multi-supplier catalog |
| B2B Hotels Search | ✅ | Otel arama (Paximum adapter) |
| B2B Exchange | ✅ | Ağ üzerinden veri değişimi |
| B2B Network Bookings | ✅ | Partner ağı rezervasyonları |
| B2B Visibility | ✅ | Ürün görünürlük kontrolü |
| B2B Funnel | ✅ | Sales funnel tracking |
| B2B Pricing | ✅ | Acenta bazlı fiyatlama |

### 6. FINANCE & LEDGER
| Özellik | Durum | Detay |
|---------|-------|-------|
| Ledger (append-only) | ✅ | Immutable ledger entries |
| Ledger Postings | ✅ | Double-entry pattern |
| Finance Views | ✅ | Dashboard + reports |
| Refund Calculator | ✅ | Otomatik iade hesaplama |
| Refund Cases | ✅ | Onay workflow'lu iade |
| Credit Exposure | ✅ | Acenta kredi risk izleme |
| Settlements | ✅ | Mutabakat runs |
| Settlement Statements | ✅ | Dönemsel hesap özetleri |
| FX Service | ✅ | Döviz kuru + multi-currency |
| Installments | ✅ | Taksit hesaplama |
| WebPOS | ✅ | Ödeme kayıt terminali |
| Stripe Payments | ✅ | Stripe integration |
| Click-to-Pay | ✅ | Link ile ödeme |
| Supplier Finance | ✅ | Tedarikçi finansalları |
| Supplier Accrual | ✅ | Tahakkuk yönetimi |

### 7. PRODUCTS & CATALOG
| Özellik | Durum | Detay |
|---------|-------|-------|
| Products CRUD | ✅ | Otel, villa, tur |
| Hotels | ✅ | Otel yönetimi |
| Tours | ✅ | Tur yönetimi |
| Catalog (Admin) | ✅ | Katalog yönetimi + yayınlama |
| Inventory | ✅ | Stok/oda yönetimi |
| Inventory Shares | ✅ | Kanal bazlı stok paylaşımı |
| Rate Plans | ✅ | Fiyat planları |
| Stop-Sell | ✅ | Satış durdurma |
| iCal Sync | ✅ | Takvim senkronizasyonu |

### 8. PRICING ENGINE
| Özellik | Durum | Detay |
|---------|-------|-------|
| Pricing Rules | ✅ | Kural bazlı fiyatlama |
| Pricing Graph | ✅ | Graf tabanlı fiyat hesaplama |
| Pricing Quote Engine | ✅ | Anlık fiyat teklifi |
| Pricing Audit | ✅ | Fiyat değişiklik izi |
| Pricing Trace | ✅ | Detaylı fiyat hesap adımları |
| Pricing Incidents | ✅ | Fiyat anomali tespiti |
| Commission Rules | ✅ | Komisyon hesaplama |
| B2B Pricing Overlay | ✅ | Acenta bazlı fiyat katmanı |

### 9. SUPPLIER INTEGRATION
| Özellik | Durum | Detay |
|---------|-------|-------|
| Supplier Adapter Registry | ✅ | Pluggable adapter pattern |
| Paximum Adapter | ✅ | XML supplier search |
| Mock Adapter | ✅ | Test/dev supplier |
| Supplier Health | ✅ | Tedarikçi sağlık + circuit breaker |
| Supplier Search | ✅ | Multi-supplier unified search |
| Supplier Mapping | ✅ | Marketplace mapping |
| Supplier Confirm | ✅ | Booking konfirmasyonu |

### 10. OPS (Operations)
| Özellik | Durum | Detay |
|---------|-------|-------|
| Ops Cases | ✅ | Guest case yönetimi |
| Ops Tasks | ✅ | Görev atama + takip |
| Ops Incidents | ✅ | Incident konsolu (P0-P2) |
| Ops B2B Queues | ✅ | B2B operasyon kuyrukları |
| Ops Booking Events | ✅ | Booking event stream |
| Ops Finance | ✅ | Finansal operasyon görünümü |
| Ops Playbook | ✅ | Otomatik playbook tetikleme |

### 11. E-FATURA
| Özellik | Durum | Provider |
|---------|-------|---------|
| Fatura CRUD | ✅ | — |
| Fatura Gönder | ✅ | MockProvider (adapter-ready) |
| Fatura İptal | ✅ | — |
| Fatura Events | ✅ | Timeline tracking |
| Profil Yönetimi | ✅ | Vergi no, ünvan vs. |
| Idempotency | ✅ | Duplicate guard |

### 12. SMS BİLDİRİMLER
| Özellik | Durum | Provider |
|---------|-------|---------|
| Tekli SMS | ✅ | MockProvider (adapter-ready) |
| Toplu SMS | ✅ | Batch sending |
| Template | ✅ | 5 hazır şablon |
| Log Takibi | ✅ | Delivery status |

### 13. QR TICKET & CHECK-IN
| Özellik | Durum | Detay |
|---------|-------|-------|
| Bilet Oluştur | ✅ | QR data generation |
| Check-in | ✅ | Code-based check-in |
| İptal | ✅ | Ticket cancellation |
| Guard'lar | ✅ | Already checked, canceled, expired |
| İstatistikler | ✅ | Total, active, checked_in, canceled |
| Idempotency | ✅ | Per-reservation unique |

### 14. ENTERPRISE GOVERNANCE
| Özellik | Durum | Detay |
|---------|-------|-------|
| Approval Workflows | ✅ | Refund, export, high-value |
| Immutable Audit Chain | ✅ | SHA-256 hash zinciri |
| Audit Log Export | ✅ | CSV + JSON |
| Enterprise Export | ✅ | Tenant data export |
| Scheduled Reports | ✅ | Zamanlanmış rapor teslimi |
| Enterprise Health | ✅ | Live + Ready endpoints |

### 15. OPERASYONEL MÜKEMMELLIK (Yeni Sprint)
| Özellik | Durum | Detay |
|---------|-------|-------|
| Backup System | ✅ | mongodump + retention (30 gün) |
| Restore Test Script | ✅ | scripts/restore_test.py |
| Audit Chain Verifier | ✅ | Günlük cron (03:00) |
| Ledger Integrity Check | ✅ | Günlük cron (03:30) |
| Orphan Detector | ✅ | Fatura/bilet/rezervasyon |
| System Metrics | ✅ | 8 metrik (cached 30s) |
| System Errors | ✅ | Aggregated by signature |
| Slow Request Alert | ✅ | >1000ms → warning |
| Exception Aggregation | ✅ | Middleware-level catch |
| Enhanced Health Ready | ✅ | DB + scheduler + disk + error rate |
| Maintenance Mode | ✅ | Tenant-level toggle |
| Uptime Tracking | ✅ | Dakikalık health check |
| Incident Management | ✅ | Create → Resolve lifecycle |
| Preflight (GO/NO-GO) | ✅ | 15 otomatik kontrol |
| Ops Runbook | ✅ | P0-P2 interaktif playbook |
| Perf Sampling | ✅ | %5 sampling, p50/p95/p99 |
| MongoDB Cache | ✅ | TTL-based read-through |
| Perf Dashboard | ✅ | Top endpoints + slow alerts |
| Demo Guide | ✅ | 10-adım interaktif rehber |

### 16. PUBLIC / STOREFRONT
| Özellik | Durum | Detay |
|---------|-------|-------|
| Public Search | ✅ | Ürün arama |
| Public Checkout | ✅ | Online satın alma |
| Public Campaigns | ✅ | Kampanya sayfaları |
| Public CMS Pages | ✅ | Statik sayfa yönetimi |
| Public Tours | ✅ | Tur detay + checkout |
| Storefront (multi-tenant) | ✅ | Tenant-scoped vitrin |
| SEO | ✅ | Meta tag + sitemap + IndexNow |
| Partner Apply | ✅ | Partner başvuru formu |
| Signup + Pricing | ✅ | Self-service kayıt |

### 17. BILLING & SUBSCRIPTION
| Özellik | Durum | Detay |
|---------|-------|-------|
| Subscription Management | ✅ | Plan + tier |
| Usage Metering | ✅ | Kullanım bazlı ölçüm |
| Usage Push | ✅ | Stripe usage push |
| Billing Finalize | ✅ | Otomatik fatura kesme |
| Billing Webhooks | ✅ | Stripe webhook handler |
| Iyzico Provider | ✅ | TR ödeme entegrasyonu |

### 18. PARTNER & MARKETPLACE
| Özellik | Durum | Detay |
|---------|-------|-------|
| Partner Graph | ✅ | Partner ilişki ağı |
| Partner v1 API | ✅ | External partner API |
| Partner Auth | ✅ | Partner authentication |
| Marketplace Listings | ✅ | Çoklu tedarikçi kataloğu |
| Marketplace Booking | ✅ | Cross-supplier booking |
| Match System | ✅ | Otomatik eşleştirme |
| Match Alerts | ✅ | Eşleşme bildirimleri |

### 19. RAPORLAMA & ANALİTİK
| Özellik | Durum | Detay |
|---------|-------|-------|
| Advanced Reports | ✅ | Financial/Product/Partner/Aging |
| Admin Metrics | ✅ | KPI dashboard |
| Revenue Analytics | ✅ | Gelir analizi |
| Admin Reporting | ✅ | Özel raporlar |
| Export (CSV/JSON) | ✅ | Rate limited |
| Scheduled Reports | ✅ | Email teslimatlı |

---

## 🖥️ FRONTEND MİMARİ

### Tech Stack
- **Framework:** React 19
- **Routing:** React Router 7.5
- **UI Kit:** Radix UI + Tailwind CSS + shadcn/ui (75 bileşen)
- **Charts:** Recharts 3.6
- **DnD:** @dnd-kit (CRM pipeline)
- **Forms:** React Hook Form + Zod
- **Animations:** Framer Motion 12
- **Payments:** @stripe/react-stripe-js
- **Icons:** Lucide React 507
- **HTTP:** Axios

### Sayfa Dağılımı

| Kategori | Sayfa Sayısı |
|----------|-------------|
| Admin Yönetim | 100 |
| Admin (Yeni) | 14 |
| CRM | 6 |
| Public | 12 |
| Storefront | 3 |
| B2B | 6 |
| Ops | 4 |
| Partners | 10 |
| Marketplace | 2 |
| **TOPLAM** | **149** |

### Layout Yapısı
- **AppShell** — Ana uygulama kabuğu (sidebar + header)
- **AdminLayout** — Admin sayfaları wrapper
- **AgencyLayout** — Acenta portal layout
- **HotelLayout** — Otel portal layout
- **B2BLayout** — B2B portal layout

### Navigasyon (3 bölüm, 36+ item)
1. **Admin** — 27 navigasyon öğesi
2. **Risk & Matches** — 6 öğe
3. **Operasyonel Mükemmellik** — 10 öğe (yeni)

---

## 🗄️ VERİTABANI (MongoDB)

### Koleksiyon Sayısı: 98

**Ana Gruplar:**
- **Auth & Users:** users, organizations, tenants, permissions, role_permissions, user_2fa, memberships
- **CRM:** crm_deals, crm_tasks, crm_activities, crm_notes, crm_events, customers, leads
- **Booking:** bookings, booking_drafts, booking_events, booking_payments, reservations, vouchers
- **Finance:** ledger_entries, ledger_postings, finance_accounts, account_balances, payments, settlements
- **B2B:** agencies, agency_hotel_links, b2b quotes, marketplace_access, marketplace_listings
- **Products:** products, hotels, inventory, rate_plans, channel_allocations
- **Pricing:** pricing_rules, pricing_contracts, pricing_rate_grids, pricing_traces
- **Ops:** ops_cases, system_errors, system_incidents, system_uptime, system_backups
- **Integration:** integration_providers, integration_mappings, integration_sync_outbox
- **Cache & Perf:** app_cache, perf_samples, request_logs, rate_limits, search_cache

### İndex Stratejisi: 300+
- TTL indexes: rate_limits, request_logs (24h), perf_samples (7d), app_cache
- Compound indexes: tenant_id + status, org_id + created_at, vb.
- Unique indexes: user email+org, tenant_key, ticket_code, vb.

---

## 🧪 TEST ALTYAPISI

### Backend
- **100 test dosyası** (pytest)
- Kapsamlı: booking lifecycle, ledger net-zero, audit chain, pricing engine, B2B, CRM, ops
- Integration test pattern: conftest.py + fixtures

### E2E (Playwright)
- **27 spec dosyası**
- Dashboard, CRM pipeline, booking, ops incidents, notifications
- **5 yeni ops spec** (backups, integrity, metrics, maintenance, incident flow)
- Tümü yeşil ✅

---

## 📋 CRON / SCHEDULER GÖREVLER

| Görev | Zamanlama | Açıklama |
|-------|-----------|----------|
| Billing Finalize | Periyodik | Abonelik fatura kesme |
| Report Schedule Check | Her 15 dk | Zamanlanmış rapor teslimi |
| Uptime Check | Her 1 dk | Sistem sağlık kontrolü |
| Audit Chain Verify | Günlük 03:00 | Hash zinciri doğrulama |
| Ledger Integrity | Günlük 03:30 | Defter tutarlılık kontrolü |
| Backup Cleanup | Günlük 04:00 | 30 gün üstü yedek silme |

---

## 📄 DOKÜMANTASYON

| Dosya | İçerik |
|-------|--------|
| PRODUCTION_CHECKLIST.md | 7 bölüm go-live checklist |
| RUNBOOK.md | P0-P2 ops playbook |
| SLA_DEMO_SCRIPT.md | 15 dk demo script |
| DEMO_SCRIPT_15MIN.md | Ekran ekran detaylı demo |
| SALES_DECK.md | 10 slayt deck iskeleti |
| POSITIONING.md | Rekabet pozisyonlama + itiraz cevapları |
| DISCOVERY_AND_PRICING.md | 20 soru + fiyat çerçevesi |

---

## 🎯 MEVCUT DURUM ÖZETİ

### ✅ Production-Ready
- Tüm core modüller çalışır durumda
- Enterprise governance (RBAC, 2FA, audit chain) aktif
- Ops layer tam (backup, uptime, incidents, preflight)
- Cache + perf sampling aktif
- Preflight verdict: **GO** (14 pass, 1 warn, 0 fail)

### ⚠️ Mock/Placeholder Durumunda
- **E-Fatura Provider:** MockProvider aktif → Paraşüt/Foriba adapter gerekli
- **SMS Provider:** MockProvider aktif → Netgsm/Twilio adapter gerekli
- **Paximum Supplier:** API key gerekli (staging key set)
- **Stripe:** Test key aktif (`sk_test_emergent`)

### 📈 Ölçek Metrikleri
- ~166K satır kod (backend + frontend)
- 590 API endpoint
- 98 MongoDB koleksiyon
- 149 frontend sayfa
- 27 E2E test
- 100 backend test dosyası

---

> **Sonuç:** Bu platform, enterprise SaaS standardında, multi-tenant izolasyonlu, operasyonel mükemmellik katmanlı, tam denetim izli bir turizm ERP sistemidir.
