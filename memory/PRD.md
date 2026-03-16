# Syroce Travel SaaS — Product Requirements Document

## Original Problem Statement
CTO requested a comprehensive frontend architecture analysis and redesign to transform the "Syroce" Travel SaaS platform into an enterprise-grade product comparable to Stripe Dashboard or Shopify Admin. The project involves multi-phase implementation.

## Architecture
- **Frontend:** React + Vite, TanStack Query, Shadcn/UI, custom Design System (`/design-system/`)
- **Backend:** FastAPI + MongoDB
- **Design System Components:** PageShell, DataTable, FilterBar, StatusBadge, ConfirmDialog, Timeline, SdsEmptyState
- **Feature-based Organization:** `/features/{domain}/api.js` + `/features/{domain}/hooks.js`

## Completed Phases

### Phase 1: Architecture Cleanup (DONE)
- Route reorganization (admin, agency, core, hotel, b2b, public)
- Feature-based directory structure
- Lazy loading for all routes

### Phase 2: Design System Foundation (DONE)
- PageShell, DataTable, FilterBar, StatusBadge, ConfirmDialog, Timeline, SdsEmptyState
- Consistent enterprise UI patterns

### Phase 3 Batch 1: UX Standardization (DONE — 2026-03-15)
- ReservationsPage → PageShell + DataTable + FilterBar
- CrmCustomersPage → PageShell + DataTable (server-side pagination)
- AdminAgenciesPage → PageShell + DataTable + KPI cards
- DashboardPage → PageShell wrapper
- Bookings feature hooks updated (useBookings, useCancelBooking)

### Phase 3 Batch 2: UX Standardization (DONE — 2026-03-15)
- AgencyBookingsListPage → PageShell + DataTable + FilterBar + StatusBadge + useAgencyBookings hook
- ProductsPage → PageShell + DataTable + FilterBar + useProducts/useDeleteProduct hooks
- AdminAllUsersPage → PageShell + DataTable + FilterBar + StatusBadge + KPI cards + useAdminUsers/useAdminAgencies hooks
- OpsTasksPage → PageShell + DataTable + FilterBar + StatusBadge + useOpsTasks hook
- AdvancedReportsPage → PageShell wrapper (complex multi-card layout preserved)
- InventoryPage → PageShell wrapper (specialized calendar/grid UI preserved)
- AdminFinanceOpsPage → PageShell wrapper (tabbed reconciliation UI preserved)
- AdminFinanceExposurePage → PageShell wrapper (exposure table preserved)
- Test: 98.2% pass rate (56/57, 1 timeout = expected behavior)

### Phase 3c: Remaining Page Migrations (DONE — 2026-03-16)
- AdminScheduledReportsPage → PageShell + DataTable + TanStack Query (useScheduledReports, useCreateSchedule, useDeleteSchedule, useExecuteDueReports)
- AdminAccountingPage → PageShell + tabs (overview/rules/customers) + DataTable for sync jobs + TanStack Query (useAccountingDashboard, useSyncJobs, useRetryJob, useAccountingRules, useAccountingCustomers)
- B2BPortalPage → PageShell + tabs (flow/list) + component extraction (AccountSummaryCard, B2BDashboardKpiRow, QuoteBookCancelFlow, BookingListTab, PricePreviewDialog)
- New feature directories: features/reporting/, features/accounting/
- Test: 100% pass rate (40/40 tests passed + regression verified)

## Current Design System Adoption
- **15+ pages** using PageShell pattern
- **Unified DataTable** replacing 50+ custom table implementations
- **TanStack Query adoption:** ~20% (up from 15%)
- **Feature hook directories:** reporting, accounting, bookings, users, reports, products, operations, crm, finance, analytics, dashboard, governance

## Backlog (Prioritized)

### P0 — Phase 3d: "God Page" Splitting
- AdminFinanceRefundsPage (2150 LOC) → Split into components/hooks
- PlatformHardeningPage (1912 LOC, /pages/admin/) → Split into components/hooks
- B2BPortalPage (1734 LOC → already partially componentized in Phase 3c)

### P1 — TanStack Query Adoption (Target: 80%+)
- Continue migrating useEffect + useState patterns to TanStack Query hooks
- Current adoption: ~20%

### P2 — Phase 4: Performance
- Route-based code splitting
- List virtualization for large tables
- Bundle size optimization

### P3 — Phase 5: Enterprise UX
- Command Palette (Cmd+K)
- Global Search
- Keyboard shortcuts
- Activity Timeline

### P4 — TypeScript Migration
- API layer → hooks → design system components

## Known Issues
- React Router v7 future flag warnings (informational)
- 400 API errors for tenant context (backend state issue for super_admin)
- Ratehawk sync adapter uses MOCKED/simulated data

## Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
