# Syroce — Travel Agency Operating System (PRD)

## Core Product
Multi-tenant SaaS platform for travel agencies. Manages bookings, finance, suppliers, B2B distribution, and internal operations.

## Tech Stack
- **Backend:** FastAPI, Motor, Pydantic, Celery, Redis
- **Frontend:** React, Shadcn/UI
- **Database:** MongoDB
- **Infrastructure:** Redis (cache, rate limiting, Celery broker)
- **Architecture:** Event-Driven, CQRS-lite, Circuit Breaker, Distributed Rate Limiting, DDD
- **Observability:** OpenTelemetry, Prometheus-ready

## Current Architecture Version: 4.0 (Operations Layer)

---

## What's Been Implemented

### Phase 1 — Core Platform (Complete)
- Multi-tenant agency management
- User auth with JWT (role-based)
- Booking CRUD
- Finance (accounts, transactions, payments, invoices)
- Customer management
- Document management
- Web catalog & WebPOS
- Google Sheets & AviationStack integrations

### Phase 2 — Enterprise Infrastructure (Complete)
- Celery + Redis async task queue
- Redis-based distributed rate limiting (token bucket)
- Event-driven architecture (Redis Pub/Sub)
- Circuit breaker pattern (pybreaker)
- OpenTelemetry instrumentation
- MongoDB index optimization
- Infrastructure monitoring router (/api/infra/*)

### Phase 3 — Supplier Ecosystem (Complete - 2026-03-12)
14-part production-grade supplier integration:
- 5 supplier adapters (hotel, flight, tour, insurance, transport)
- Inventory aggregation with fan-out search
- Booking state machine (13 states, 22 transitions)
- Booking orchestration engine with retry/failover
- Supplier failover engine with weighted scoring
- Health scoring (5-metric formula, auto-disable)
- Redis inventory cache with TTL per product type
- 6-stage pricing pipeline
- Channel manager for B2B partners
- Domain events (15 types, 5 handlers)
- 18 API endpoints under /api/suppliers/ecosystem/*

### Phase 4 — Operations Layer (Complete - 2026-03-12)
10-part operations architecture:

1. **Supplier Performance Dashboard** — Real-time latency (p50/p95/p99), error rate, timeout rate, confirmation rate, failover frequency, timeseries
2. **Booking Funnel Analytics** — 8-stage funnel (draft→voucher_issued), conversion rates, supplier reliability
3. **Failover Visibility** — Failover summary, circuit breaker states, health timeline, recent events
4. **Booking Incident Tracking** — Stuck booking detection, failed confirmations, payment mismatches, manual recovery (force-state)
5. **Supplier Debugging Tools** — Interaction logging, request/response inspection, dry-run replay
6. **Real-Time Alerting** — Alert rules engine, Slack/email dispatch, acknowledge/resolve lifecycle
7. **Voucher Pipeline** — Create→Generate(HTML)→Send, retry logic, pipeline status
8. **OPS Admin Panel** — Booking inspection, supplier override (circuit open/close, disable/enable), manual failover, price override, audit log
9. **Operations Metrics** — Prometheus exposition format, JSON metrics, bookings/min, conversion rates, error rates
10. **Operations Roadmap** — 30 improvements, risk analysis, production readiness score (62/100)

---

## API Endpoints — Operations Layer (/api/ops/suppliers/*)

| Method | Endpoint | Part | Description |
|--------|----------|------|-------------|
| GET | /api/ops/suppliers/performance/dashboard | P1 | Real-time supplier dashboard |
| GET | /api/ops/suppliers/performance/timeseries/{code} | P1 | Latency timeseries |
| GET | /api/ops/suppliers/funnel/analytics | P2 | Booking funnel |
| GET | /api/ops/suppliers/funnel/timeseries | P2 | Funnel trends |
| GET | /api/ops/suppliers/failover/dashboard | P3 | Failover visibility |
| GET | /api/ops/suppliers/incidents/detect | P4 | Auto-detect incidents |
| GET | /api/ops/suppliers/incidents | P4 | List incidents |
| POST | /api/ops/suppliers/incidents | P4 | Create incident |
| POST | /api/ops/suppliers/incidents/{id}/resolve | P4 | Resolve incident |
| POST | /api/ops/suppliers/incidents/recovery/force-state/{id} | P4 | Force booking state |
| GET | /api/ops/suppliers/debug/interactions | P5 | Debug logs |
| GET | /api/ops/suppliers/debug/interactions/{id} | P5 | Interaction detail |
| POST | /api/ops/suppliers/debug/replay/{id} | P5 | Replay request |
| GET | /api/ops/suppliers/alerts | P6 | List alerts |
| POST | /api/ops/suppliers/alerts/{id}/acknowledge | P6 | Acknowledge |
| POST | /api/ops/suppliers/alerts/{id}/resolve | P6 | Resolve |
| POST | /api/ops/suppliers/alerts/evaluate | P6 | Evaluate rules |
| POST | /api/ops/suppliers/alerts/config | P6 | Configure channels |
| POST | /api/ops/suppliers/vouchers | P7 | Create voucher |
| POST | /api/ops/suppliers/vouchers/{id}/generate | P7 | Generate PDF |
| POST | /api/ops/suppliers/vouchers/{id}/send | P7 | Send email |
| GET | /api/ops/suppliers/vouchers/pipeline | P7 | Pipeline status |
| POST | /api/ops/suppliers/vouchers/retry-failed | P7 | Retry failed |
| GET | /api/ops/suppliers/admin/booking/{id} | P8 | Inspect booking |
| POST | /api/ops/suppliers/admin/supplier/{code}/override | P8 | Supplier override |
| POST | /api/ops/suppliers/admin/supplier/{code}/manual-failover | P8 | Manual failover |
| POST | /api/ops/suppliers/admin/price-override | P8 | Price override |
| GET | /api/ops/suppliers/admin/audit-log | P8 | Audit trail |
| GET | /api/ops/suppliers/metrics | P9 | JSON metrics |
| GET | /api/ops/suppliers/metrics/prometheus | P9 | Prometheus format |

---

## New MongoDB Collections (Operations Layer)

| Collection | Purpose | TTL |
|------------|---------|-----|
| supplier_debug_logs | Supplier request/response logs | 7 days |
| ops_incidents | Incident tracking | None |
| ops_alerts | Alert history | 30 days |
| ops_alert_config | Per-org alert config | None |
| ops_audit_log | Audit trail | 90 days |
| ops_email_queue | Email delivery queue | 7 days |
| voucher_pipeline | Voucher generation | None |

---

## Pending / Backlog

### P0 — Critical
- God Router decomposition (ops_finance.py → domain routers)
- Replace mock adapters with real supplier integrations (Paximum, AviationStack)
- Implement real Celery task bodies
- Real PDF generation (weasyprint) for voucher pipeline
- Email delivery integration (SendGrid/SES)
- Slack webhook integration

### P1 — High
- Frontend ops admin panel (React dashboard)
- RBAC (role-based access control)
- Alert deduplication and rate limiting
- Auto-incident detection scheduler (Celery beat)
- Supplier debug middleware (auto-log all adapter calls)
- Grafana dashboard templates
- Secret management (replace hardcoded API keys)

### P2 — Medium
- GDS connectivity (Amadeus, Sabre)
- Supplier sandbox environment
- Booking reconciliation
- Dynamic pricing
- PagerDuty integration
- WebSocket real-time feed

### P3 — Future
- ML-based supplier ranking
- Predictive failure detection
- Multi-region failover
- Fraud detection

---

## Test Credentials
- **Agency Admin:** agent@acenta.test / agent123
- **Agency User:** agency1@demo.test / agency123

## Key Files
- `/app/backend/app/suppliers/` — Supplier ecosystem
- `/app/backend/app/suppliers/operations/` — Operations layer
- `/app/backend/app/routers/ops_supplier_operations.py` — Operations API router
- `/app/memory/supplier_ecosystem_architecture.md` — Supplier ecosystem docs
- `/app/memory/operations_architecture.md` — Operations layer docs
- `/app/test_reports/iteration_67.json` — Operations test report (30/30 passed)
- `/app/test_reports/iteration_3.json` — Supplier ecosystem test report (23/23 passed)
