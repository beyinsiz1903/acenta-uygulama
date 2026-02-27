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
  - Simple form: Hotel + Sheet ID + tabs
  - Route: `/app/agency/sheets`
  - Backend: `/api/agency/sheets/*` endpoints
  - **NEW (Feb 27):** Manual sync trigger endpoint: `POST /api/agency/sheets/sync/{connection_id}`
  - **NEW (Feb 27):** Sync status display with SyncStatusBadge component
  - **NEW (Feb 27):** Error detail display when sync fails
  - **NEW (Feb 27):** Sync button (Zap icon) per connection

### Bug Fixes (Feb 2026)
- Fixed agency dropdown empty in admin sheet connections form
- Fixed CI/CD ruff linting failure in agency_sheets.py (unused imports)

## Key Files
- `backend/app/routers/agency_sheets.py` - Agency self-service sheet endpoints (incl. sync)
- `backend/app/routers/admin_sheets.py` - Admin portfolio sync endpoints
- `backend/app/services/sheets_provider.py` - Google Sheets API client
- `backend/app/services/hotel_portfolio_sync_service.py` - Sync engine
- `frontend/src/pages/AgencySheetConnectionsPage.jsx` - Agency sheet management UI
- `frontend/src/pages/admin/AdminPortfolioSyncPage.jsx` - Admin portfolio sync dashboard

## Key API Endpoints
- `POST /api/agency/sheets/connect` - Create agency sheet connection
- `GET /api/agency/sheets/connections` - List agency connections
- `GET /api/agency/sheets/hotels` - List available hotels for agency
- `POST /api/agency/sheets/sync/{connection_id}` - Trigger manual sync
- `DELETE /api/agency/sheets/connections/{connection_id}` - Delete connection
- `GET /api/admin/sheets/config` - Google Sheets config status
- `POST /api/admin/sheets/connect` - Admin create connection
- `POST /api/admin/sheets/sync/{hotel_id}` - Admin trigger sync

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
- P3: Root directory test file cleanup (move to backend/tests)
