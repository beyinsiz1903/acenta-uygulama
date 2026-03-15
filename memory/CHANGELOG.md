# Syroce Changelog

## 2026-03-15 — Frontend Architecture Phase 1+2 (Route Splitting + Design System)
- **Route Modules**: Split App.js (598→189 lines) into 6 domain route files under `/src/routes/`
  - adminRoutes.jsx (219 lines), coreRoutes.jsx (109 lines), publicRoutes.jsx (65 lines)
  - agencyRoutes.jsx (50 lines), hotelRoutes.jsx (26 lines), b2bRoutes.jsx (19 lines)
- **Features Directory**: Created 9 domain modules under `/src/features/` with API layers + TanStack Query hooks
  - auth, dashboard, bookings, inventory, finance, crm, operations, analytics, governance
- **Design System (SDS)**: Built 7 pattern components under `/src/design-system/patterns/`
  - DataTable (sort, filter, paginate, select, loading, empty states)
  - PageShell (title, description, breadcrumbs, actions, tabs)
  - FilterBar (search, dropdowns, active filter chips, reset)
  - StatusBadge (semantic colors with dot indicators)
  - ConfirmDialog (destructive/default variants, loading state)
  - Timeline (activity events with icons, relative time, metadata)
  - EmptyState (5 variants: default, search, error, no-permission, onboarding)
- **Shared Layer**: Centralized query key registry at `/src/shared/queryKeys.js`
- **Dependencies**: Added @tanstack/react-table@8.21.3
- **Testing**: 100% frontend pass rate, all routes verified, no regressions

## 2026-03-15 — Frontend Architecture Analysis Report
- Created comprehensive 10-step analysis at `/app/docs/FRONTEND_ARCHITECTURE_REPORT.md`
- Identified: 101,864 LOC, 193 pages, 12 god pages, 5% TanStack Query adoption
- Proposed domain-driven architecture with 5-phase roadmap (67 dev-days)

## 2026-03-15 — Inventory Sync Engine (MEGA PROMPT #37)
- **Architecture Decision**: CTO approved Option B — Travel Inventory Platform
- **Backend**: Created `inventory_sync_service.py` with full sync engine
- **Frontend**: Created `InventorySyncDashboardPage.jsx` with KPIs
- **Testing**: 28/28 backend tests PASS, 100% frontend verified

## 2026-03-15 — Supplier Response Diff (Previous Session)
- Implemented `supplier_response_diff` metric
- 9/9 backend tests PASS, 10/10 simulation flows PASS

## Previous Sessions
- Pilot flow simulation system
- Pilot dashboard with Flow Health, Supplier Metrics, Finance Metrics
- Supplier adapters (Ratehawk, Paximum, WWTatil, TBO)
- Full travel ERP platform features
