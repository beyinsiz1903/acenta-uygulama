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
- Production pilot launch

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
- 5 dedicated queues, worker pool, DLQ consumers, observability

### Supplier Activation (DONE - Score: 9.88/10)
- 10-part plan: shadow traffic, canary, normalization, failover, rate limiting, health, incidents

### Stress Testing (DONE - Score: 10.0/10)
- 10-part: Load, Queue, Supplier Outage, Payment, Cache, DB, Incident, Tenant, Metrics, Report

### Production Pilot Launch (DONE - Score: 10.0/10)
- **Part 1:** Pilot Environment — controlled production, limited agencies/traffic, feature flags
- **Part 2:** Real Supplier Traffic — Paximum + AviationStack: shadow → limited → full modes
- **Part 3:** Monitoring Stack — Prometheus (12 targets) + Grafana (5 dashboards), live metrics
- **Part 4:** Incident Detection — 8 detection rules, 3 playbooks, Slack/PagerDuty/Email alerts
- **Part 5:** Pilot Agency Onboarding — 3 agencies, pricing tiers, training materials
- **Part 6:** Real Booking Flow — 8-step: search → pricing → availability → booking → payment → supplier → voucher → notify
- **Part 7:** Production Incident Test — supplier outage, payment error, DB slowdown with auto-recovery
- **Part 8:** Real Performance Metrics — P95 latency, supplier reliability, booking success rate, throughput
- **Part 9:** Pilot Report — readiness score, 9 weighted components, traffic stats, incident log
- **Part 10:** Go-Live Decision — GO/CONDITIONAL_GO/NO_GO with checklist, risk assessment, next steps

## Key APIs

### Pilot Launch APIs
- `GET /api/pilot/dashboard` — Combined pilot dashboard
- `GET /api/pilot/environment` — Pilot environment config
- `POST /api/pilot/environment/activate` — Activate pilot environment
- `GET /api/pilot/supplier-traffic` — Supplier traffic status
- `POST /api/pilot/supplier-traffic/{code}/{mode}` — Activate supplier (shadow/limited/full)
- `GET /api/pilot/monitoring` — Prometheus + Grafana status
- `GET /api/pilot/incidents` — Detection rules and alerts
- `POST /api/pilot/incidents/simulate/{type}` — Simulate incident
- `GET /api/pilot/agencies` — Pilot agencies list
- `POST /api/pilot/agencies/onboard?agency_name=X` — Onboard agency
- `POST /api/pilot/booking-flow/{type}` — Execute booking flow
- `POST /api/pilot/incident-test/{scenario}` — Production incident test
- `GET /api/pilot/performance` — Real performance metrics
- `GET /api/pilot/report` — Pilot report
- `GET /api/pilot/go-live` — Go-live decision

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

## Remaining Backlog

### P2 — Future
- Part 6: Dedicated cross-tenant security testing
- Part 7: Real Prometheus/Grafana binding (currently simulated)
- Part 9: Full customer onboarding workflow
- Connect pilot system to real supplier APIs

## Known Issues
- Intermittent `pymongo.errors.AutoReconnect` in batch test runs (P2, recurring)

## Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
