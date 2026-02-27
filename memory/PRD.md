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

### App Store Preparation (Completed)
- Screenshots for iPhone, iPad, Apple Watch
- Store metadata (Turkish) for App Store & Google Play
- Privacy Policy and Terms of Service pages

### Session Persistence (Completed)
- Access token: 8 hours, Refresh token: 90 days

### CORS Fix (Completed)
- Backend CORS configured for `agency.syroce.com`

### Google Sheets Integration (Feb 2026)
- Admin Panel: Portfolio sync dashboard, hotel-level + agency-level connections
- Agency Portal: Self-service sheet connection management
  - Route: `/app/agency/sheets`, Backend: `/api/agency/sheets/*`
  - Manual sync trigger: `POST /api/agency/sheets/sync/{connection_id}`
  - Sync status display with SyncStatusBadge + error details

### Root Directory Cleanup (Feb 27, 2026)
- Removed ~220+ stale test/debug files from root directory

### Seed Refactoring (Feb 27, 2026)
- **Extracted ~80 index definitions** from `seed.py` into `app/indexes/seed_indexes.py`
- **`seed_indexes.py`** (241 lines): All collection indexes, called at startup via server.py lifespan
- **`seed.py`** (782 lines): Only data seeding, modular with numbered sections
- Original `seed.py` was 1167 lines mixing indexes + data in one function

## Key Files
- `backend/app/indexes/seed_indexes.py` - **NEW** Extracted seed indexes
- `backend/app/seed.py` - Refactored data-only seeding
- `backend/server.py` - Calls seed_indexes at startup
- `backend/app/routers/agency_sheets.py` - Agency sheet endpoints
- `backend/app/routers/admin_sheets.py` - Admin sheet endpoints
- `frontend/src/pages/AgencySheetConnectionsPage.jsx` - Agency sheet UI
- `frontend/src/pages/admin/AdminPortfolioSyncPage.jsx` - Admin sync dashboard

## Credentials
| Portal | Email | Password | Role |
|--------|-------|----------|------|
| Admin | admin@acenta.test | admin123 | Super Admin |
| Agency | agent@acenta.test | agent123 | Agency Admin |

## Backlog
- P1: Call ensure_seed_data() on startup + create hotels/links for existing org
- P1: Google Sheets sync testing (requires actual Service Account JSON)
- P2: Production DB permissions (createIndex)
- P2: Cache warm-up expansion
- P2: Apple Watch UI
- P3: Orphan org cleanup ("Varsayilan Acenta" with slug=default)
