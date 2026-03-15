# Syroce — Travel ERP Platform — PRD

## Product Overview
Syroce is a production-grade Turkish travel ERP platform that manages the full lifecycle of travel agency operations: supplier management, booking engine, pricing engine, revenue/growth engine, invoice/e-document engine, accounting sync, financial operations, and multi-provider accounting architecture.

## Current Platform Layers
1. **Supplier Ecosystem** (Score: 10/10)
2. **Booking Engine** (Score: 9.9/10)
3. **Revenue Engine** (Score: 9.8/10)
4. **Invoice Engine** (Score: 9.8/10)
5. **E-Document Layer** (Score: 9.7/10)
6. **Accounting Sync Layer** (Score: 9.6/10)
7. **Accounting Automation Layer** (Score: 9.7/10)
8. **Reconciliation & Finance Ops Layer** (Score: 9.8/10) — MEGA PROMPT #33
9. **Multi Accounting Provider Architecture** (Score: NEW) — MEGA PROMPT #34
10. **Pilot Agency Real Flow Validation** (Score: NEW) — MEGA PROMPT #35

## Core Requirements

### Authentication
- JWT-based auth with role-based access control
- Roles: super_admin, admin, finance_admin, agency_admin

### Pilot Agency Real Flow Validation (MEGA PROMPT #35) - IMPLEMENTED
- **Pilot Setup Wizard**: 9-step enforced onboarding flow
  - Step 1: Agency Create (name, email, phone, tax_id, mode)
  - Step 2: Supplier Credential (supplier_type, api_key, api_secret, agency_code)
  - Step 3: Accounting Provider Credential (provider_type, company_code, username, password)
  - Step 4: Connection Test (supplier + accounting)
  - Step 5: First Search Test
  - Step 6: First Booking Test
  - Step 7: First Invoice Test
  - Step 8: First Accounting Sync Test
  - Step 9: Reconciliation Check (booking vs invoice vs accounting)
- **3 Operating Modes**: sandbox (platform test), simulation (demo), production (real customer)
- **Pilot Dashboard KPIs**:
  - Platform Health: search success rate, booking success rate, supplier latency, supplier error rate
  - Financial Flow: booking→invoice conversion, invoice→accounting sync latency, reconciliation mismatch rate
  - Pilot Usage: active agencies, daily searches, daily bookings, revenue generated
  - Incident Monitoring: failed bookings, failed invoices, failed accounting sync, critical alerts
- **Collections**: pilot_agencies, pilot_metrics, pilot_incidents
- **Supplier Support**: RateHawk, Paximum, TBO, WWTatil
- **Accounting Provider Support**: Luca, Logo, Parasut, Mikro
- **Pilot Target**: 3 agencies (Agency A → Ratehawk+Luca, Agency B → Paximum+Parasut, Agency C → WWTatil+Luca)

### Multi Accounting Provider Architecture (MEGA PROMPT #34) - IMPLEMENTED
- Base Provider Contract, Normalized Response, 4 Provider Adapters
- Capability Matrix, Provider Routing, Credential Management (AES-256-GCM)
- Provider Health Monitoring, Failover Strategy

### Reconciliation & Finance Operations Layer (MEGA PROMPT #33) - IMPLEMENTED
- Reconciliation Engine, Finance Operations Queue, Financial Alerts

### Accounting Automation Layer (MEGA PROMPT #32) - IMPLEMENTED
- Customer matching, Accounting sync queue, Auto-sync rule engine

## Technical Architecture

### Backend
- FastAPI + MongoDB + Redis
- APScheduler for background jobs
- AES-256-GCM credential encryption
- Collection prefix for tenant isolation

### Frontend
- React + Shadcn UI
- Page routing via React Router
- Admin pages: Dashboard, Pilot Wizard, Pilot Dashboard, Accounting Providers, Finance Ops, etc.

### Key Collections (MEGA PROMPT #35)
- `pilot_agencies` — Agency setup + wizard completion state + flow results
- `pilot_metrics` — Per-step metrics (latency, success rate, timestamps)
- `pilot_incidents` — Failed flow steps and critical alerts

### Key API Endpoints (MEGA PROMPT #35)
- `POST /api/pilot/onboarding/setup` — Create pilot agency (step 1)
- `PUT /api/pilot/onboarding/setup/supplier` — Save supplier credential (step 2)
- `PUT /api/pilot/onboarding/setup/accounting` — Save accounting credential (step 3)
- `POST /api/pilot/onboarding/test-connection` — Test connections (step 4)
- `POST /api/pilot/onboarding/test-search` — Test search (step 5)
- `POST /api/pilot/onboarding/test-booking` — Test booking (step 6)
- `POST /api/pilot/onboarding/test-invoice` — Test invoice (step 7)
- `POST /api/pilot/onboarding/test-accounting` — Test accounting sync (step 8)
- `POST /api/pilot/onboarding/test-reconciliation` — Reconciliation check (step 9)
- `GET /api/pilot/onboarding/agencies` — List pilot agencies
- `GET /api/pilot/onboarding/metrics` — Pilot metrics dashboard
- `GET /api/pilot/onboarding/incidents` — Pilot incidents

## What's Mocked
- **Pilot Flow Tests**: All flow tests (search, booking, invoice, accounting, reconciliation) use SIMULATED data in sandbox/simulation mode
- **LucaProvider**: Simulation mode when real Luca API is unreachable
- **Logo/Parasut/Mikro**: Stub providers returning ERR_UNSUPPORTED
- **Real Supplier APIs**: Not connected yet — pilot phase uses sandbox mode

## Credentials
- Super Admin: admin@acenta.test / admin123
- Agency Admin: agency1@demo.test / agency123

## Test Stabilization Status (Feb 2026) - COMPLETED
- Fixture conflicts fixed, PyMongo AutoReconnect fixed, 39 mocked HTTP tests added
- 139/139 tests passed + 15/15 pilot onboarding tests

## Upcoming Tasks (P1)
- Onboard 3 pilot agencies through the wizard with real credentials
- Connect real supplier APIs (RateHawk, Paximum first)
- Validate first real booking-to-invoice-to-accounting sync flow
- Run the full chain at least 10 times with real data

## Future Tasks (P2+)
- Full financial analytics dashboard
- Tax reporting module
- Payment/refund tracking integration
- APScheduler → Celery Beat migration
- CI/CD pipeline improvements
- Multi-provider fallback
- Nested Button HTML warning fix

## Redis Status
- Running on port 6379 (used by customer matching, rate limiting, caching)
