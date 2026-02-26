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

### Google Sheets Integration
- **Admin Panel:** Portfolio sync dashboard, hotel-level connections, agency-level connections
- **Agency Portal (NEW - Feb 2026):** Self-service sheet connection management
  - Agency auto-detected from logged-in user (no dropdown needed)
  - Simple form: Hotel + Sheet ID + tabs
  - Route: `/app/agency/sheets`
  - Backend: `/api/agency/sheets/*` endpoints

### Bug Fixes (Feb 2026)
- Fixed agency dropdown empty in admin sheet connections form (fallback to all active agencies when no hotel-specific links exist)

## Key Files
- `backend/app/routers/agency_sheets.py` - Agency self-service sheet endpoints
- `backend/app/routers/admin_sheets.py` - Admin portfolio sync endpoints
- `backend/app/services/sheets_provider.py` - Google Sheets API client
- `frontend/src/pages/AgencySheetConnectionsPage.jsx` - Agency sheet management UI
- `frontend/src/pages/admin/AdminPortfolioSyncPage.jsx` - Admin portfolio sync dashboard

## Credentials
| Portal | Email | Password | Role |
|--------|-------|----------|------|
| Admin | admin@acenta.test | admin123 | Super Admin |
| Agency | agent@acenta.test | agent123 | Agency Admin |

## Backlog
- P1: Database seeding improvements
- P2: Production DB permissions (createIndex)
- P2: Cache warm-up expansion
- P2: Apple Watch UI
