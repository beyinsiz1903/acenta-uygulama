# PRD — Syroce: Acenta İşletim Sistemi (Multi-Product SaaS)

## Vizyon
Otel/tur acenteleri için uçtan uca dijital operasyon yönetim sistemi.
Admin, Agency, Hotel ve B2B persona'ları için görev odaklı arayüz.

## Mimari
- **Backend**: FastAPI + MongoDB + Celery + Redis
- **Frontend**: React + Shadcn/UI + React Router
- **Domain-Driven Design**: 16 bounded context (Faz 2'de tamamlandı)
- **Navigation**: Persona-based navigation platform (Faz 3 Sprint 1'de tamamlandı)

## Persona'lar
1. **Admin** — Sistem sahibi/operasyon yöneticisi (max 7 sidebar grubu)
2. **Agency** — Acenta operasyon kullanıcısı (max 7 sidebar grubu)
3. **Hotel** — Otel operasyon/kontrat kullanıcısı (max 7 sidebar grubu)
4. **B2B** — Bayi/partner (max 6 sidebar grubu, ayrı layout)

## Tamamlanan Fazlar

### Faz 1 — Mimari Analiz (Tamamlandı)
- Mevcut kod base'in analizi, bağımlılık haritası çıkarıldı

### Faz 2 — Router & Domain Ownership Cleanup (Tamamlandı)
- ~160+ legacy router, 16 bounded context'e migrate edildi
- domain_router_registry.py refactor edildi
- Architecture Guard testi oluşturuldu
- DOMAIN_OWNERSHIP_MANIFEST.md dokümante edildi

### Faz 3 — UI Simplification & Info Architecture
#### Sprint 1: Persona-Based Navigation Platform (Tamamlandı - 26.03.2026)
- Monolitik appNavigation.js (1038 satır) → persona bazlı 6 dosyaya bölündü
- navigation/personas/{admin,agency,hotel,b2b}.navigation.js
- navigation/shared/navigation.utils.js + navigation/index.js
- Her persona max 7 sidebar grubu görüyor
- directAccessOnly metadata ile eski route'lar korunuyor
- visibleInSidebar, visibleInSearch, legacy, directAccessOnly metadata
- Türkçe iş dili label'ları (modül adları yerine görev adları)
- PERSONA_IA.md ve MENU_PRUNING_MATRIX.md dokümantasyonu
- API response envelope auto-unwrap (Axios interceptor)
- PageErrorBoundary eklendi
- Tüm testler geçti (%100 frontend)

## Bekleyen İşler

### Sprint 2 (Sıradaki): Agency Dashboard & Ana Akış Ekranları
- Agency persona dashboard'u (görev odaklı, 4 blok: Bugün, KPI, Hızlı Aksiyon, Son Aktivite)
- Agency ana akış ekranlarının yeniden gruplaması
- Ölü route ve menü temizlikleri

### Sprint 3: Admin Dashboard & Yönetim Yüzeyi
- Admin dashboard (persona'ya özel)
- Ortak page shell / breadcrumb / section header standardı

### Sprint 4: Hotel + B2B Rollout
- Hotel ve B2B dashboard'ları
- Son temizlik, UX polish, demo senaryoları

### Gelecek Fazlar
- Fiziksel router taşınması (app/routers → modules/*/routers)
- CI Quality Gates & Coverage Visibility
- Dependency & Scope Control Audits
- Event-Driven Core Expansion
- Cache Strategy L0/L1/L2

## Bilinen Sorunlar
- Frontend yarn.lock dependency mismatch (P2, tekrarlayan)
- API 400 hataları (tenant/auth ile ilgili, non-blocking)
- test_paximum_unit "too many open files" (ortam limiti, kod hatası değil)
