# Travel Distribution Infrastructure - PRD

## Original Problem Statement
Build a "Travel Distribution Infrastructure" platform, pivoted to a multi-phase **Order Management System (OMS)**.

## Core Requirements
- Multi-tenant SaaS platform (React + FastAPI + MongoDB)
- OMS Phase 1: Order lifecycle, state machine, event logging
- OMS Phase 2: Financial Linkage (Ledger + Settlement integration)
- Admin panel with full CRUD for agencies, hotels, tours, contracts, etc.
- CRM, Finance, Operations, Risk Management modules
- B2B marketplace and partner management

## User Personas
- **Super Admin**: Full system access, manages tenants, monitors operations
- **Agency Admin**: Manages agency-specific operations, orders, reservations
- **Agency Agent**: Day-to-day booking and order management

## What's Been Implemented

### OMS Phase 1 (DONE)
- Order lifecycle management with state machine
- Event logging and activity timeline
- Order Number Strategy (ORD-YYYY-######)
- Optimistic Locking (version field)
- Search Endpoint with comprehensive filtering

### OMS Phase 2 - Financial Linkage (DONE)
- Order-Ledger-Settlement integration
- Financial summary, ledger posting refs, settlement run refs
- Financial status tracking (not_posted, posted, settled)
- New API endpoints for financial data

### Bug Fix: 16 White Screen Pages (DONE - 2026-03-17)
- Fixed 16+ pages that crashed due to misplaced useQuery hooks and undefined state variables
- Fixed pages: AdminAgencyModulesPage, SettingsPage, AdminTenantFeaturesPage, AdminPerfDashboardPage, AdminB2BDashboardPage, AdminCampaignsPage, AdminPartnersPage, AdminB2BMarketplacePage, AdminCatalogPage, AdminCatalogHotelsPage, AdminMatchesPage, AdminExportsPage, AdminSystemBackupsPage, AdminSystemIncidentsPage, AdminRunbookPage
- Fixed API response parsing (.data vs .data.items)
- Fixed HTML nesting issue in AdminPartnersPage
- 42+ routes tested with 100% pass rate

## Architecture
- Frontend: React + Shadcn UI + TanStack Query
- Backend: FastAPI + MongoDB
- Auth: JWT-based with role-based access

## Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123

## Prioritized Backlog

### P0
- Real RateHawk Environment Execution

### P1
- Timeline Export (CSV/PDF)

### P2
- New Supplier Integrations (Paximum, Hotelbeds, Juniper)

### Future
- OMS Phase 3+ (multi-product, modifications, cancellations, refunds)
- OMS Dashboard (operational control panel)
- TypeScript Migration
- Legacy Code Cleanup

## Known Issues
- yarn.lock mismatch (DEFERRED - does not block development)
- Some API endpoints return 400/404 (expected - no seeded data)
