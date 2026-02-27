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
- Production DB permissions (_safe_create)
- Cache warmup expansion (+agencies, hotels, FX, pricing rules)
- Seed on startup with idempotent data creation

### Per-Agency Module Management (Feb 27, 2026)
- **Backend:** GET/PUT `/api/admin/agencies/{id}/modules` — store allowed_modules per agency
- **Backend:** GET `/api/agency/profile` — agency users fetch their allowed modules
- **Admin UI:** `/app/admin/agency-modules` — checkbox grid to configure tabs per agency
- **Sidebar:** "Acente Modulleri" menu item under YONETIM

### Branding Restriction (Feb 27, 2026)
- **Backend:** `can_edit_name` flag in whitelabel-settings response (true only for super_admin)
- **Backend:** company_name update silently ignored for non-super_admin
- **Frontend:** company_name input readonly with message for non-super_admin users

### Super Admin Unified User Management (Feb 27, 2026)
- **Backend:** GET `/api/admin/all-users` — lists all agency users across all agencies with agency_name
- **Frontend:** `/app/admin/all-users` — unified user management page with:
  - Search by email, name, or agency
  - Filter by agency and status (active/disabled)
  - Summary cards (total, active, disabled, agency count)
  - Inline role change (agency_admin/agency_agent)
  - Status toggle (activate/deactivate)
  - Click agency name to navigate to per-agency detail
- **Sidebar:** "Kullanici Yonetimi" link added under YONETIM group

### Dynamic Agency Navigation (Feb 27, 2026)
- **Frontend:** AppShell.jsx now fetches `/api/agency/profile` for agency users
- Sidebar items filtered by `allowed_modules` — only matching `modeKey` items shown
- Empty `allowed_modules` means no restriction (all modules visible)
- Admin users always see full navigation regardless of agency settings

## Key Files
- `backend/app/routers/admin_agency_users.py` - Per-agency user CRUD + all_users_router
- `backend/app/routers/admin_agencies.py` - Agency CRUD + module management
- `backend/app/routers/agency_profile.py` - Agency profile endpoint
- `backend/app/routers/enterprise_whitelabel.py` - Branding with role restriction
- `frontend/src/pages/AdminAllUsersPage.jsx` - Unified user management UI
- `frontend/src/pages/AdminAgencyModulesPage.jsx` - Module config UI
- `frontend/src/pages/AdminBrandingPage.jsx` - Branding with canEditName
- `frontend/src/components/AppShell.jsx` - Sidebar with dynamic agency module filtering

## Credentials
| Portal | Email | Password | Role |
|--------|-------|----------|------|
| Admin | admin@acenta.test | admin123 | Super Admin |
| Agency | agent@acenta.test | agent123 | Agency Admin |

## Backlog
- P2: Production DB permissions (createIndex for production MongoDB user)
- P2: Cache warm-up expansion
- P2: Apple Watch UI
- P2: Google Sheets sync testing (requires Service Account JSON)
