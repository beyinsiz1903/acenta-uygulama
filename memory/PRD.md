# PRD - Acenta Master Travel Management Platform

## Original Problem Statement
Full-stack travel management (acenta) application with B2B agency management, hotel portfolio sync via Google Sheets, reservations, CRM, finance, and operations modules.

## Core Architecture
- **Frontend:** React (CRA + Tailwind + shadcn/ui)
- **Backend:** FastAPI (Python)
- **Database:** MongoDB
- **Auth:** JWT-based with role-based access control

## User Roles
- `super_admin` / `admin` - Full platform access
- `agency_admin` / `agency_agent` - B2B agency portal
- `hotel_admin` / `hotel_staff` - Hotel portal

## What's Been Implemented

### Google Sheets Integration (Feb 2026)
- Admin + Agency portal sheet connections
- Manual sync, sync status badges, error details

### Infrastructure (Feb 27, 2026)
- Root cleanup, seed refactoring, orphan org cleanup
- Cache warmup expansion (+agencies, hotels, FX, pricing rules)
- Seed on startup with idempotent data creation

### Per-Agency Module Management (Feb 27, 2026)
- **Backend:** GET/PUT `/api/admin/agencies/{id}/modules` — store allowed_modules per agency
- **Backend:** GET `/api/agency/profile` — agency users fetch their allowed modules
- **Admin UI:** `/app/admin/agency-modules` — checkbox grid to configure tabs per agency

### Branding Restriction (Feb 27, 2026)
- **Backend:** `can_edit_name` flag in whitelabel-settings response (true only for super_admin)
- **Frontend:** company_name input readonly for non-super_admin users

### Super Admin Unified User Management (Feb 27, 2026)
- **Backend:** GET `/api/admin/all-users` — all agency users with agency_name
- **Frontend:** `/app/admin/all-users` — search, filter, role/status management
- **Sidebar:** "Kullanici Yonetimi" link under YONETIM

### Dynamic Agency Navigation (Feb 27, 2026)
- AppShell fetches `/api/agency/profile` for agency users
- Sidebar items filtered by `allowed_modules` modeKey matching
- Empty allowed_modules = no restriction (all visible)

### DB Index Cleanup (Feb 27, 2026)
- `_safe_create` now uses OperationFailure error codes (85, 86, 13) instead of string matching
- Removed bare `except Exception` that silently swallowed all errors
- Removed match_alert_deliveries migration workaround (one-time index rename)
- perf_indexes import no longer wrapped in try/except

### Cache Warm-up Expansion (Feb 27, 2026)
- Added: product_counts, reservation_summary, agency_modules, onboarding state
- Total warm-up sources: tenant features, CMS nav, campaigns, agencies, hotels, FX rates, pricing rules, product counts, reservation summaries, agency module settings, onboarding state

## Key Files
- `backend/app/routers/admin_agency_users.py` - Per-agency user CRUD + all_users_router
- `backend/app/routers/admin_agencies.py` - Agency CRUD + module management
- `backend/app/routers/agency_profile.py` - Agency profile endpoint
- `backend/app/indexes/seed_indexes.py` - Consolidated DB indexes
- `backend/app/services/cache_warmup.py` - Startup cache warm-up
- `frontend/src/pages/AdminAllUsersPage.jsx` - Unified user management UI
- `frontend/src/pages/AdminAgencyModulesPage.jsx` - Module config UI
- `frontend/src/components/AppShell.jsx` - Sidebar with dynamic agency module filtering

## Credentials
| Portal | Email | Password | Role |
|--------|-------|----------|------|
| Admin | admin@acenta.test | admin123 | Super Admin |
| Agency | agent@acenta.test | agent123 | Agency Admin |

## Backlog
- P2: Apple Watch UI
- P2: Google Sheets sync testing (requires Service Account JSON)
