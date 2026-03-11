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
- [x] **Automatic Google Sheets Sync** — 2026-03-11
- [x] **Multi-Agency Google Sheets Credentials** — 2026-03-11
- [x] **Granular User Permissions** — 2026-03-11
- [x] **Permission Templates** — 2026-03-11
- [x] **Refined Pricing Page** — 2026-03-12
  - PublicNavbar component with logo, nav links (Ana Sayfa, Fiyatlar, Demo), and CTAs
  - Promotional banner ("Süre Sınırlı Teklif: 2 yıllık alımlarda +1 yıl bizden!")
  - Trust bar with 4 items (SSL, 7/24 altyapı, Destek, Kurulum)
  - 4 pricing cards with old price strikethrough, expandable detailed features
  - Billing cycle toggle (Aylık/Yıllık) defaulting to Yıllık
  - Comparison table, FAQ accordion
  - Contact section with phone, email, hours
  - Footer with copyright and links
- [x] **Otellerim Kontenjan Görünümü** — 2026-03-12
  - All hotel cards now show "Kontenjan" badge with color-coding
  - Green (>5), Amber (1-5), Red (0), Gray (no data)
  - Sheet sync details (date, last sync) shown inline

## Prioritized Backlog

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
│       │   └── scheduler_app.py
│       ├── routers/
│       │   ├── agency.py (hotels endpoint with allocation_available)
│       │   ├── agency_availability.py
│       │   ├── agency_reservations.py
│       │   ├── agency_writeback.py
│       │   ├── agency_booking.py
│       │   ├── agency_sheets.py
│       │   └── admin_agency_users.py
│       ├── auth.py
│       ├── schemas/main.py
│       └── services/
│           ├── hotel_portfolio_sync_service.py
│           ├── sheet_writeback_service.py
│           ├── google_sheets_client.py
│           └── sheets_provider.py
└── frontend/
    └── src/
        ├── components/
        │   ├── AppShell.jsx
        │   ├── HotelInventoryCalendar.jsx
        │   ├── QuickReservationDialog.jsx
        │   └── marketing/
        │       ├── PublicNavbar.jsx (NEW)
        │       ├── SyrocePricingCard.jsx (UPDATED: expandable details, old price)
        │       ├── SyrocePricingComparison.jsx
        │       └── SyroceFaqSection.jsx
        ├── lib/
        │   └── syrocePricingContent.js (UPDATED: detailedFeatures, oldPrice)
        └── pages/
            ├── AgencyHotelsPage.jsx (UPDATED: kontenjan display)
            ├── AgencySheetConnectionsPage.jsx
            ├── AgencyHotelDetailPage.jsx
            └── public/
                └── PricingPage.jsx (UPDATED: full refinement)
```

## Key DB Collections
- `hotels`, `hotel_inventory_snapshots`, `hotel_portfolio_sources`
- `reservations`, `sheet_writeback_queue`, `sheet_writeback_markers`
- `sheet_sync_runs`, `platform_config`
- `agencies`, `users` (with allowed_screens field), `bookings`, `booking_drafts`

## Key API Endpoints
- `GET /api/agency/hotels`: Returns hotel list with allocation_available field
- `GET /api/agency/availability/{hotel_id}`: Inventory data for calendar
- `POST /api/agency/reservations/quick`: Creates reservation
- `POST /api/agency/sheets/sync/{connection_id}`: Manual sync trigger
- `GET /api/agency/sheets/sync-status`: Auto-sync overview
- `PUT /api/admin/agency-users/{user_id}/permissions`: User permissions
- `GET /api/admin/permissions/screens`: Available screen definitions
- `GET /api/admin/permissions/templates`: Permission templates
