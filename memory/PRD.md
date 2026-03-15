# Syroce Travel SaaS — PRD

## Original Problem Statement
CTO-requested comprehensive frontend architecture analysis and redesign to transform the existing "Syroce" Travel SaaS platform into an enterprise-grade product comparable to Stripe Dashboard or Shopify Admin.

## Architecture Plan
Detailed in `/app/docs/FRONTEND_ARCHITECTURE_REPORT.md`

## Tech Stack
- **Frontend:** React, TailwindCSS, Shadcn/UI, @tanstack/react-table, @tanstack/react-query, Recharts
- **Backend:** FastAPI, MongoDB
- **Design System:** `/src/design-system/patterns/` — DataTable, PageShell, FilterBar, StatusBadge, ConfirmDialog, Timeline, EmptyState

---

## Completed Phases

### Phase 1 — Architecture Cleanup (DONE)
- App.jsx refactored: 598 LOC → 189 LOC
- Modular routing: `/src/routes/` (admin, agency, b2b, core, hotel, public)
- Domain-driven features: `/src/features/` (auth, dashboard, bookings, inventory, finance, crm, operations, analytics, governance)

### Phase 2 — Design System Foundation (DONE)
- Created 7 reusable design system components
- Installed @tanstack/react-table
- 100% test pass (iteration_1.json)

### Phase 3 — UX Standardization (IN PROGRESS)
**Migrated Pages:**
- **ReservationsPage** → PageShell + DataTable + FilterBar + StatusBadge + TanStack Query hooks
- **AdminAgenciesPage** → PageShell + DataTable + FilterBar + StatusBadge + KPI Cards
- **CrmCustomersPage** → PageShell + DataTable + FilterBar + Server-side Pagination
- **DashboardPage** → PageShell wrapper (preserving widgets/charts)
- **CustomersPage** → PageShell + DataTable + FilterBar + ConfirmDialog (legacy route)

**Test Result:** 93.1% pass rate (iteration_107.json). All core flows verified working.

---

## Remaining Phase 3 Work (P0)
Target pages still to migrate:
- BookingsPage (hotel/agency variants)
- FinanceLedgerPage
- InventoryPage / ProductsPage
- AdminUsersPage
- OperationsPage (OpsCasesPage)
- ReportsPage

## God Page Splitting (P1)
| Page | LOC |
|------|-----|
| AdminFinanceRefundsPage | 2150 |
| PlatformHardeningPage | 1912 |
| B2BPortalPage | 1734 |

## Phase 4 — Performance (P2)
- Route code splitting
- Virtualized tables
- Bundle optimization

## Phase 5 — Enterprise UX (P2)
- Cmd+K command palette
- Global search
- Keyboard shortcuts

## TypeScript Migration (P3)
- Incremental: API layer → hooks → design system

---

## Known Issues
- "Tenant context bulunamadı" for super_admin on CRM page (backend issue)
- Ratehawk sync adapter uses simulated data (MOCKED)
- React Router v7 future flag warnings (informational)

## Test Credentials
- **Super Admin:** agent@acenta.test / agent123
- **Agency Admin:** agency1@demo.test / agency123

## Key Documents
- `/app/docs/FRONTEND_ARCHITECTURE_REPORT.md` — Master architecture plan
- `/app/docs/EXECUTIVE_SUMMARY.md` — CTO executive summary
- `/app/test_reports/iteration_1.json` — Phase 1+2 test results
- `/app/test_reports/iteration_107.json` — Phase 3 test results
