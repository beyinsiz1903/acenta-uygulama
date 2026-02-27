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
- Screenshots, store metadata, privacy policy, app icon

### Session Persistence (Completed)
- Access token: 8h, Refresh token: 90d

### CORS Fix (Completed)
- Backend CORS configured for `agency.syroce.com`

### Google Sheets Integration (Feb 2026)
- Admin + Agency portal sheet connections
- Manual sync, sync status badges, error details

### Infrastructure Improvements (Feb 27, 2026)
- **Root cleanup:** ~220+ stale files removed
- **Seed refactoring:** indexes → seed_indexes.py, data → seed.py
- **Orphan org cleanup:** slug=default on active org
- **Production DB permissions:** _safe_create defensive pattern
- **Cache warmup expansion:** +agencies, hotels, FX rates, pricing rules
- **Seed on startup:** ensure_seed_data() called in server.py lifespan
  - Creates 3 demo hotels (Istanbul, Antalya, Izmir)
  - Creates 2+ agencies with hotel links
  - Creates rooms, rate plans, inventory, users, finance accounts
  - Fully idempotent — safe to run repeatedly

## Key Files
- `backend/app/indexes/seed_indexes.py` - All indexes (defensive _safe_create)
- `backend/app/seed.py` - Data-only seeding (called on startup)
- `backend/app/services/cache_warmup.py` - Expanded cache warmup
- `backend/server.py` - Streamlined startup with seed + indexes

## Credentials
| Portal | Email | Password | Role |
|--------|-------|----------|------|
| Admin | admin@acenta.test | admin123 | Super Admin |
| Agency | agent@acenta.test | agent123 | Agency Admin |

## Backlog
- P1: Google Sheets sync testing (requires actual Service Account JSON)
- P2: Apple Watch UI
