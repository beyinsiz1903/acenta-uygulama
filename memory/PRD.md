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
10. **Reservation Write-Back**: Quick reservation from calendar → DB + Google Sheet + allotment management

## Tech Stack
- **Backend**: FastAPI, Motor (async MongoDB), passlib, JWT auth
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
- [x] Hotel status correctly shows "Satışa Açık"
- [x] **Inventory Calendar View** — 2026-03-10
- [x] **Reservation Write-Back** — 2026-03-10
  - Quick reservation from calendar (POST /api/agency/reservations/quick)
  - List reservations (GET /api/agency/reservations)
  - Cancel reservation with allotment restore (POST /api/agency/reservations/{id}/cancel)
  - Auto-decrement allotment in hotel_inventory_snapshots
  - Write-back job queued to sheet_writeback_queue (for Google Sheet sync)
  - QuickReservationDialog with hotel/room summary, price calculation, form
  - "Rezervasyon Yap" buttons on calendar day detail cards
  - Testing: Backend 100%, Frontend 95% PASS (iteration_55)

## Prioritized Backlog

### P1 (Next Up)
- [ ] User-Based Screen Permissions: Granular permission model per user

### P2
- [ ] Refine Pricing Page (agentis.com.tr inspiration)
- [ ] "Otellerim" screen: Display availability (kontenjan) field
- [ ] Automatic Google Sheets Sync (background scheduler)
- [ ] Process pending write-back queue (scheduler to execute queued sheet writes)

## Key Credentials
- **Superadmin**: admin@acenta.test / admin123
- **Agency Admin**: agent@acenta.test / agent123

## Architecture
```
/app
├── backend/
│   └── app/
│       ├── routers/
│       │   ├── agency.py
│       │   ├── agency_availability.py (tenant_id $in query fix)
│       │   ├── agency_reservations.py (NEW: quick reservation CRUD)
│       │   ├── agency_writeback.py (write-back status/queue)
│       │   ├── agency_booking.py
│       │   └── agency_sheets.py
│       └── services/
│           ├── sheet_writeback_service.py (write-back + allotment mgmt)
│           ├── google_sheets_client.py
│           └── sheets_provider.py
└── frontend/
    └── src/
        ├── components/
        │   ├── HotelInventoryCalendar.jsx (calendar + reserve buttons)
        │   └── QuickReservationDialog.jsx (NEW: reservation form dialog)
        └── pages/
            ├── AgencyHotelDetailPage.jsx (calendar integrated)
            └── AgencyHotelsPage.jsx (Detay & Takvim button)
```

## Key DB Collections
- `hotels`: Hotel definitions
- `hotel_inventory_snapshots`: Sheet-synced inventory (date, room_type, price, allotment, stop_sale)
- `hotel_portfolio_sources`: Google Sheets connection config per hotel
- `reservations`: Quick reservations from calendar (with pnr, idempotency_key)
- `sheet_writeback_queue`: Queued write-back jobs for Google Sheets
- `sheet_writeback_markers`: Idempotency markers for write-back dedup
- `agencies`, `users`, `bookings`, `booking_drafts`
