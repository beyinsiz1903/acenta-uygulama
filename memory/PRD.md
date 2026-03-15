# Syroce Travel Platform — Product Requirements Document

## Original Problem Statement
CTO-driven Travel ERP platform (Syroce) with multi-supplier booking engine, revenue engine, invoice engine, accounting sync, finance ops, growth engine, pilot validation, and supplier drift monitoring. The platform is transitioning from a **Travel API Aggregator** to a **Travel Inventory Platform** (CTO decision — Option B).

## Core Architecture Decision (MEGA PROMPT #37)
**Travel Inventory Platform** — Enterprise architecture pattern used by Booking.com, Expedia, Travelport:
```
Supplier API → Inventory Sync Engine → MongoDB → Redis Cache → Search Engine
Search → Cache (NOT supplier API)
Booking → Supplier API (revalidation with diff tracking)
```

## Sandbox Architecture (MEGA PROMPT #38)
**Config-Driven Supplier Integration** — Sandbox-ready adapter pattern:
```
Credential Check → Has Credentials? → Real API (sandbox/production)
                 → No Credentials?  → Simulation Mode (if allowed)
                 → Simulation Disabled? → Error (production guard)
```

## Frontend Architecture Redesign (2026-03-15)
Full analysis at `/app/docs/FRONTEND_ARCHITECTURE_REPORT.md`

### Architecture Changes Completed (Phase 1+2)
- **App.js**: Reduced from 598 → 189 lines via domain route modules
- **Route Modules**: 6 files under `/src/routes/` (admin, agency, b2b, core, hotel, public)
- **Features Directory**: 9 domain modules under `/src/features/` with API + hooks
  - auth, dashboard, bookings, inventory, finance, crm, operations, analytics, governance
- **Design System (SDS)**: 7 pattern components under `/src/design-system/patterns/`
  - DataTable, PageShell, FilterBar, StatusBadge, ConfirmDialog, Timeline, EmptyState
- **Shared Layer**: Centralized query key registry at `/src/shared/queryKeys.js`
- **TanStack React Table**: Installed for DataTable component

### Key Findings (Pre-Refactor)
- 101,864 lines of source code, 193 pages, 108 components
- 12 files over 1000 lines (god pages)
- TanStack Query installed but only 5% adopted
- 50+ pages with hand-built tables (DataTable now available)
- Monolithic App.js (598 lines → now 189)

### New Directory Structure
```
src/
├── routes/          # Domain route modules (6 files)
├── features/        # Domain modules with api.js + hooks.js (9 domains)
├── design-system/   # SDS pattern components (7 components)
├── shared/          # Cross-cutting: queryKeys.js
├── components/      # Legacy shared components (being migrated)
├── pages/           # Legacy page components (being migrated)
├── hooks/           # Legacy hooks (backward-compatible re-exports)
├── lib/             # Legacy utilities
└── App.js           # Slim entry point (189 lines)
```

## Implemented Features

### Phase: Simulation Complete
- 10/10 successful simulation flows
- `supplier_response_diff` metric
- Pilot Dashboard with KPIs

### Phase: Inventory Sync Engine (MEGA PROMPT #37)
- `POST /api/inventory/sync/trigger`
- `GET /api/inventory/sync/status`
- `GET /api/inventory/sync/jobs`
- `GET /api/inventory/search`
- `GET /api/inventory/stats`
- `POST /api/inventory/revalidate`

### Phase: Sandbox Integration (MEGA PROMPT #38)
- `GET /api/inventory/supplier-config`
- `POST /api/inventory/supplier-config`
- `DELETE /api/inventory/supplier-config/{supplier}`
- `POST /api/inventory/sandbox/validate`
- `GET /api/inventory/supplier-metrics`

### Phase: Supplier Health & KPI Dashboard — COMPLETED
- `GET /api/inventory/supplier-health`
- `GET /api/inventory/kpi/drift`
- Frontend KPI Dashboard with all visualizations
- SUPPLIER_SIMULATION_ALLOWED config flag

### Phase: Frontend Architecture (Phase 1+2) — COMPLETED
- Route splitting into 6 domain modules
- Features directory with 9 domain API + hook modules
- Design System with 7 pattern components
- All tests PASS (100% frontend success rate)

## Upcoming Tasks (Prioritized)

### P0 — Page Migration (Phase 3 - UX Standardization)
- Migrate DashboardPage to use PageShell + DataTable
- Migrate ReservationsPage to use DataTable + FilterBar + StatusBadge
- Migrate AdminAgenciesPage to new patterns
- Standardize loading/error/empty states across all pages

### P1 — God Page Splitting
- Split AdminFinanceRefundsPage (2150 lines)
- Split PlatformHardeningPage (1912 lines)
- Split B2BPortalPage (1734 lines)
- Split AdminMetricsPage (1326 lines)
- Split UnifiedSearchPage (1257 lines)

### P2 — Performance Optimization (Phase 4)
- Route-based code splitting with named chunks
- Virtualized tables for large datasets
- React.memo on key components
- Bundle analysis + tree-shaking audit

### P3 — Enterprise UX (Phase 5)
- Command palette (Cmd+K) using cmdk
- Global search with unified results
- Keyboard shortcuts framework
- Activity timeline on entity pages

### Backlog
- Real Ratehawk Sandbox Validation
- Paximum Sandbox & Reliability Engine
- TypeScript migration (incremental)
- CI/CD pytest fix (test_inventory_sync_iter103.py)

## Known Issues
- P3: GitHub sync issue (platform-level, deferred)
- P4: Nested button HTML warning (de-prioritized)
- Redis unavailable in preview (MongoDB fallback working)
- Recharts width/height -1 console warning (cosmetic)

## Credentials
- **Super Admin:** `agent@acenta.test` / `agent123`
- **Agency Admin:** `agency1@demo.test` / `agency123`
