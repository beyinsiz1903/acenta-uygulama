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
- App icon and feature graphic

### Session Persistence (Completed)
- Access token: 8 hours
- Refresh token: 90 days

### CORS Fix (Completed - Pending Production Deploy)
- Backend CORS configured for `agency.syroce.com`

### Google Sheets Integration (Feb 2026)
- **Admin Panel:** Portfolio sync dashboard, hotel-level connections, agency-level connections
- **Agency Portal:** Self-service sheet connection management
  - Agency auto-detected from logged-in user (no dropdown needed)
  - Route: `/app/agency/sheets`
  - Backend: `/api/agency/sheets/*` endpoints
  - Manual sync trigger: `POST /api/agency/sheets/sync/{connection_id}`
  - Sync status display with SyncStatusBadge component
  - Error detail display when sync fails

### Bug Fixes (Feb 2026)
- Fixed agency dropdown empty in admin sheet connections form
- Fixed CI/CD ruff linting failure in agency_sheets.py

### Root Directory Cleanup (Feb 27, 2026)
- Removed ~220+ stale test/debug files from root directory
- Removed: `*_test.py`, `debug_*.py`, `test_*.py`, `*_results.json`, `*.sh`, `*.ts`, `*.csv`, `*.html`, `*.png`, empty placeholder files
- Root directory reduced from 230+ items to 20 clean items

## Key Files
- `backend/app/routers/agency_sheets.py` - Agency self-service sheet endpoints (incl. sync)
- `backend/app/routers/admin_sheets.py` - Admin portfolio sync endpoints
- `backend/app/services/sheets_provider.py` - Google Sheets API client
- `backend/app/services/hotel_portfolio_sync_service.py` - Sync engine
- `frontend/src/pages/AgencySheetConnectionsPage.jsx` - Agency sheet management UI
- `frontend/src/pages/admin/AdminPortfolioSyncPage.jsx` - Admin portfolio sync dashboard

## Credentials
| Portal | Email | Password | Role |
|--------|-------|----------|------|
| Admin | admin@acenta.test | admin123 | Super Admin |
| Agency | agent@acenta.test | agent123 | Agency Admin |

## Backlog
- P1: Google Sheets sync error investigation (requires actual Google Sheets config)
- P1: Database seeding improvements
- P2: Production DB permissions (createIndex)
- P2: Cache warm-up expansion
- P2: Apple Watch UI
