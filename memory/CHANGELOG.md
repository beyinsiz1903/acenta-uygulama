# CHANGELOG — Syroce

## [2026-03-26] Faz 3 Sprint 4: Hotel & B2B Dashboard + Cmd+K Enrichment

### Eklenen
- `components/CommandPalette.jsx` — Persona-bazlı dinamik navigasyon araması (hardcoded liste kaldırıldı)
- `pages/HotelDashboardPage.jsx` — Otel operasyon dashboard'u (5 blok)
- `pages/B2BDashboardPage.jsx` — B2B ticari dashboard (5 blok)
- `hooks/useHotelDashboard.js` — React Query hook (/api/dashboard/hotel-today)
- `hooks/useB2BDashboard.js` — React Query hook (/api/dashboard/b2b-today)
- `backend/app/routers/dashboard_hotel.py` — Hotel daily overview endpoint (12 paralel query)
- `backend/app/routers/dashboard_b2b.py` — B2B daily overview endpoint (13 paralel query)

### Değiştirilen
- `components/AppShell.jsx` — CommandPalette'e persona prop'u iletiliyor
- `routes/coreRoutes.jsx` — DashboardRouter'a hotel persona eklendi
- `routes/hotelRoutes.jsx` — Dashboard route eklendi, index → dashboard redirect
- `routes/b2bRoutes.jsx` — B2BDashboardPage route eklendi
- `b2b/B2BLayout.jsx` — "Ana Panel" nav link eklendi (/b2b/dashboard)
- `navigation/personas/hotel.navigation.js` — Dashboard path /app/hotel/dashboard olarak güncellendi
- `navigation/personas/b2b.navigation.js` — Dashboard path /b2b/dashboard olarak güncellendi
- `modules/reporting/__init__.py` — dashboard_hotel ve dashboard_b2b router'ları eklendi
- `App.js` — Hotel route auth'a admin/super_admin eklendi

### Düzeltilen
- `backend/app/routers/dashboard_agency.py` — Kullanılmayan import (Query) ve değişken (tomorrow_end) kaldırıldı

### Notlar
- Cmd+K: Admin 115, Agency 20 sayfa görüyor (persona izolasyonu)
- directAccessOnly öğeler "gizli" badge'ı ile Cmd+K'da aranabilir
- Hotel dashboard: check-in/out, doluluk, uyarılar, bekleyenler, varışlar
- B2B dashboard: pipeline, partner, onaylar, ciro, son satışlar
- Test raporu: backend 20/20, frontend %100 (iteration_152.json)

---

## [2026-03-26] Faz 3 Sprint 3: Admin Dashboard & Yönetim Yüzeyi

### Eklenen
- `pages/AdminDashboardPage.jsx` — Yönetim odaklı Admin dashboard (6 blok)
- `hooks/useAdminDashboard.js` — React Query hook (/api/dashboard/admin-today)
- `backend/app/routers/dashboard_admin.py` — Admin daily overview endpoint (18 paralel query)

### Değiştirilen
- `routes/coreRoutes.jsx` — DashboardRouter: admin → AdminDashboardPage eklendi
- `modules/reporting/__init__.py` — dashboard_admin_router eklendi
- `pages/DashboardPage.jsx` — Feature-gated /reports/* çağrıları temizlendi (403 console noise)

### Düzeltilen
- yarn.lock dependency mismatch (silindi, yeniden oluşturuldu)
- API 403 feature_not_enabled console hataları (dashboard'dan /reports/* çağrıları kaldırıldı)

---

## [2026-03-26] Faz 3 Sprint 2: Agency Dashboard & Görev Odaklı Kontrol Paneli

### Eklenen
- `pages/AgencyDashboardPage.jsx` — Görev odaklı Agency dashboard (4 blok)
- `hooks/useAgencyDashboard.js` — React Query hook (/api/dashboard/agency-today)
- `backend/app/routers/dashboard_agency.py` — Agency daily overview endpoint (11 paralel query)

--- 

## [2026-03-26] Faz 3 Sprint 1: Persona-Based Navigation Platform

### Eklenen
- `navigation/personas/{admin,agency,hotel,b2b}.navigation.js`
- `navigation/shared/navigation.utils.js` — resolvePersona(), flattenNavItems(), filterSidebarItems()
- `navigation/index.js` — Merkezi export

---

## [2026-03-25] Faz 2: Router & Domain Ownership Cleanup

### Eklenen
- 4 yeni domain modülü: inventory, pricing, public, reporting
- Architecture Guard testi: test_architecture_guard.py
- DOMAIN_OWNERSHIP_MANIFEST.md
