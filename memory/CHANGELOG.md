# CHANGELOG — Acenta Master Travel SaaS

## 2026-03-12 — Enterprise Scalability Phase 2

### Redis Infrastructure
- Centralized async/sync Redis client singleton (`infrastructure/redis_client.py`)
- Redis health check integration in `/api/infrastructure/redis`
- Graceful fallback to MongoDB when Redis unavailable

### Token Bucket Rate Limiter
- Atomic Lua script for O(1) token bucket operations (~0.1ms per check)
- 8 rate limit tiers: auth_login, auth_signup, auth_password, api_global, b2b_booking, public_checkout, export, supplier_api
- MongoDB fallback for graceful degradation
- `X-RateLimit-Policy: token_bucket` header on all API responses

### Celery Background Job System
- 6 task queues: default, critical, supplier, notifications, reports, maintenance
- 3 dead letter queues: dlq.default, dlq.critical, dlq.supplier
- Task modules: booking_tasks, supplier_tasks, report_tasks, notification_tasks, maintenance_tasks
- Exponential backoff with jitter retry policies
- Beat schedule for periodic maintenance tasks

### Event-Driven Architecture
- Redis Pub/Sub + MongoDB persistence event bus
- 15 domain event types defined (booking.created, payment.completed, etc.)
- In-process handler registry with async support
- Event query API for audit trail

### Circuit Breaker Pattern
- 6 pre-configured circuit breakers: aviationstack, paximum, stripe, iyzico, google_sheets, email_provider
- States: CLOSED → OPEN → HALF_OPEN → CLOSED
- Configurable thresholds, recovery timeouts, half-open limits
- Manual reset API endpoint

### Observability Stack
- OpenTelemetry tracing initialization
- Prometheus metrics collection framework (counters, gauges, histograms)
- Infrastructure health API (8 endpoints)
- Prometheus text format export endpoint

### Database Performance
- 26 new performance-critical MongoDB indexes
- TTL indexes for auto-cleanup (rate_limits, app_cache, domain_events)
- Covered indexes for booking, reservation, ledger, audit queries

### Architecture Documentation
- `SCALABILITY_ARCHITECTURE.md`: 10-part architecture assessment
- Top 40 scalability improvements ranked by priority
- 120-day roadmap with 4 monthly phases
- Risk analysis matrix
- Platform maturity score: 5.5 → 6.8/10

### Verification
- Testing agent iteration_65: 20/20 backend tests PASSED
- All infrastructure endpoints verified with real Redis
- All existing endpoints confirmed working (health, auth, deep diagnostic)
- Rate limiting confirmed via X-RateLimit-Policy header

---

## 2026-03-12 — Enterprise Stabilization Phase 1

### Enhanced Health Checks
- `GET /api/health` — Simple liveness probe with timestamp
- `GET /api/healthz` — Kubernetes readiness probe
- `GET /api/health/ready` — MongoDB connectivity verification with latency_ms
- `GET /api/health/deep` — Full system diagnostic with collection document counts for 8 critical collections (users, organizations, tenants, memberships, bookings, reservations, products, agencies)

### CSRF Protection Middleware
- Double-submit cookie pattern implemented (`csrf_middleware.py`)
- Cookie-authenticated state-changing requests (POST/PUT/DELETE) validated
- Bearer-token requests exempt (inherently CSRF-safe)
- Exempt paths: health, public, webhooks, partner API
- Registered in middleware stack between SecurityHeaders and ErrorTracking

### MongoDB Schema Validation
- `$jsonSchema` validation applied to 10 critical collections: users, organizations, tenants, bookings, agencies, products, memberships, reservations, finance_accounts, audit_log
- `warn` mode in dev/preview, `error` mode in production
- Applied during app startup (api_app.py lifespan)

### CI/CD Pipeline (GitHub Actions)
- 7-stage pipeline: Lint → Security → Backend Tests → Frontend Build → Contract Tests → Staging Deploy → Production Deploy
- Ruff (Python) + ESLint (JS) lint checks
- pip-audit + yarn audit security scanning
- pytest with coverage and MongoDB service container
- Deploy stages with environment protection

### Stabilization Test Suite
- `test_stabilization_auth.py` — 15 tests: login flow, token validation, role normalization, password policy, hashing
- `test_stabilization_booking.py` — 11 tests: state machine transitions, lifecycle guards (cancel/amend), event persistence, B2B API
- `test_stabilization_tenant_isolation.py` — 6 tests: tenant context injection, cross-tenant data isolation, org-scoped APIs
- `test_stabilization_health.py` — 4 tests: all health check tiers
- `test_stabilization_security.py` — 8 tests: security headers, CSP, HSTS, correlation ID

### Architecture Documentation
- `STABILIZATION_PLAN.md` created with 10 parts: Testing Strategy, CI/CD, Security Hardening, Tenant Isolation, Background Jobs, Rate Limiting, Caching, Observability, Performance, 90-Day Roadmap
- Security Risk Matrix with 10 risk categories
- Top 30 Engineering Improvements prioritized
- Operational Maturity Score tracking

### Verification
- Testing agent iteration_64: 42/42 local ASGI tests PASSED, 14/14 preview HTTP tests PASSED
- All health endpoints verified with real MongoDB (latency: 0.27-0.33ms)
- All security headers verified
- Schema validation applied successfully on startup

---

## 2026-03-09 — Google Sheets reservation import + Otellerim kapasite yansimasi
(Previous changelog entries preserved below)

## 2026-03-09 — Google Sheets admin validation UI + endpoint finalize
## 2026-03-09 — Google Sheets P0 hardening
## 2026-03-09 — CI lint hotfix (requirements + LoginPage)
## 2026-03-09 — Fork revalidation
## 2026-03-09 — Admin Tenant Panel Cleanup
## 2026-03-09 — Billing redirect re-smoke + AppShell branding guard
## 2026-03-09 — Billing History Timeline
## 2026-03-08 — Soft Quota Warning + Upgrade CTA PR-UM5
## 2026-03-08 — Usage Visibility PR-UM4
## 2026-03-08 — Usage Metering PR-UM3
## 2026-03-08 — Usage Metering PR-UM2
## 2026-03-08 — Demo Seed Data Utility
## 2026-03-07 — CI / Test Collection Compatibility Fix
## 2026-03-07 — Deployment / Mongo Migration Hardening
## 2026-03-07 — Usage Metering PR-UM1 Foundation
## 2026-03-07 — Entitlement Projection Engine V1
## 2026-03-07 — /api/v1 Standardizasyonu Tamamlandi
## 2026-03-06 — Auth, Session ve Runtime Hardening
## 2026-03-06 — Operasyonel ve Yonetimsel Iyilestirmeler
