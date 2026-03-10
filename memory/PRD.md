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
9. **Inventory Calendar View**: Visual calendar showing room type, price, and allotment per date from Google Sheets data

## User Personas
- **Superadmin**: Platform owner, manages agencies, hotels, pricing
- **Agency Admin**: Manages their agency's hotels, reservations, users
- **Agency User**: Views assigned hotels, creates reservations

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
- [x] **Inventory Calendar View** — 2026-03-10 ✅
  - Visual monthly calendar on hotel detail page
  - Color-coded cells: green (available), amber (low), orange (none), red (stop-sale)
  - Per-day: min price (TL) + total room count
  - Click-to-expand day detail: room type, price, allotment per room
  - Room type filter dropdown
  - Month navigation (prev/next)
  - Stats bar: total records, room types, E-Tablo Bağlı badge, last sync time
  - Backend fix: tenant_id $in query for org_id+tenant_id compatibility
  - 270 demo inventory snapshots seeded (45 days × 3 room types × 2 hotels)
  - Testing: Backend 11/11 PASS, Frontend 100% PASS (iteration_54)

### In Progress
- None

### Blocked
- None

## Prioritized Backlog

### P1 (Next Up)
- [ ] Reservation Write-Back: Write new reservations from app back to Google Sheet "Rezervasyonlar" tab
- [ ] User-Based Screen Permissions: Granular permission model per user
- [ ] Reservation Limits: Backend enforcement per pricing plan

### P2
- [ ] Refine Pricing Page (agentis.com.tr inspiration)
- [ ] "Otellerim" screen: Display availability (kontenjan) field
- [ ] Automatic Google Sheets Sync (background scheduler)
- [ ] Payment Failure Lifecycle
- [ ] Landing Funnel Optimization

## Key Credentials
- **Superadmin**: admin@acenta.test / admin123
- **Agency Admin**: agent@acenta.test / agent123
- **Google Service Account**: syroce-sheets@syroce-sheets.iam.gserviceaccount.com

## Architecture
```
/app
├── backend/
│   └── app/
│       ├── main.py
│       ├── routers/
│       │   ├── agency.py (hotel list with sheet sync data)
│       │   ├── agency_availability.py (FIXED: tenant_id $in query for calendar)
│       │   ├── admin_sheets.py
│       │   ├── agency_sheets.py
│       │   ├── agency_users.py
│       │   └── settings.py
│       └── services/
│           ├── google_sheets_client.py
│           ├── hotel_portfolio_sync_service.py
│           └── sheets_provider.py
└── frontend/
    └── src/
        ├── components/
        │   └── HotelInventoryCalendar.jsx (NEW: calendar view component)
        ├── pages/
        │   ├── AgencyHotelDetailPage.jsx (calendar integrated)
        │   ├── AgencyHotelsPage.jsx (Detay & Takvim button)
        │   └── agency-admin/SettingsPage.jsx
        ├── layouts/AgencyAdminLayout.jsx
        └── lib/sidebar-links.js
```

## Key DB Collections
- `hotels`: Hotel definitions
- `hotel_inventory_snapshots`: Sheet-synced inventory (date, room_type, price, allotment, stop_sale)
- `hotel_portfolio_sources`: Google Sheets connection config per hotel
- `stop_sell_rules`: Date-ranged stop-sell rules per hotel/room
- `agencies`: Agency definitions with modules
- `users`: User accounts with hashed passwords
- `platform_config`: Google Service Account JSON storage
