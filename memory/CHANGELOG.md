# CHANGELOG — Syroce

## [2026-03-26] Faz 3 Sprint 2: Agency Dashboard & Görev Odaklı Kontrol Paneli

### Eklenen
- `pages/AgencyDashboardPage.jsx` — Görev odaklı Agency dashboard (4 blok)
- `hooks/useAgencyDashboard.js` — React Query hook (/api/dashboard/agency-today)
- `backend/app/routers/dashboard_agency.py` — Agency daily overview endpoint (11 paralel query)
- Persona-aware `DashboardRouter` bileşeni (`coreRoutes.jsx`)

### Değiştirilen
- `routes/coreRoutes.jsx` — DashboardRouter ile persona bazlı dashboard yönlendirmesi
- `modules/reporting/__init__.py` — dashboard_agency_router eklendi
- `bootstrap/router_registry.py` — dashboard_agency_router import & include

### Notlar
- Agency kullanıcıları /app'te görev odaklı dashboard görüyor
- Admin kullanıcıları mevcut Yönetim Panosu'nu görmeye devam ediyor
- user_name serialization düzeltmesi (obje → string)
- Test raporu: backend 10/10, frontend %100 (iteration_150.json)

--- [2026-03-26] Faz 3 Sprint 1: Persona-Based Navigation Platform

### Eklenen
- `navigation/personas/admin.navigation.js` — Admin persona navigasyon tanımı (7 sidebar grubu, ~100 öğe)
- `navigation/personas/agency.navigation.js` — Agency persona navigasyon tanımı (7 sidebar grubu)
- `navigation/personas/hotel.navigation.js` — Hotel persona navigasyon tanımı (5 aktif sidebar grubu)
- `navigation/personas/b2b.navigation.js` — B2B persona navigasyon tanımı (6 sidebar grubu)
- `navigation/shared/navigation.utils.js` — resolvePersona(), flattenNavItems(), filterSidebarItems()
- `navigation/index.js` — Merkezi export (getPersonaNavSections, getPersonaAccountLinks)
- `components/PageErrorBoundary.jsx` — Sayfa bazlı hata yakalayıcı
- `docs/PERSONA_IA.md` — Persona bilgi mimarisi dokümanı
- `docs/MENU_PRUNING_MATRIX.md` — Menü budama matrisi (keep/merge/remove/hide kararları)

### Değiştirilen
- `components/AppShell.jsx` — lib/appNavigation yerine navigation/ modülü kullanıyor; PageErrorBoundary eklendi
- `lib/api.js` — Axios response interceptor'a otomatik envelope unwrap eklendi ({ok, data, meta} → data)
- `hooks/useAuth.js` — Login envelope unwrap yorumu güncellendi (interceptor tarafından yönetiliyor)

### Düzeltilen
- Agency dashboard WeeklySummaryTable crash (response envelope unwrap sorunu)
- ReservationsPage crash (aynı sebep)
- Tüm API yanıtları artık otomatik olarak envelope'dan çıkarılıyor

### Notlar
- Eski appNavigation.js dosyası bozulmadı (AdminAllModulesPage hâlâ kullanıyor)
- Tüm route'lar backward compatible — sidebar'dan kaldırılan menüler URL ile erişilebilir
- directAccessOnly metadata sayesinde "üründen kaldırıldı" ≠ "teknik olarak erişilemez"

---

## [2026-03-25] Faz 2: Router & Domain Ownership Cleanup

### Eklenen
- 4 yeni domain modülü: inventory, pricing, public, reporting
- Architecture Guard testi: test_architecture_guard.py
- DOMAIN_OWNERSHIP_MANIFEST.md

### Değiştirilen
- domain_router_registry.py — 400+ satırdan ~50 satıra (16 domain aggregator)
- ~160+ legacy router mantıksal olarak bounded context'lere taşındı
