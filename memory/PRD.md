# PRD — Syroce: Acenta İşletim Sistemi (Multi-Product SaaS)

## Vizyon
Otel/tur acenteleri için uçtan uca dijital operasyon yönetim sistemi.
Admin, Agency, Hotel ve B2B persona'ları için görev odaklı arayüz.

## Mimari
- **Backend**: FastAPI + MongoDB + Celery + Redis
- **Frontend**: React + Shadcn/UI + React Router
- **Domain-Driven Design**: 16 bounded context (Faz 2'de tamamlandı)
- **Navigation**: Persona-based navigation platform (Faz 3 Sprint 1'de tamamlandı)
- **Dashboard**: Persona-based dashboards — Admin, Agency, Hotel, B2B (Faz 3 Sprint 2-4'te tamamlandı)
- **Command Palette**: Persona-based Cmd+K search (Faz 3 Sprint 4'te tamamlandı)

## Persona'lar
1. **Admin** — Sistem sahibi/operasyon yöneticisi (max 7 sidebar grubu, ~115 aranabilir sayfa)
2. **Agency** — Acenta operasyon kullanıcısı (max 7 sidebar grubu, ~20 aranabilir sayfa)
3. **Hotel** — Otel operasyon/kontrat kullanıcısı (max 7 sidebar grubu, özel dashboard)
4. **B2B** — Bayi/partner (max 6 sidebar grubu, ayrı layout, özel dashboard)

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
- Monolitik appNavigation.js → persona bazlı 6 dosyaya bölündü
- visibleInSidebar, visibleInSearch, legacy, directAccessOnly metadata
- Türkçe iş dili label'ları
- API response envelope auto-unwrap (Axios interceptor)

#### Sprint 2: Agency Dashboard (Tamamlandı - 26.03.2026)
- AgencyDashboardPage.jsx — 4 bloklı dashboard
- Backend: /api/dashboard/agency-today endpoint (11 paralel sorgu)

#### Sprint 3: Admin Dashboard (Tamamlandı - 26.03.2026)
- AdminDashboardPage.jsx — 6 bloklı dashboard
- Backend: /api/dashboard/admin-today endpoint (18 paralel sorgu)

#### Sprint 4: Hotel & B2B Dashboard + Cmd+K Enrichment (Tamamlandı - 26.03.2026)
- **Cmd+K Command Palette Zenginleştirme**:
  - Hardcoded 9 sayfa listesi → Persona-bazlı dinamik navigasyon
  - flattenNavItems() + visibleInSearch filter
  - directAccessOnly öğeler "gizli" badge'ı ile aranabilir
  - Admin: 115 sayfa, Agency: 20 sayfa (persona izolasyonu)
  - legacy: true öğeler filtreleniyor
  - Grup bazlı sonuç görüntüleme (DASHBOARD, OPERASYON, vb.)
  - moduleAliases ile genişletilmiş arama
- **Hotel Dashboard**: HotelDashboardPage.jsx — 5 bloklı
  - Check-in/Check-out KPI (bugün, yarın, aktif konaklama)
  - Doluluk & Müsaitlik (kontenjan, stop sell, haftalık rez)
  - Kritik Uyarılar (dinamik threshold)
  - Bekleyen Rezervasyonlar & İptaller
  - Yaklaşan Varışlar (7 gün) + Son Aktiviteler
  - Backend: /api/dashboard/hotel-today (12 paralel sorgu)
- **B2B Dashboard**: B2BDashboardPage.jsx — 5 bloklı
  - Satış Pipeline (açık teklif, kazanılan, kaybedilen, dönüşüm oranı)
  - Partner Performansı (aktif partner, bekleyen onay)
  - Bekleyen Onaylar (rez + partner başvuruları)
  - Tahsilat & Ciro Özeti (aylık, haftalık)
  - Son B2B Satışlar + Son Aktiviteler
  - Backend: /api/dashboard/b2b-today (13 paralel sorgu)
- DashboardRouter: Admin→AdminDashboard, Agency→AgencyDashboard, Hotel→HotelDashboard
- B2B Layout güncellendi ("Ana Panel" nav link)
- Hotel auth: super_admin + admin artık hotel route'larına erişebilir
- Tüm testler geçti (iteration_152.json: backend 20/20, frontend %100)

## Bekleyen İşler

### Gelecek Fazlar
- Fiziksel router taşınması (app/routers → modules/*/routers)
- CI Quality Gates & Coverage Visibility
- Dependency & Scope Control Audits
- Event-Driven Core Expansion
- Cache Strategy L0/L1/L2
- Auto-generated Live Architecture Docs
- In-Product Analytics & Usage Visibility

## Bilinen Sorunlar
- Frontend yarn.lock dependency mismatch (Çözüldü - 26.03.2026)
- API 400/403 hataları (/reports/* feature-gated) (Çözüldü - 26.03.2026)
- test_paximum_unit "too many open files" (ortam limiti, kod hatası değil)
- CommandDialog aria-describedby uyarısı (shadcn UI bileşeni, minör erişilebilirlik)
