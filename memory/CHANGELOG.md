# CHANGELOG -- Syroce

## [2026-02-XX] Faz 2: Router & Domain Ownership Cleanup

### Eklendi
- Yeni domain modulleri olusturuldu:
  - `modules/inventory/` -- otel, oda, musaitlik, PMS, sheets, arama (24 router)
  - `modules/pricing/` -- fiyatlama, marketplace, teklifler (12 router)
  - `modules/public/` -- storefront, public search, checkout, SEO (13 router)
  - `modules/reporting/` -- raporlar, analytics, dashboard, export (10 router)
- Architecture Guard testi (`tests/test_architecture_guard.py`)
- Domain Ownership Manifest (`docs/DOMAIN_OWNERSHIP_MANIFEST.md`)

### Degistirildi
- `domain_router_registry.py` tamamen yeniden yazildi:
  - Onceki: ~413 satir, ~109 router "REMAINING" bolumunde
  - Simdi: ~160 satir, 16 domain import, 0 REMAINING router
- Mevcut domain modulleri guncellendi (yeni router'lar eklendi):
  - `modules/supplier/` -- +4 router (activation, credentials, aggregator, ecosystem)
  - `modules/booking/` -- +11 router (legacy, vouchers, matches, unified)
  - `modules/finance/` -- +9 router (ledger, settlements, OMS, accounting)
  - `modules/system/` -- +20 router (platform layers, admin misc, extensions)
  - `modules/enterprise/` -- +3 router (risk, policies, approvals)
  - `modules/operations/` -- +1 router (tickets)
  - `modules/b2b/` -- +3 router (partner_graph, partner_v1, admin_partners)
  - `modules/crm/` -- +2 router (inbox, inbox_v2)

### Test Durumu
- Architecture Guard: PASSED (0 cross-domain violation)
- Supplier tests: 6 passed
- Tenant isolation tests: 32 passed
- Admin settlements, pricing, ical tests: PASSED
- Backend startup: OK

## [2026-02-XX] Faz 1: Dokumantasyon & Konumlandirma Reseti

### Eklendi
- `docs/MODULE_MAP.md` -- domain boundary tanimlari
- `docs/COMMERCIAL_PACKAGES.md` -- lisanslama mimarisi
- `docs/TEST_ISOLATION_POLICY.md` -- test kurallari

### Degistirildi
- `PRD.md` -- cok urunlu SaaS tanimiyla guncellendi
- `README.md` -- sifirdan yazildi

## [2026-02-XX] P0: Test Suite Stabilizasyonu
- Backend test suite 680 passed, 0 failed, 0 error
- conftest.py fixture'lari (retry logic, graceful skips)
- Supplier circuit test DB state duzeltmesi
