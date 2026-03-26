# PRD -- Syroce: Acente Bulut Otomasyonu

## Urun Tanimi
Syroce, turizm acentelerinin otel, tur, ucus ve B2B islemlerini tek platformda yoneten
cok urunlu SaaS acente isletim sistemidir.

## Hedef Kullanicilar
- Admin (Sistem yoneticisi)
- Acente (Satis & operasyon)
- Otel (Envanter & musaitlik)
- B2B (Ag/partner yonetimi)
- Finans (Odeme & raporlama)

## Temel Gereksinimler
1. Cok-kiracili (multi-tenant) mimari, organization_id bazli izolasyon
2. Domain-driven modul yapisi (16 bounded context)
3. Booking state machine (tek dogru kaynak)
4. Supplier entegrasyonu (adapter pattern, circuit breaker)
5. B2B marketplace & exchange
6. Finans: faturalama, odeme, mutabakat, ledger
7. Webhook sistemi (HMAC, retry, DLQ)
8. Event-driven outbox pattern

## Mimari
- Backend: FastAPI + MongoDB + Celery + Redis
- Frontend: React + Shadcn UI
- 16 Domain Modulu: auth, identity, booking, b2b, supplier, finance, crm,
  operations, enterprise, system, inventory, pricing, public, reporting, tenant, webhooks
- Router registry: domain_router_registry.py (tum router'lar domain modullerinde)

## Tamamlanan Calisma
- Faz 1: Dokumantasyon & Konumlandirma (Subat 2026)
- P0: Backend test suite %100 yesil (Subat 2026)
- Faz 2: Router & Domain Ownership Cleanup - TUM DALGALAR (Subat 2026)
  - 16 domain modulu, ~160+ router konsolide, REMAINING: 0
  - Architecture Guard testi, Domain Ownership Manifest

## Siradaki Hedefler
- Faz 3: UI Sadelestirme & Bilgi Mimarisi
- Event-Driven Core Expansion
- Cache Strategy L0/L1/L2
