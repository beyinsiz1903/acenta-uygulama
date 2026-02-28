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

### Deployment Fixes (Feb 27, 2026)
- **Fix:** Removed unused `serialize_doc` import from `agency_profile.py` (Ruff lint CI failure)
- **Fix:** Simplified `_db_name()` in `db.py` — removed dual-source DB name logic (DB_NAME env + MONGO_URL path extraction) that caused `INVALID_DATABASE_NAME` error during MongoDB Atlas migration (name was duplicated with comma)
- **Fix:** Removed comments from `backend/.env` to prevent deployment parser issues

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

### Super Admin Unified User Management - CRUD Complete (Feb 27, 2026)
- **Backend:** GET `/api/admin/all-users` — all agency users with agency_name
- **Backend:** POST `/api/admin/all-users` — create new agency user with email, name, password, agency_id, role
- **Backend:** PUT `/api/admin/all-users/{user_id}` — update user name, email, role, status, agency_id
- **Backend:** DELETE `/api/admin/all-users/{user_id}` — hard delete user
- **Frontend:** `/app/admin/all-users` — full CRUD with search, filter, role/status management
- **Frontend:** Create user dialog (name, email, password, agency, role fields)
- **Frontend:** Edit user dialog (name, email, agency, role, status fields)
- **Frontend:** Delete user confirmation dialog (hard delete)
- **Sidebar:** "Kullanici Yonetimi" link under YONETIM

### Dynamic Agency Navigation (Feb 27, 2026)
- AppShell fetches `/api/agency/profile` for agency users
- Sidebar items filtered by `allowed_modules` modeKey matching
- Empty allowed_modules = no restriction (all visible)

### DB Index Cleanup (Feb 27, 2026)
- `_safe_create` now uses OperationFailure error codes (85, 86, 13) instead of string matching
- Removed bare `except Exception` that silently swallowed all errors

### Cache Warm-up Expansion (Feb 27, 2026)
- Added: product_counts, reservation_summary, agency_modules, onboarding state
- Total warm-up sources: tenant features, CMS nav, campaigns, agencies, hotels, FX rates, pricing rules, product counts, reservation summaries, agency module settings, onboarding state

## Key Files
- `backend/app/routers/admin_agency_users.py` - Per-agency user CRUD + all_users_router (GET/POST/PUT/DELETE)
- `backend/app/routers/admin_agencies.py` - Agency CRUD + module management
- `backend/app/routers/agency_profile.py` - Agency profile endpoint
- `backend/app/indexes/seed_indexes.py` - Consolidated DB indexes
- `backend/app/services/cache_warmup.py` - Startup cache warm-up
- `frontend/src/pages/AdminAllUsersPage.jsx` - Unified user management UI with CRUD dialogs
- `frontend/src/pages/AdminAgencyModulesPage.jsx` - Module config UI
- `frontend/src/components/AppShell.jsx` - Sidebar with dynamic agency module filtering

## Key API Endpoints
- `GET /api/admin/all-users` - List all agency users across agencies
- `POST /api/admin/all-users` - Create new agency user
- `PUT /api/admin/all-users/{user_id}` - Update agency user
- `DELETE /api/admin/all-users/{user_id}` - Delete agency user
- `GET /api/me/modules` - Agency user's allowed modules

## Credentials
| Portal | Email | Password | Role |
|--------|-------|----------|------|
| Admin | admin@acenta.test | admin123 | Super Admin |
| Agency | agent@acenta.test | agent123 | Agency Admin |

## Backlog
- P2: Apple Watch UI
- P2: Google Sheets sync testing (requires Service Account JSON)

### Bug Fix: React Error #31 - {tr, en} Object Rendering (Feb 28, 2026)
- **Root cause:** `dashboard/popular-products` API returned `product_name` as `{tr: "...", en: "..."}` object from MongoDB. DashboardPage.jsx rendered this directly in a `<p>` tag, crashing the entire React tree.
- **Backend fix:** Added `_str_name()` helper in `dashboard_enhanced.py` to flatten multilingual objects to strings. Applied to all `product_name`, `hotel_name`, `tour_name` fields across `popular-products`, `reservation-widgets`, and abandoned data endpoints.
- **Frontend fix:** Added `safeName()` utility in `formatters.js`. Applied as defense-in-depth across: DashboardPage, AdminAgenciesPage (+ Dialog moved out of TableRow), AdminAllUsersPage, AdminAgencyContractsPage, AdminAgencyModulesPage, AdminAgencyUsersPage, AdminHotelsPage.
- **Status:** FIXED & TESTED — both `/app` (dashboard) and `/app/admin/agencies` verified with zero console errors.
