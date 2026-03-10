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

### Completed (Verified) ✅
- [x] Agency CRUD + subscription management
- [x] User management with direct password setting
- [x] JWT-based authentication
- [x] Change Password (agency users) — Verified
- [x] Agency Module saving — Verified
- [x] Billing link hidden from agency users — Verified
- [x] Google Sheets Service Account integration — **Activated 2026-03-11**
- [x] Google Sheets sync: 5 rows synced, 489ms, "Rezervasyonlar" writeback tab created
- [x] Stop-sell date filtering fix — 2026-03-11
- [x] Hotel detail page (AgencyHotelDetailPage) crash fix — 2026-03-11
- [x] Turkish character encoding fix — 2026-03-11
- [x] Hotel status correctly shows "Satışa Açık" when no active stop-sell rules

### In Progress
- None

### Blocked
- None (Google Sheets was unblocked on 2026-03-11)

## Prioritized Backlog

### P1 (Next Up)
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
- **Agency Admin**: agency1@demo.test / Agency12345!
- **Google Service Account**: syroce-sheets@syroce-sheets.iam.gserviceaccount.com

## Architecture
```
/app
├── backend/
│   └── app/
│       ├── main.py
│       ├── routers/
│       │   ├── admin_agencies.py
│       │   ├── admin_sheets.py
│       │   ├── agency.py (stop-sell date filter fix)
│       │   ├── agency_users.py
│       │   └── settings.py
│       └── services/
│           ├── google_sheets_client.py
│           ├── hotel_portfolio_sync_service.py
│           └── sheets_provider.py
└── frontend/
    └── src/
        ├── pages/
        │   ├── AgencyHotelDetailPage.jsx (TDZ fix, field mapping fix)
        │   ├── AgencyHotelsPage.jsx
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
