# Syroce - Hotel PMS (Property Management System) PRD

## Original Problem Statement
Syroce is a Travel Agency Operating System that pivoted to focus on building a **Property Management System (PMS)** for hotels, based on agency user feedback.

## Core Requirements
1. **Hotel PMS Focus**: Application functions as a PMS for agency hotel operations
2. **Room Management**: CRUD for hotel rooms ✅
3. **Operational Lists**: Arrivals, in-house, departures ✅
4. **Stayover Report**: Count of stayover rooms ✅ (included in dashboard)
5. **Reservation Enrichment**: Flight and tour details in reservations ✅
6. **Accounting & Invoicing**: Payments, cari hesap, invoice management ✅
7. **Automatic Integrations**: Flight API integration (future)

## Tech Stack
- **Backend**: FastAPI, Motor (async MongoDB), Pydantic, passlib
- **Frontend**: React, React Router, Tailwind CSS, Shadcn/UI, Axios, Sonner
- **Database**: MongoDB (MongoDB Atlas in production)
- **Auth**: Cookie-based with httpOnly cookies, JWT

## Architecture
```
/app
├── backend/app/routers/
│   ├── agency_pms.py              # PMS operations (dashboard, rooms, check-in/out)
│   └── agency_pms_accounting.py   # Accounting & invoicing (folios, charges, payments, invoices)
├── frontend/src/pages/
│   ├── PMSDashboardPage.jsx       # PMS dashboard with stats, tabs, reservation list
│   ├── PMSRoomsPage.jsx           # Room management (CRUD, floor grouping)
│   ├── PMSAccountingPage.jsx      # Accounting (folios, charges, payments)
│   └── PMSInvoicesPage.jsx        # Invoice list and management
├── frontend/src/nav/agencyNav.js  # Agency sidebar navigation
└── frontend/src/lib/appNavigation.js # App-wide navigation config
```

## Key DB Collections
- **reservations**: Guest reservations with PMS status
- **pms_rooms**: Hotel room inventory
- **pms_transactions**: Charges and payments (folio transactions)
- **pms_invoices**: Generated invoices

## API Endpoints
### PMS Operations
- `GET /api/agency/pms/dashboard` — Dashboard summary
- `GET /api/agency/pms/arrivals` — Today's arrivals
- `GET /api/agency/pms/in-house` — In-house guests
- `GET /api/agency/pms/departures` — Today's departures
- `GET/POST/PUT/DELETE /api/agency/pms/rooms` — Room CRUD
- `POST /api/agency/pms/reservations/{id}/check-in` — Check in
- `POST /api/agency/pms/reservations/{id}/check-out` — Check out

### Accounting & Invoicing
- `GET /api/agency/pms/accounting/summary` — Financial summary
- `GET /api/agency/pms/accounting/folios` — List folios (cari hesaplar)
- `GET /api/agency/pms/accounting/folios/{id}` — Folio detail with transactions
- `POST /api/agency/pms/accounting/folios/{id}/charge` — Post charge
- `POST /api/agency/pms/accounting/folios/{id}/payment` — Post payment
- `DELETE /api/agency/pms/accounting/transactions/{id}` — Delete transaction
- `GET/POST /api/agency/pms/accounting/invoices` — Invoice CRUD
- `PUT /api/agency/pms/accounting/invoices/{id}` — Update invoice status

## Completed Features
- [x] PMS Dashboard (stats, arrivals/in-house/departures/all reservations tabs)
- [x] Room Management (CRUD, floor grouping, status management)
- [x] Check-in / Check-out flow
- [x] Reservation enrichment (flight info, tour info)
- [x] Hotel selector for multi-hotel agencies
- [x] Accounting Module (folios, charges, payments, balance tracking)
- [x] Invoice Management (create, issue, mark paid, cancel, with KDV calculation)
- [x] Navigation with PMS section (4 pages)

## Remaining Backlog
### P1 - Stayover List (Separate view)
- Dedicated stayover list/report page beyond dashboard count

### P2 - Flight API Integration
- Automatic flight data enrichment via external API

### P3 - Agency Subscription Management
- Subscription duration and access control based on expiry

### P4 - Direct Password Management
- Superadmin can create users and set passwords directly

### P5 - Refactoring
- Centralize data normalization in agency_hotels.py
- Decompose AgencyHotelDetailPage.jsx

## Test Credentials
- **Agency Admin**: agency1@demo.test / agency123
- **Superadmin**: agent@acenta.test / agent123
