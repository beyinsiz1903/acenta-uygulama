# PRD — Syroce: Acente Bulut Otomasyonu

## Ürün Kimliği

### Slogan
**Yeni nesil acente işletim sistemi.**

### Tek Cümlelik Tanım
Tur, otel, uçak ve B2B satış yapan acenteler için rezervasyon, operasyon, tedarikçi ve finans akışını tek yerden yöneten acente bulut otomasyonu.

### Açıklayıcı Tanım
Acentelerin tekliften rezervasyona, operasyondan tedarikçiye, B2B dağıtımdan mutabakata kadar tüm süreçlerini tek platformda yönetmesini sağlayan çok modüllü SaaS altyapısı.

### Stratejik Çerçeve
Bu sistem, yalnızca otel satan acenteler için değil; tur, otel, uçak ve B2B satış yapan acentelerin rezervasyon, operasyon, tedarikçi ve finans süreçlerini tek merkezden yönetmesi için tasarlanmış çok modüllü bir acente bulut otomasyonudur.

- **Çekirdek kimlik:** Acente otomasyonu
- **Rezervasyon kontrol kası:** PMS benzeri operasyon disiplini
- **Genişleme kası:** B2B ve tedarikçi ağı

---

## Hedef Kitle

Ürün tek bir satış tipine değil, çok ürünlü acente yapısına hitap eder:
- Tur satışı yapan acenteler
- Otel satışı yapan acenteler
- Uçak satışı yapan acenteler
- B2B dağıtım yapan acenteler
- Karma (multi-product) çalışan acenteler

## Kullanıcı Personaları

| Persona | Rol | Temel Görevler |
|---------|-----|----------------|
| **Platform Yöneticisi** | Super Admin | Platform geneli yönetim, tenant yönetimi, sistem izleme |
| **Acente Yöneticisi** | Agency Admin | Organizasyon yönetimi, kullanıcı/rol atamaları, raporlama |
| **Satış Temsilcisi** | Sales | Teklif oluşturma, rezervasyon, müşteri takibi |
| **Operasyon Sorumlusu** | Ops | Rezervasyon takibi, tedarikçi koordinasyonu, vaka yönetimi |
| **Finans Sorumlusu** | Finance | Faturalama, mutabakat, ödeme takibi, muhasebe |
| **Otel/Tedarikçi** | Hotel/Supplier | Gelen talep yönetimi, allocasyon, stop-sell |
| **B2B İş Ortağı** | B2B Partner | B2B portal üzerinden arama, rezervasyon, mutabakat |
| **Harici Geliştirici** | API Consumer | Versiyonlu API + webhook entegrasyonu |

---

## Teknik Mimari

### Backend
- **Framework:** FastAPI (Python)
- **Veritabanı:** MongoDB (Motor async driver)
- **Kuyruk:** Celery + Redis (broker DB 1, results DB 2, cache DB 0)
- **Desen:** Transactional Outbox → Celery Worker → Consumer Handlers
- **API Standardı:** `{ok, data, meta}` response envelope
- **API Versiyonlama:** `/api/v1/...` (canonical) + `/api/...` (legacy, deprecation header)

### Frontend
- **Framework:** React (CRA + CRACO)
- **UI Kit:** Shadcn/UI + Tailwind CSS
- **State:** React Context + React Query
- **Routing:** React Router v6
- **i18n:** Türkçe (birincil)

### Event Sistemi
- **Outbox Tablosu:** `outbox_events` collection
- **EventPublisher:** Domain katmanı Celery/Redis'e doğrudan dokunmaz
- **Outbox Consumer:** Celery beat (5s periyot)
- **Dispatch Tablosu:** 13 event tipi, 45+ handler
- **First-Wave Consumer'lar:** notification, email, billing, reporting, webhook
- **Garantiler:** At-least-once delivery, idempotent consumer'lar, dead-letter queue

### Webhook Sistemi
- Organizasyon kapsamlı subscription modeli
- HMAC-SHA256 imzalama, HTTPS-only, SSRF koruması
- 6 deneme exponential backoff ile retry
- Per-subscription circuit breaker (5 ardışık hatada durdurma)
- 10 desteklenen event tipi

### Multi-Tenant Güvenlik
- Her dokümanda `organization_id` izolasyonu
- Middleware seviyesinde tenant bağlamı zorunluluğu
- RBAC ile rol tabanlı erişim kontrolü
- JWT + session tabanlı kimlik doğrulama

---

## Modül Haritası

Detaylı modül sınıflandırması için bkz: `/app/docs/MODULE_MAP.md`

### Çekirdek Modüller
identity, tenant, auth, booking, finance, supplier, crm

### Destekleyici Çekirdek (Operasyonel Derinlik)
operations, inventory, pricing, reservation-control

### Extension Modüller
b2b-network, marketplace, enterprise, partner-graph, reporting, public/storefront, mobile-bff, webhook, ai-assistant, campaigns/cms

---

## Ticari Paket Yapısı

| Özellik | Trial | Starter | Pro | Enterprise |
|---------|-------|---------|-----|------------|
| Dashboard | + | + | + | + |
| Rezervasyonlar | + | + | + | + |
| CRM | + | + | + | + |
| Envanter | + | + | + | + |
| Raporlar | + | + | + | + |
| Muhasebe | + | - | + | + |
| WebPOS | + | - | + | + |
| İş Ortakları | + | - | + | + |
| B2B Dağıtım | + | - | - | + |
| Operasyon | + | - | + | + |
| Kullanıcı Limiti | 2 | 3 | 10 | Sınırsız |
| Aylık Rez. Limiti | 100 | 100 | 500 | Sınırsız |
| Fiyat (TRY/ay) | 0 (14 gün) | 990 | 2.490 | 6.990 |

---

## Tamamlanan İşler

- [x] Booking truth model (state machine)
- [x] Tenant isolation (organization_id enforcement)
- [x] Orphan order recovery (evidence-based migration + quarantine)
- [x] Celery + Redis + Outbox Consumer (5 first-wave consumer)
- [x] Outbox Consumer Hardening (EventPublisher, Idempotency, DLQ)
- [x] API Response Standardization (Envelope Middleware)
- [x] API Versioning (/api/v1/)
- [x] Webhook System Productization (2026-03-18)
- [x] Backend Test Suite Stabilization (88 → 4 hata, 2026-03-19)
- [x] Ruff linting hataları düzeltildi (booking/service.py, 2026-03-20)
- [x] CI test hataları düzeltildi (test_orphan_migration.py, 2026-03-20)
- [x] Ürün konumlandırması ve dokümantasyon reseti (Faz 1, 2026-02)

---

## Aktif Backlog

### P0 — Kritik
- [x] Backend test suite %100 yeşil (0 FAILED, 0 ERROR — 680 passed)

### P1 — Yüksek
- [ ] Router Consolidation Phase 2 (fiziksel birleştirme)
- [ ] Event-Driven Core Expansion (daha fazla domain worker)
- [ ] Cache Strategy (L0/L1/L2)
- [ ] UI Sadeleştirme & Bilgi Mimarisi

### P2 — Orta
- [ ] Frontend Dependency Mismatch (yarn.lock regeneration)
- [ ] CI Quality Gates & Coverage
- [ ] Dependency Audit
- [ ] Ürün İçi Analitik Altyapısı
- [ ] Canlı Mimari Dokümantasyon (auto-generated route inventory, ADR)

### P3 — Gelecek
- [ ] Yeni Supplier Adapter'ları (Hotelbeds, Juniper)
- [ ] Frontend Persona Ayrımı (satış/operasyon/finans görünümleri)
- [ ] Enterprise SLA Monitoring
- [ ] Per-Tenant Rate Limiting Enhancement
