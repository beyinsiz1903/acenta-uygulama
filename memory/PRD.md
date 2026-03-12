# Syroce — Travel Agency Operating System PRD

## Original Problem Statement
Syroce is a Travel Agency Operating System that started as a **Property Management System (PMS)** for hotels and has evolved into a comprehensive **Enterprise Travel SaaS Platform**. The platform now covers booking lifecycle, B2B agency ecosystem, CRM, pricing engine, settlements, supplier integrations, and Google Sheets import tools.

## Current Phase: Enterprise Scalability (Phase 2)
The platform completed **Phase 1: Stabilization** (CI/CD, testing, CSRF) and is now in **Phase 2: Scalability & Async Operations**.

### Maturity Score Progress
- Overall Maturity: 5.5/10 → 6.3/10 (post-Phase 1) → **6.8/10** (post-Phase 2)
- Security: 6.5/10 → 7.5/10
- Architecture: 5/10 → 5.5/10 → **7/10**
- Scalability: 3/10 → **6.5/10**
- Observability: 3/10 → **6/10**
- Test Coverage: 2/10 → 4/10

## Tech Stack
- **Backend**: FastAPI, Motor (async MongoDB), Pydantic, passlib, httpx
- **Frontend**: React, React Router, Tailwind CSS, Shadcn/UI, Axios, Sonner
- **Database**: MongoDB (MongoDB Atlas in production)
- **Auth**: Cookie-based with httpOnly cookies, JWT, 2FA
- **Payments**: Stripe + Iyzico (Turkish payment gateway)
- **External APIs**: AviationStack (flight lookup), Google Sheets, Paximum
- **Caching**: Redis (L1) + MongoDB (L2)
- **Queue**: Celery + Redis (6 queues + 3 DLQ)
- **Events**: Redis Pub/Sub + MongoDB persistence
- **Observability**: OpenTelemetry, Prometheus, Sentry
- **CI/CD**: GitHub Actions (7-stage pipeline)

## Architecture
```
/app
├── backend/app/
│   ├── bootstrap/          # App factory, router registry, middleware
│   ├── billing/            # Stripe + Iyzico payment providers
│   ├── domain/             # Booking state machine
│   ├── indexes/            # MongoDB indexes + schema validation + scalability indexes
│   ├── infrastructure/     # (NEW) Redis, Celery, Event Bus, Circuit Breaker, Rate Limiter, Observability
│   ├── middleware/          # 9 middleware (+ CSRF, updated rate limiter)
│   ├── repositories/       # 25+ data access repos
│   ├── routers/            # 180+ API router files + infrastructure router
│   ├── services/           # 120+ business logic services
│   ├── security/           # B2B context, feature flags, JWT config
│   └── tasks/              # (NEW) Celery tasks (booking, supplier, report, notification, maintenance)
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

## Key DB Collections
- **users**: User accounts with email, password_hash, roles, organization_id
- **organizations**: Multi-tenant organizations with settings
- **tenants**: Tenant records with status and organization link
- **bookings**: Booking lifecycle with state machine statuses
- **agencies**: Travel agency records
- **products**: Hotel/tour/transfer products
- **domain_events**: (NEW) Event bus persistence with TTL
- **rate_limits**: Rate limit tracking (Redis primary, MongoDB fallback)
- **jobs**: Background job queue

## Completed Features

### Phase 1: Stabilization (2026-03-12)
- [x] Enhanced Health Checks (4-tier)
- [x] CSRF Protection Middleware
- [x] MongoDB $jsonSchema Validation (10 collections)
- [x] CI/CD Pipeline (7-stage)
- [x] Stabilization Test Suite (42 tests)
- [x] Architecture Documentation

### Phase 2: Scalability (2026-03-12)
- [x] Redis infrastructure + connection pooling (sync + async)
- [x] Token bucket rate limiter (Lua script, 8 tiers)
- [x] Celery + Redis background job system (6 queues + 3 DLQ)
- [x] Event-driven architecture (Redis Pub/Sub + MongoDB persistence)
- [x] Circuit breaker implementation (6 external services)
- [x] OpenTelemetry distributed tracing initialization
- [x] Prometheus metrics collection framework
- [x] Infrastructure health API (8 endpoints)
- [x] 26 performance-critical MongoDB indexes
- [x] TTL indexes for auto-cleanup (rate_limits, cache, events)
- [x] Full scalability architecture document (SCALABILITY_ARCHITECTURE.md)

## API Endpoints (Key)
### Infrastructure (NEW)
- `GET /api/infrastructure/health` - Full infrastructure health
- `GET /api/infrastructure/redis` - Redis stats
- `GET /api/infrastructure/circuit-breakers` - Circuit breaker statuses
- `POST /api/infrastructure/circuit-breakers/{name}/reset` - Reset breaker
- `GET /api/infrastructure/events` - Event bus status
- `GET /api/infrastructure/rate-limits` - Rate limiter stats
- `GET /api/infrastructure/metrics` - Application metrics
- `GET /api/infrastructure/queues` - Celery queue status

### Health
- `GET /api/health` - Liveness probe
- `GET /api/healthz` - Kubernetes readiness
- `GET /api/health/ready` - DB connectivity
- `GET /api/health/deep` - Full diagnostic

## Remaining Backlog

### P0 — In Progress
- [ ] Event handler wiring (booking lifecycle events)
- [ ] Metrics instrumentation (HTTP, business, infra counters)
- [ ] God Router decomposition (ops_finance.py → 6 modules)

### P1 — Next
- [ ] Event-driven cache invalidation
- [ ] Payment event handlers
- [ ] Grafana dashboard templates
- [ ] Alerting rules configuration
- [ ] Cursor-based pagination
- [ ] N+1 query elimination

### P2 — Future
- [ ] MongoDB replica set with read preferences
- [ ] Redis Sentinel for HA
- [ ] API Gateway (Kong)
- [ ] Service mesh preparation
- [ ] Multi-region deployment design
- [ ] Load testing & capacity planning

## Test Credentials
- **Admin**: agent@acenta.test / agent123
- **Agency Admin**: agency1@demo.test / agency123

## Environment Variables
- `REDIS_URL` - Redis connection (redis://localhost:6379/0)
- `CELERY_BROKER_URL` - Celery broker (default: REDIS_URL)
- `JWT_SECRET` - JWT signing secret
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook verification
