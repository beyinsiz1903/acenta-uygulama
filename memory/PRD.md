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
- Comprehensive stress testing

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
- 10-part activation plan: shadow traffic, canary deployment, normalization, failover, rate limiting, health monitoring, incident handling, traffic analysis, activation report

### Stress Testing (DONE - Score: 10.0/10)
- **Part 1:** Load Testing — 10k searches/hr, 1k bookings/hr, API/supplier/worker latency
- **Part 2:** Queue Stress — 5k jobs, autoscaling (3→8 workers), completion rate tracking
- **Part 3:** Supplier Outage — Failover logic, circuit breaker, fallback chain for 3 suppliers
- **Part 4:** Payment Failure — 6 failure scenarios, retry logic, incident logging
- **Part 5:** Cache Failure — Redis failure phases (normal→disconnect→degraded→recovery)
- **Part 6:** Database Stress — Query latency, index performance, concurrent writes, aggregation
- **Part 7:** Incident Response — Supplier outage & queue overload with SLA tracking
- **Part 8:** Tenant Safety — 4 tenants, 12 test cases, zero cross-tenant leaks
- **Part 9:** Performance Metrics — P95 latency, error rate, queue depth, supplier availability
- **Part 10:** Stress Test Report — Weighted readiness score, bottlenecks, capacity limits

## Key APIs

### Stress Test APIs
- `POST /api/stress-test/load` — Load testing
- `POST /api/stress-test/queue` — Queue stress
- `POST /api/stress-test/supplier-outage/{code}` — Supplier outage
- `POST /api/stress-test/payment-failure` — Payment failure
- `POST /api/stress-test/cache-failure` — Cache failure
- `POST /api/stress-test/database` — Database stress
- `POST /api/stress-test/incident/{type}` — Incident response
- `POST /api/stress-test/tenant-safety` — Tenant safety
- `GET /api/stress-test/metrics` — Performance metrics
- `GET /api/stress-test/report` — Final report
- `GET /api/stress-test/dashboard` — Combined dashboard

### Supplier Activation APIs
- `GET /api/supplier-activation/dashboard` — Combined dashboard
- `GET /api/supplier-activation/plan` — Activation plan
- `POST /api/supplier-activation/shadow/{code}` — Shadow traffic
- `GET /api/supplier-activation/canary` — Canary status
- `POST /api/supplier-activation/canary/{code}/{action}` — Canary control
- And more...

## Remaining Backlog

### P2 — Future
- Part 6: Tenant Safety Test (cross-tenant security — dedicated)
- Part 7: Real-Time Dashboard (Prometheus metrics binding)
- Part 9: First Customer Onboarding (agency workflow + pricing)

## Known Issues
- Intermittent `pymongo.errors.AutoReconnect` in batch test runs (P2, recurring)

## Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
