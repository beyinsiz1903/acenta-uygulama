# PRD — Syroce Travel Agency Operating System

## Original Problem Statement
The user is building a "Travel Agency Operating System" named "Syroce". It manages agencies, hotels, reservations, pricing, and integrations (Google Sheets for inventory).

## Core Requirements
1. Agency Subscription Management with expiry warnings
2. Direct Password Management (superadmin creates users)
3. Public Pricing Page (inspired by agentis.com.tr)
4. Google Sheets Integration for hotel reservations/availability
5. Settings Page for agency users
6. Change Password functionality
7. Granular User Permissions (screen-level access control)
8. UI/UX: Billing screen hidden from agency users
9. **Inventory Calendar View**: Visual calendar showing room type, price, and allotment per date
10. **Reservation Write-Back**: Quick reservation from calendar -> DB + Google Sheet + allotment management
11. **Automatic Google Sheets Sync**: Background scheduler for periodic sync + write-back processing
12. **Multi-Agency Google Sheets Credentials**: Each agency can use their own Google Service Account

## Tech Stack
- **Backend**: FastAPI, Motor (async MongoDB), passlib, JWT auth, APScheduler
- **Frontend**: React, React Router, Tailwind CSS, Shadcn/UI, Axios, Sonner
- **Database**: MongoDB Atlas
- **Integrations**: Google Sheets API, Google Drive API

## What's Been Implemented

### Completed (Verified)
- [x] Agency CRUD + subscription management
- [x] User management with direct password setting
- [x] JWT-based authentication
- [x] Change Password (agency users)
- [x] Agency Module saving
- [x] Billing link hidden from agency users
- [x] Google Sheets Service Account integration
- [x] Google Sheets sync: availability data read from sheets
- [x] Stop-sell date filtering fix
- [x] Hotel detail page crash fix
- [x] Turkish character encoding fix
- [x] Hotel status correctly shows "Satisa Acik"
- [x] **Inventory Calendar View** — 2026-03-10
- [x] **Reservation Write-Back** — 2026-03-10
  - Quick reservation from calendar (POST /api/agency/reservations/quick)
  - List reservations (GET /api/agency/reservations)
  - Cancel reservation with allotment restore (POST /api/agency/reservations/{id}/cancel)
  - Auto-decrement allotment in hotel_inventory_snapshots
  - Write-back job queued to sheet_writeback_queue (for Google Sheet sync)
  - QuickReservationDialog with hotel/room summary, price calculation, form
- [x] **Automatic Google Sheets Sync** — 2026-03-11
  - Background scheduler running via APScheduler (backend-scheduler process)
  - Portfolio sync every 5 minutes (configurable per connection)
  - Write-back processing every 30 seconds
  - API: GET /api/agency/sheets/sync-status (sync overview)
  - API: GET /api/agency/sheets/sync-history (paginated sync runs)
  - API: PATCH /api/agency/sheets/connections/{id}/settings (toggle sync, change interval)
  - Frontend: Auto-sync toggle and interval selector per connection
  - Frontend: Sync status overview cards
  - Frontend: Expandable sync history panel
- [x] **Multi-Agency Google Sheets Credentials** — 2026-03-11
  - API: POST /api/agency/sheets/credentials (save agency's own service account)
  - API: GET /api/agency/sheets/credentials/status (check credential source)
  - API: DELETE /api/agency/sheets/credentials (remove, fallback to global)
  - Frontend: Credentials management section with active source indicator
  - Frontend: JSON textarea form for pasting Service Account credentials
  - Validation: JSON format, required fields (client_email, private_key)
  - In-memory caching via sheets_provider.set_db_config()
  - Persistent storage in platform_config collection

## Prioritized Backlog

### P0 (Next Up)
- [ ] User-Based Screen Permissions: Granular permission model per user

### P1
- [ ] Refine Pricing Page (agentis.com.tr inspiration)
- [ ] "Otellerim" screen: Display availability (kontenjan) field

### P2
- [ ] Process pending write-back queue (improve retry/monitoring)

## Key Credentials
- **Superadmin**: admin@acenta.test / admin123
- **Agency Admin**: agent@acenta.test / agent123

## Architecture
```
/app
├── backend/
│   └── app/
│       ├── bootstrap/
│       │   └── scheduler_app.py (APScheduler: portfolio sync, writeback, reports, ops)
│       ├── routers/
│       │   ├── agency.py
│       │   ├── agency_availability.py
│       │   ├── agency_reservations.py
│       │   ├── agency_writeback.py
│       │   ├── agency_booking.py
│       │   └── agency_sheets.py (UPDATED: credentials CRUD, sync-status, sync-history, settings)
│       └── services/
│           ├── hotel_portfolio_sync_service.py (full sync engine)
│           ├── sheet_writeback_service.py (write-back + allotment)
│           ├── google_sheets_client.py
│           └── sheets_provider.py (tenant-based credential caching)
└── frontend/
    └── src/
        ├── components/
        │   ├── HotelInventoryCalendar.jsx
        │   └── QuickReservationDialog.jsx
        ├── nav/
        │   └── agencyNav.js (UPDATED: Sheet Baglantilari link added)
        └── pages/
            ├── AgencySheetConnectionsPage.jsx (REWRITTEN: credentials, sync status/history, settings)
            └── AgencyHotelDetailPage.jsx
```

## Key DB Collections
- `hotels`: Hotel definitions
- `hotel_inventory_snapshots`: Sheet-synced inventory (date, room_type, price, allotment, stop_sale)
- `hotel_portfolio_sources`: Google Sheets connection config per hotel (with sync_enabled, sync_interval_minutes)
- `reservations`: Quick reservations from calendar (with pnr, idempotency_key)
- `sheet_writeback_queue`: Queued write-back jobs for Google Sheets
- `sheet_writeback_markers`: Idempotency markers for write-back dedup
- `sheet_sync_runs`: Sync run history (status, rows_read, upserted, duration_ms)
- `platform_config`: Agency-specific Google credentials (config_key: google_service_account_agency_{agency_id})
- `agencies`, `users`, `bookings`, `booking_drafts`

## Key API Endpoints
- `GET /api/agency/availability/{hotel_id}`: Fetches aggregated inventory data for calendar
- `POST /api/agency/reservations/quick`: Creates reservation, decrements allotment, triggers write-back
- `POST /api/agency/sheets/sync/{connection_id}`: Triggers manual sync
- `GET /api/agency/sheets/sync-status`: Auto-sync overview
- `GET /api/agency/sheets/sync-history`: Sync run history
- `PATCH /api/agency/sheets/connections/{id}/settings`: Update sync settings
- `POST /api/agency/sheets/credentials`: Save agency Google credentials
- `GET /api/agency/sheets/credentials/status`: Check credential source
- `DELETE /api/agency/sheets/credentials`: Remove agency credentials
