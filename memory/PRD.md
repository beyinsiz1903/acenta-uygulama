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

### Session Persistence (Completed)
- Access token: 8 hours, Refresh token: 90 days

### CORS Fix (Completed)
- Backend CORS configured for `agency.syroce.com`

### Google Sheets Integration (Feb 2026)
- Admin Panel: Portfolio sync dashboard, hotel-level + agency-level connections
- Agency Portal: Self-service sheet connection management
  - Route: `/app/agency/sheets`, Backend: `/api/agency/sheets/*`
  - Manual sync, sync status badge, error details

### Root Directory Cleanup (Feb 27, 2026)
- Removed ~220+ stale test/debug files

### Seed Refactoring (Feb 27, 2026)
- Extracted indexes from seed.py → `app/indexes/seed_indexes.py`
- seed.py: data-only, modular (782 lines)
- Orphan org cleaned up (slug=default assigned to active org)

### Production DB Permissions (Feb 27, 2026)
- `seed_indexes.py`: `_safe_create` defensive pattern (OperationFailure handling)
- Moved ~120 lines of inline index creation from server.py → seed_indexes.py
- server.py reduced from 899 → 779 lines
- All index files now handle production MongoDB without createIndex permission

### Cache Warmup Expansion (Feb 27, 2026)
- Expanded from 3 to 7 data types:
  - Existing: tenant features, CMS nav, campaigns
  - NEW: agencies list, hotels list, FX rates, pricing rules
- All with appropriate TTLs (300s-600s)

## Key Files
- `backend/app/indexes/seed_indexes.py` - All indexes (defensive _safe_create)
- `backend/app/seed.py` - Data-only seeding
- `backend/app/services/cache_warmup.py` - Expanded cache warmup
- `backend/server.py` - Streamlined startup

## Credentials
| Portal | Email | Password | Role |
|--------|-------|----------|------|
| Admin | admin@acenta.test | admin123 | Super Admin |
| Agency | agent@acenta.test | agent123 | Agency Admin |

## Backlog
- P1: Call ensure_seed_data() on startup + create hotels/links for existing org
- P1: Google Sheets sync testing (requires actual Service Account JSON)
- P2: Apple Watch UI
