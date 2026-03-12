# Syroce - Hotel PMS (Property Management System) PRD

## Original Problem Statement
Syroce is a Travel Agency Operating System that pivoted to focus on building a **Property Management System (PMS)** for hotels, based on agency user feedback.

## Core Requirements
1. **Hotel PMS Focus**: Application functions as a PMS for agency hotel operations
2. **Room Management**: CRUD for hotel rooms
3. **Operational Lists**: Arrivals, in-house, departures
4. **Stayover Report**: Dedicated stayover list with count and guest details
5. **Reservation Enrichment**: Flight and tour details in reservations
6. **Accounting & Invoicing**: Payments, cari hesap, invoice management with KDV
7. **Flight API Integration**: Automatic flight data lookup via AviationStack API

## Tech Stack
- **Backend**: FastAPI, Motor (async MongoDB), Pydantic, passlib, httpx
- **Frontend**: React, React Router, Tailwind CSS, Shadcn/UI, Axios, Sonner
- **Database**: MongoDB (MongoDB Atlas in production)
- **Auth**: Cookie-based with httpOnly cookies, JWT
- **External APIs**: AviationStack (flight lookup)

## Architecture
```
/app
├── backend/app/routers/
│   ├── agency_pms.py              # PMS operations + flight lookup
│   └── agency_pms_accounting.py   # Accounting & invoicing
├── frontend/src/pages/
│   ├── PMSDashboardPage.jsx       # PMS dashboard with flight auto-fill
│   ├── PMSRoomsPage.jsx           # Room management
│   ├── PMSAccountingPage.jsx      # Accounting
│   └── PMSInvoicesPage.jsx        # Invoice management
```

## Key DB Collections
- **reservations**: Guest reservations with PMS status, flight info, tour info
- **pms_rooms**: Hotel room inventory
- **pms_transactions**: Charges and payments (folio transactions)
- **pms_invoices**: Generated invoices

## API Endpoints
### PMS Operations
- `GET /api/agency/pms/dashboard` - Dashboard summary
- `GET /api/agency/pms/arrivals` - Today's arrivals
- `GET /api/agency/pms/in-house` - In-house guests
- `GET /api/agency/pms/stayovers` - Stayover guests
- `GET /api/agency/pms/departures` - Today's departures
- `GET/POST/PUT/DELETE /api/agency/pms/rooms` - Room CRUD
- `POST /api/agency/pms/reservations/{id}/check-in` - Check in
- `POST /api/agency/pms/reservations/{id}/check-out` - Check out

### Flight Integration (NEW - 2026-03-11)
- `GET /api/agency/pms/flights/lookup?flight_no=TK1234&flight_date=2026-03-11` - Lookup flight info from AviationStack
- `POST /api/agency/pms/reservations/{id}/auto-flight` - Auto-fill reservation flight info from API

### Accounting & Invoicing
- `GET /api/agency/pms/accounting/summary` - Financial summary
- `GET /api/agency/pms/accounting/folios` - List folios
- `POST /api/agency/pms/accounting/folios/{id}/charge` - Post charge
- `POST /api/agency/pms/accounting/folios/{id}/payment` - Post payment
- `GET/POST /api/agency/pms/accounting/invoices` - Invoice CRUD

## Completed Features
- [x] PMS Dashboard (stats, arrivals/in-house/departures/stayovers/all tabs)
- [x] Room Management (CRUD, floor grouping, status management)
- [x] Check-in / Check-out flow
- [x] Reservation enrichment (flight info, tour info)
- [x] Hotel selector for multi-hotel agencies
- [x] Accounting Module (folios, charges, payments, balance tracking)
- [x] Invoice Management (create, issue, mark paid, cancel, KDV)
- [x] Stayover (Konaklama) list (2026-03-11)
- [x] Flight API Integration - AviationStack (2026-03-11)
  - Backend: Flight lookup endpoint + auto-fill endpoint
  - Frontend: "Otomatik Doldur" buttons in reservation detail edit mode
  - Flight status display in view mode
  - Graceful error handling when API key not configured

## Enterprise Audit (February 2026)
- Full 12-part audit completed at `/app/ENTERPRISE_AUDIT_REPORT.md`
- Overall Maturity: 5.5/10, Security: 6.5/10, Architecture: 5/10, Scalability: 3/10
- Recommended: Modular monolith approach, 6-phase transformation roadmap

## Remaining Backlog
### P0 - AviationStack API Key Configuration
- User needs to obtain and configure AVIATIONSTACK_API_KEY in backend/.env
- Free plan available at https://aviationstack.com/signup/free

### P1 - Agency API Key Management UI
- Agency admins should be able to enter/save their AviationStack API key via UI
- Backend should read key from DB instead of env variable

### P2 - Agency Subscription Management
- Subscription duration and access control based on expiry

### P3 - Direct Password Management
- Superadmin can create users and set passwords directly

### P4 - Refactoring
- Centralize data normalization in agency_hotels.py
- Decompose AgencyHotelDetailPage.jsx
- Split router_registry.py into domain-grouped registries
- Split App.js routes into domain files

### P5 - Infrastructure & Testing
- CI/CD pipeline setup
- Automated test coverage for booking lifecycle
- Redis caching layer
- MongoDB schema validation

## Environment Variables
- `AVIATIONSTACK_API_KEY` - AviationStack API key for flight lookup (backend/.env)

## Test Credentials
- **Agency Admin**: agency1@demo.test / agency123
- **Superadmin**: agent@acenta.test / agent123
