# Roadmap — Syroce: Acente Bulut Otomasyonu

## TAMAMLANDI

### Altyapı & Çekirdek
- [x] P0 #1: Booking Truth Model (State Machine)
- [x] P0 #2: Tenant Isolation Hardening (organization_id enforcement)
- [x] P0 #3: Orphan Order Recovery (Evidence-Based Migration + Quarantine)
- [x] P0 #4: Celery + Redis + Outbox Consumer (5 First-Wave Consumer)
- [x] Outbox Consumer Hardening (EventPublisher, Idempotency, DLQ)
- [x] API Response Standardization (Envelope Middleware)
- [x] API Versioning (/api/v1/ canonical + legacy deprecation)

### Webhook & Entegrasyon
- [x] P0.5: Webhook System Productization (HMAC, Retry, Circuit Breaker, Admin)

### Stabilizasyon
- [x] Backend Test Suite Stabilization (88 failure → 4)
- [x] Ruff linting hataları (booking/service.py)
- [x] CI test hataları (test_orphan_migration.py idempotent fixture)

### Ürün Stratejisi
- [x] Ürün konumlandırma reseti (çok ürünlü acente otomasyonu)
- [x] Modül haritası (çekirdek / destekleyici çekirdek / extension)
- [x] Dokümantasyon reseti (README, PRD, MODULE_MAP)

---

## P0 — Kritik (Şu An)
- [ ] Backend test suite %100 yeşil (kalan 4 test-ordering/isolation hatası)

## P1 — Yüksek (Sıradaki Sprint)
- [ ] Router Consolidation Phase 2
  - Legacy router'ları domain modüllerine fiziksel birleştirme
  - ~109 taşınmamış router → ilgili modules/ altına taşıma
  - Sahiplik tablosu uygulaması
- [ ] Event-Driven Core Expansion
  - Daha fazla domain-specific worker ve event type
  - Consumer handler sayısını artırma
- [ ] Cache Strategy (L0/L1/L2)
  - MongoDB query cache
  - Redis session/response cache
  - CDN edge cache
- [ ] UI Sadeleştirme & Bilgi Mimarisi
  - Role-based menu pruning
  - Persona başına 5-7 ana iş tanımı
  - Görev bazlı dashboard
  - Secondary navigation'a gelişmiş modülleri alma

## P2 — Orta
- [ ] Frontend Dependency Mismatch (yarn.lock regeneration)
- [ ] CI Quality Gates & Coverage raporu
- [ ] Dependency Audit (gereksiz paket temizliği)
- [ ] Ürün İçi Analitik Altyapısı
  - Modül bazlı kullanım skoru
  - Tenant bazlı adoption score
  - Feature activation analytics
- [ ] Canlı Mimari Dokümantasyon
  - Auto-generated route inventory
  - Module map senkronizasyonu
  - ADR (Architecture Decision Records)
  - Environment docs

## P3 — Gelecek
- [ ] Yeni Supplier Adapter'ları (Hotelbeds, Juniper)
- [ ] Frontend Persona Ayrımı (satış/operasyon/finans görünümleri)
- [ ] Enterprise SLA Monitoring
- [ ] Per-Tenant Rate Limiting Enhancement
- [ ] Full Regression Test Suite

## Bilinen Teknik Borç
- [ ] yarn.lock mismatch (tekrarlayan, P3)
- [ ] ~109 router hala routers/ altında (Phase 2 hedefi)
- [ ] Bazı schema dosyaları modules dışında (schemas_*.py)
