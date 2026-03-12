# Syroce — Travel Agency Operating System PRD

## Original Problem Statement
Syroce is a Travel Agency Operating System that started as a **Property Management System (PMS)** for hotels and has evolved into a comprehensive **Enterprise Travel SaaS Platform**. The platform now covers booking lifecycle, B2B agency ecosystem, CRM, pricing engine, settlements, supplier integrations, and Google Sheets import tools.

## Current Phase: Enterprise Stabilization
The platform underwent a comprehensive enterprise audit (February 2026) revealing:
- Overall Maturity: 5.5/10 → **6.3/10** (post-stabilization)
- Security: 6.5/10 → **7.5/10** (CSRF protection added)
- Architecture: 5/10 → **5.5/10** (documentation + schema validation)
- Test Coverage: 2/10 → **4/10** (stabilization test suite)

## Tech Stack
- **Backend**: FastAPI, Motor (async MongoDB), Pydantic, passlib, httpx
- **Frontend**: React, React Router, Tailwind CSS, Shadcn/UI, Axios, Sonner
- **Database**: MongoDB (MongoDB Atlas in production)
- **Auth**: Cookie-based with httpOnly cookies, JWT, 2FA
- **Payments**: Stripe + Iyzico (Turkish payment gateway)
- **External APIs**: AviationStack (flight lookup), Google Sheets, Paximum
- **Observability**: Sentry, Prometheus middleware, structured logging
- **CI/CD**: GitHub Actions (7-stage pipeline)

## Architecture
```
/app
├── backend/app/
│   ├── bootstrap/          # App factory, router registry, middleware
│   ├── billing/            # Stripe + Iyzico payment providers
│   ├── domain/             # Booking state machine
│   ├── indexes/            # MongoDB indexes + schema validation
│   ├── middleware/          # 9 middleware (+ CSRF protection)
│   ├── repositories/       # 25+ data access repos
│   ├── routers/            # 180+ API router files
│   ├── services/           # 120+ business logic services
│   └── security/           # B2B context, feature flags, JWT config
├── frontend/src/
│   ├── b2b/               # B2B portal
│   ├── components/        # Shared UI components
│   ├── pages/             # 100+ page components
│   └── hooks/             # Auth, dashboard, reservations hooks
├── .github/workflows/
│   └── ci.yml             # 7-stage CI/CD pipeline
└── memory/
    ├── PRD.md
    ├── CHANGELOG.md
    └── ROADMAP.md
```

## Key DB Collections (with Schema Validation)
- **users**: User accounts with email, password_hash, roles, organization_id
- **organizations**: Multi-tenant organizations with settings
- **tenants**: Tenant records with status and organization link
- **bookings**: Booking lifecycle with state machine statuses
- **agencies**: Travel agency records
- **products**: Hotel/tour/transfer products
- **memberships**: User-tenant membership records
- **reservations**: Guest reservation data
- **finance_accounts**: Financial ledger accounts
- **audit_log**: Hash-chain verified audit trail

## Completed Features

### Core Platform
- [x] Multi-tenancy with RBAC
- [x] JWT + Cookie authentication with 2FA
- [x] Booking lifecycle (quote → book → confirm → cancel)
- [x] B2B Agency Network & Marketplace
- [x] CRM (customers, deals, tasks, timeline)
- [x] Pricing Engine (rules, markup/commission)
- [x] Settlement System (ledger, commission)
- [x] Financial Accounting (ops finance, ledger, payments)
- [x] Invoicing with e-Fatura integration
- [x] Voucher System (templates, PDF generation)
- [x] Billing/Subscription (Stripe checkout, plans, lifecycle)
- [x] Public Booking (search, checkout, click-to-pay)
- [x] Google Sheets Integration (connections, sync, writeback)
- [x] Tour Management

### PMS (Property Management System)
- [x] PMS Dashboard (stats, arrivals/in-house/departures/stayovers)
- [x] Room Management (CRUD, floor grouping, status)
- [x] Check-in / Check-out flow
- [x] Reservation enrichment (flight info, tour info)
- [x] Accounting Module (folios, charges, payments)
- [x] Invoice Management (create, issue, mark paid, KDV)
- [x] Flight API Integration (AviationStack)

### Enterprise Stabilization (2026-03-12) ✅
- [x] Enhanced Health Checks (4-tier: liveness, readiness, DB connectivity, deep diagnostic)
- [x] CSRF Protection Middleware (double-submit cookie pattern)
- [x] MongoDB $jsonSchema Validation (10 critical collections)
- [x] CI/CD Pipeline (GitHub Actions, 7-stage: lint → security → tests → build → contracts → staging → production)
- [x] Stabilization Test Suite (42 tests: auth, booking, tenant isolation, health, security)
- [x] Comprehensive Architecture Documentation (STABILIZATION_PLAN.md)
- [x] Security Risk Matrix
- [x] 90-Day Hardening Roadmap

## API Endpoints (Key)
### Health
- `GET /api/health` - Liveness probe
- `GET /api/healthz` - Kubernetes readiness
- `GET /api/health/ready` - DB connectivity check
- `GET /api/health/deep` - Full system diagnostic

### Auth
- `POST /api/auth/login` - Authentication
- `GET /api/auth/me` - Current user info
- `POST /api/auth/refresh` - Token refresh

### PMS
- `GET /api/agency/pms/dashboard` - Dashboard summary
- `GET /api/agency/pms/arrivals|in-house|stayovers|departures` - Operational lists
- `GET/POST/PUT/DELETE /api/agency/pms/rooms` - Room CRUD
- `GET /api/agency/pms/flights/lookup` - Flight lookup

### Booking
- `GET /api/b2b/hotels/search` - Hotel search
- `POST /api/b2b/quotes` - Create quote
- `POST /api/b2b/bookings` - Create booking

## Remaining Backlog

### P0 — In Progress
- [ ] Payment flow test coverage (extend stabilization tests)
- [ ] AviationStack API Key management UI (agency admins)
- [ ] Redis rate limiter (replace MongoDB-based)

### P1 — Next
- [ ] Redis caching layer (pricing, catalog, permissions)
- [ ] Background job system (Celery + Redis)
- [ ] JWT dual-key rotation
- [ ] API key permission scoping
- [ ] PII masking in logs
- [ ] E2E Playwright tests (10 critical flows)

### P2 — Future
- [ ] OpenTelemetry distributed tracing
- [ ] Split God-routers (ops_finance: 2,452 LOC)
- [ ] Frontend component decomposition
- [ ] Channel manager integration (1 live OTA)
- [ ] MongoDB replica set + read preferences
- [ ] Multi-currency settlement

## Test Credentials
- **Superadmin**: agent@acenta.test / agent123
- **Agency Admin**: agency1@demo.test / agency123

## Environment Variables
- `AVIATIONSTACK_API_KEY` - AviationStack API key (backend/.env)
- `JWT_SECRET` - JWT signing secret
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook verification
- `CSRF_SECRET` - CSRF token signing (optional)
