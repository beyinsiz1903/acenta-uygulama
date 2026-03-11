# PRD — Syroce Travel Agency Operating System

## Original Problem Statement
The user is building a "Travel Agency Operating System" named "Syroce". It manages agencies, hotels, reservations, pricing, and integrations (Google Sheets for inventory). Recent user feedback from an agency partner requested PMS (Property Management System) functionality to manage hotel operations like a mini-PMS: arrival/in-house/departure lists, room management, guest check-in/check-out, flight/tour info tracking, and future financial (cari hesap/fatura) capabilities.

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
13. **PMS (Property Management System)**: Arrival/In-house/Departure/Stayover operational lists, room management, check-in/check-out, flight/tour info on reservations
14. **Cari Hesap & Fatura**: Agency-level current account, balance tracking, invoice generation (UPCOMING)
15. **Flight API Integration**: Automatic flight info lookup from flight number (UPCOMING)

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
- [x] **Automatic Google Sheets Sync** — 2026-03-11
- [x] **Multi-Agency Google Sheets Credentials** — 2026-03-11
- [x] **Granular User Permissions** — 2026-03-11
- [x] **Permission Templates** — 2026-03-11
- [x] **Refined Pricing Page** — 2026-03-12
- [x] **Otellerim Kontenjan Gorünümü** — 2026-03-12
- [x] **PMS Dashboard** — 2026-03-11
  - Stat cards: Girisler (arrivals), Otelde (in-house), Cikislar (departures), Doluluk (occupancy)
  - Hotel selector dropdown for filtering
  - Tabs: Girisler, Otelde, Cikislar, Tum Rezervasyonlar
  - Check-in / Check-out buttons on reservation rows
  - Reservation detail modal with guest, flight, tour info
  - Edit mode for updating flight/tour/guest details
- [x] **Room Management** — 2026-03-11
  - Rooms grouped by floor in a visual grid
  - CRUD: Create, Edit, Delete rooms
  - Room status tracking (available, occupied, cleaning, maintenance)
  - Hotel and status filter dropdowns
- [x] **PMS Navigation Integration** — 2026-03-11
  - PMS Paneli and Oda Yonetimi added to sidebar under PMS section
  - Module aliases added (pms_paneli, oda_yonetimi)
  - Agency allowed_modules updated to include PMS

## Prioritized Backlog

### P0
- [ ] Cari Hesap (Current Account) system: agency-level balance tracking, payment recording, invoice generation
- [ ] Flight API integration: auto-lookup flight info from flight number

### P1
- [ ] Agency Subscription Management: expiry warnings, access blocking
- [ ] Direct Password Management for superadmin

### P2
- [ ] Process pending write-back queue (improve retry/monitoring)
- [ ] Refactoring: agency_hotels.py data normalization, AgencyHotelDetailPage.jsx component breakdown

## Key Credentials
- **Superadmin**: admin@acenta.test / admin123
- **Agency Admin**: agent@acenta.test / agent123

## Architecture
```
/app
├── backend/
│   └── app/
│       ├── bootstrap/
│       │   ├── scheduler_app.py
│       │   └── router_registry.py
│       ├── routers/
│       │   ├── agency.py
│       │   ├── agency_availability.py
│       │   ├── agency_reservations.py
│       │   ├── agency_pms.py (NEW - PMS endpoints)
│       │   ├── agency_writeback.py
│       │   ├── agency_booking.py
│       │   ├── agency_sheets.py
│       │   ├── agency_profile.py
│       │   └── admin_agency_users.py
│       ├── auth.py
│       ├── schemas/main.py
│       └── services/
│           ├── agency_module_service.py (UPDATED: PMS aliases)
│           ├── hotel_portfolio_sync_service.py
│           ├── sheet_writeback_service.py
│           └── sheets_provider.py
└── frontend/
    └── src/
        ├── components/
        │   ├── AppShell.jsx
        │   ├── NewSidebar.jsx
        │   └── ...
        ├── lib/
        │   └── appNavigation.js (UPDATED: PMS nav items)
        ├── nav/
        │   └── agencyNav.js (UPDATED: PMS section)
        └── pages/
            ├── PMSDashboardPage.jsx (NEW)
            ├── PMSRoomsPage.jsx (NEW)
            └── ...
```

## Key DB Collections
- `hotels`, `hotel_inventory_snapshots`, `hotel_portfolio_sources`
- `reservations` (enhanced with pms_status, flight_info, tour_info, room_number)
- `pms_rooms` (NEW - room management)
- `sheet_writeback_queue`, `sheet_writeback_markers`
- `sheet_sync_runs`, `platform_config`
- `agencies` (with allowed_modules including pms_paneli, oda_yonetimi)
- `users` (with allowed_screens field)

## Key API Endpoints
- `GET /api/agency/pms/dashboard`: PMS dashboard with stats
- `GET /api/agency/pms/arrivals`: Today's arrivals
- `GET /api/agency/pms/in-house`: In-house guests
- `GET /api/agency/pms/departures`: Today's departures
- `GET /api/agency/pms/reservations`: Filtered reservations list
- `GET /api/agency/pms/reservations/{id}`: Single reservation detail
- `PUT /api/agency/pms/reservations/{id}`: Update reservation (flight/tour/room)
- `POST /api/agency/pms/reservations/{id}/check-in`: Check in guest
- `POST /api/agency/pms/reservations/{id}/check-out`: Check out guest
- `POST /api/agency/pms/reservations/{id}/assign-room`: Assign room
- `GET /api/agency/pms/rooms`: List rooms
- `POST /api/agency/pms/rooms`: Create room
- `PUT /api/agency/pms/rooms/{id}`: Update room
- `DELETE /api/agency/pms/rooms/{id}`: Delete room
- `GET /api/agency/hotels`: Returns hotel list with allocation_available field
- `GET /api/agency/availability/{hotel_id}`: Inventory data for calendar
- `POST /api/agency/reservations/quick`: Creates reservation
