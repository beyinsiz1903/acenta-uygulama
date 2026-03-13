# Syroce — Travel SaaS Platform PRD

## Original Problem Statement
Enterprise multi-tenant travel B2B SaaS platform for agencies. Includes search, booking, pricing, payments, supplier integrations, and ops management.

## Architecture
- **Frontend:** React + Tailwind + Shadcn/UI
- **Backend:** FastAPI + MongoDB + Redis + Celery
- **Suppliers:** Paximum, AviationStack, Amadeus (simulated)

## Core Requirements
- Multi-tenant agency management
- Search, booking, voucher pipelines
- Supplier integrations with failover
- Production readiness with monitoring
- Celery worker infrastructure
- Real supplier traffic activation

## Completed Features

### Phase 1-2: Core Platform (DONE)
- Authentication, multi-tenancy, RBAC
- Hotel/flight search and booking
- Pricing, payments, CRM
- Admin dashboards

### Phase 3: Production Hardening (DONE)
- Security hardening, reliability pipeline
- DLQ system, monitoring
- Platform hardening dashboard with 15+ tabs

### Celery Worker Infrastructure (DONE - Score: 9.88/10)
- 5 dedicated queues (booking, voucher, notification, incident, cleanup)
- Worker pool design, deployment, monitoring
- DLQ consumers, failure handling, observability
- Performance testing, incident response

### Supplier Activation (DONE - Score: 9.88/10)
- **Part 1:** Activation Plan — 3 suppliers configured (Paximum P1, AviationStack P2, Amadeus P3)
- **Part 2:** Shadow Traffic — Compare internal vs supplier pricing
- **Part 3:** Canary Deployment — Gradual % rollout with auto-rollback
- **Part 4:** Response Normalization — Schema conformance, field mapping, type coercion
- **Part 5:** Failover Strategy — Priority chains + cached inventory + circuit breaker
- **Part 6:** Rate Limit Management — Token bucket + adaptive throttling per supplier
- **Part 7:** Supplier Health Monitoring — Latency, error rate, availability tracking
- **Part 8:** Supplier Incident Handling — Auto-degrade + failover + multi-channel alerts
- **Part 9:** Traffic Analysis — Conversion funnel, booking success, revenue metrics
- **Part 10:** Activation Report — Weighted score (9.88/10), deployment checklist

## Key APIs

### Supplier Activation APIs
- `GET /api/supplier-activation/dashboard` — Combined dashboard
- `GET /api/supplier-activation/plan` — Activation plan
- `POST /api/supplier-activation/shadow/{code}` — Run shadow traffic
- `GET /api/supplier-activation/canary` — Canary status
- `POST /api/supplier-activation/canary/{code}/{action}` — Canary control
- `POST /api/supplier-activation/normalization/{code}` — Normalization test
- `GET /api/supplier-activation/failover` — Failover chains
- `POST /api/supplier-activation/failover/{code}/simulate` — Failover simulation
- `GET /api/supplier-activation/rate-limits` — Rate limit status
- `POST /api/supplier-activation/rate-limits/{code}/simulate` — Rate limit simulation
- `GET /api/supplier-activation/health` — Health monitoring
- `POST /api/supplier-activation/incident/{code}` — Incident simulation
- `GET /api/supplier-activation/traffic-analysis` — Traffic analysis
- `GET /api/supplier-activation/score` — Activation score

## Remaining Backlog

### P1 — Next
- Part 4: Performance Testing (10k searches/hr, 1k bookings/hr)
- Part 5: Incident Testing (supplier outages, queue backlogs, payment failures)

### P2 — Future
- Part 6: Tenant Safety Test (cross-tenant security)
- Part 7: Real-Time Dashboard (Prometheus metrics binding)
- Part 9: First Customer Onboarding (agency workflow + pricing)

## Known Issues
- Intermittent `pymongo.errors.AutoReconnect` in batch test runs (P2, 9x recurrence)

## Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
