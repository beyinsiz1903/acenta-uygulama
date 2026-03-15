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

## Frontend Architecture Report (2026-02)
Full analysis and redesign blueprint created at `/app/docs/FRONTEND_ARCHITECTURE_REPORT.md`

### Key Findings
- 101,864 lines of source code, 193 pages, 108 components
- 12 files over 1000 lines (god pages)
- TanStack Query installed but only 5% adopted
- No DataTable component — 50+ pages build their own tables
- Monolithic App.js (598 lines, all routes in one file)
- No TypeScript

### Proposed Architecture
- Domain-Driven Frontend: `/features/`, `/design-system/`, `/shared/`
- Syroce Design System (SDS): DataTable, PageShell, FilterBar, StatusBadge, EmptyState, Timeline
- TanStack Query 100% adoption with query key strategy
- Route-based code splitting
- Strangler Fig migration pattern

### Roadmap
| Phase | Scope | Effort |
|-------|-------|--------|
| Phase 1: Architecture Cleanup | Route splitting, features dir, TanStack Query hooks | 13 dev-days |
| Phase 2: Design System | DataTable, PageShell, FilterBar, tokens | 13 dev-days |
| Phase 3: UX Standardization | Migrate all pages to patterns | 14 dev-days |
| Phase 4: Performance | Code splitting, virtualization, memoization | 7 dev-days |
| Phase 5: Enterprise UX | Cmd+K, global search, shortcuts, timeline | 20 dev-days |

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

### Phase: Supplier Health & KPI Dashboard (2026-03-15) — COMPLETED
- `GET /api/inventory/supplier-health`
- `GET /api/inventory/kpi/drift`
- Frontend KPI Dashboard with all visualizations
- SUPPLIER_SIMULATION_ALLOWED config flag

## Upcoming Tasks (Prioritized)

### P0 — Frontend Architecture (Phase 1-2)
- Split App.js, create features/ structure
- Build DataTable, PageShell, FilterBar design system components
- Migrate top 10 pages to TanStack Query + new patterns

### P1 — Real Ratehawk Sandbox Validation
- CTO provides credentials → implement actual API calls in ratehawk_sync_adapter.py
- Test: search, price, availability, revalidation against real sandbox

### P2 — Paximum Sandbox & Reliability Engine
- Paximum sandbox adapter
- Supplier reliability score, drift monitoring, failover logic

### P3 — Pilot Phase
- 3 pilot agencies with real traffic
- 3 real bookings, 3 invoices, 3 accounting sync

## Known Issues
- P3: GitHub sync issue (platform-level, deferred)
- P4: Nested button HTML warning (de-prioritized)
- Redis unavailable in preview (MongoDB fallback working)
- Recharts width/height -1 console warning (cosmetic)

## Credentials
- **Super Admin:** `agent@acenta.test` / `agent123`
- **Agency Admin:** `agency1@demo.test` / `agency123`
