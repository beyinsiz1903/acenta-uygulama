# Roadmap — Syroce: Acente Bulut Otomasyonu

## TAMAMLANDI

### Altyapi & Cekirdek
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
- [x] Backend Test Suite Stabilization (88 failure -> 4)
- [x] Ruff linting hatalari (booking/service.py)
- [x] CI test hatalari (test_orphan_migration.py idempotent fixture)
- [x] Backend test suite %100 yesil (0 FAILED, 0 ERROR - 680 passed)

### Urun Stratejisi
- [x] Urun konumlandirma reseti (cok urunlu acente otomasyonu)
- [x] Modul haritasi (cekirdek / destekleyici cekirdek / extension)
- [x] Dokumantasyon reseti (README, PRD, MODULE_MAP)

### Faz 2 - Router & Domain Ownership Cleanup (TAMAMLANDI - Subat 2026)
- [x] Dalga 1: Supplier domain konsolidasyonu (4 router tasinidi)
- [x] Dalga 2: Booking domain konsolidasyonu (11 router tasinidi)
- [x] Dalga 3: Finance domain konsolidasyonu (8 router tasinidi)
- [x] Dalga 4: Inventory & Pricing domain olusturuldu (yeni moduller)
- [x] Dalga 5: Public, Reporting, Extensions domain'lere dagitirildi
- [x] domain_router_registry.py temizlendi (REMAINING: 0 router)
- [x] 16 domain modulu aktif, ~160+ router konsolide edildi
- [x] Architecture Guard testi olusturuldu (cross-domain import kontrolu)
- [x] Domain Ownership Manifest dokumani olusturuldu

---

## P1 - Yuksek (Siradaki Sprint)
- [ ] Event-Driven Core Expansion
  - Daha fazla domain-specific worker ve event type
  - Consumer handler sayisini artirma
- [ ] Cache Strategy (L0/L1/L2)
  - MongoDB query cache
  - Redis session/response cache
  - CDN edge cache
- [ ] UI Sadelestirme & Bilgi Mimarisi (Faz 3)
  - Role-based menu pruning
  - Persona basina 5-7 ana is tanimi
  - Gorev bazli dashboard
  - Secondary navigation'a gelismis modulleri alma

## P2 - Orta
- [ ] Frontend Dependency Mismatch (yarn.lock regeneration)
- [ ] CI Quality Gates & Coverage raporu
- [ ] Dependency Audit (gereksiz paket temizligi)
- [ ] Urun Ici Analitik Altyapisi
  - Modul bazli kullanim skoru
  - Tenant bazli adoption score
  - Feature activation analytics
- [ ] Canli Mimari Dokumantasyon
  - Auto-generated route inventory
  - Module map senkronizasyonu
  - ADR (Architecture Decision Records)

## P3 - Gelecek
- [ ] Yeni Supplier Adapter'lari (Hotelbeds, Juniper)
- [ ] Frontend Persona Ayrimi (satis/operasyon/finans gorunumleri)
- [ ] Enterprise SLA Monitoring
- [ ] Per-Tenant Rate Limiting Enhancement
- [ ] Full Regression Test Suite

## Bilinen Teknik Borc
- [ ] yarn.lock mismatch (tekrarlayan, P3)
- [ ] Bazi schema dosyalari modules disinda (schemas_*.py)
- [ ] Router dosyalari hala routers/ altinda (Phase 3: domain icine tasima)
