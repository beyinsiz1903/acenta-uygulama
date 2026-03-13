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

## Current Architecture Version: 6.0 (Integration Reliability Layer)

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
1. **Supplier Performance Dashboard** — Real-time latency (p50/p95/p99), error rate, timeout rate
2. **Booking Funnel Analytics** — 8-stage funnel (draft->voucher_issued), conversion rates
3. **Failover Visibility** — Failover summary, circuit breaker states, health timeline
4. **Booking Incident Tracking** — Stuck booking detection, payment mismatches, manual recovery
5. **Supplier Debugging Tools** — Interaction logging, request/response inspection, dry-run replay
6. **Real-Time Alerting** — Alert rules engine, Slack/email dispatch, lifecycle
7. **Voucher Pipeline** — Create->Generate(HTML)->Send, retry logic
8. **OPS Admin Panel** — Booking inspection, supplier override, manual failover
9. **Operations Metrics** — Prometheus exposition format, JSON metrics
10. **Operations Roadmap** — 30 improvements, risk analysis, production readiness score

### Phase 5 — Enterprise Governance (Complete - 2026-03-12)
10-part governance architecture:
1. **RBAC System** — 6 hierarchical roles, role inheritance
2. **Permission Model** — 46 fine-grained permissions, wildcard matching
3. **Audit Logging** — Full change tracking, hash-based tamper detection
4. **Secret Management** — Encrypted storage, version-tracked rotation
5. **Tenant Security** — Cross-tenant access blocking, violation logging
6. **Compliance Logging** — Hash-chain integrity, financial operation logging
7. **Data Access Policies** — Configurable rules (allow/deny), role-based conditions
8. **Security Alerting** — 10 alert types, 5 severity levels, full lifecycle
9. **Admin Governance Panel** — Aggregated dashboard, user inspection
10. **Governance Roadmap** — Top 25 improvements, security maturity score

### Phase 6 — Integration Reliability (Complete - 2026-03-13)
10-part reliability architecture (35 API endpoints, 13 MongoDB collections):
1. **Supplier API Resilience** — Configurable timeouts, token-bucket rate limiting, adapter isolation, automatic retries with exponential backoff
2. **Supplier Sandbox** — Mock responses, test bookings, fault injection (9 fault types), call history logging
3. **Retry Strategy & DLQ** — Per-category retry config (supplier/payment/voucher), exponential backoff with jitter, dead-letter queue with full lifecycle (enqueue/retry/discard)
4. **Identity & Idempotency** — Idempotency key store with 24h TTL, request deduplication (60s window), duplicate detection for 6 operation types
5. **API Versioning** — Multi-version support per supplier, version registration/deprecation, version change history
6. **Contract Validation** — Schema validation for search/confirm/cancel responses, schema hash computation, drift detection, violation logging
7. **Integration Metrics** — Per-supplier metrics (call count, errors, latency), latency percentiles (p50/p95/p99), error rate timeline, success rate summary
8. **Supplier Incident Response** — Auto-detection of outages/high error rates/high latency, auto-actions (disable/degrade supplier, increase timeout), full incident lifecycle (open->acknowledge->resolve)
9. **Integration Dashboard** — Engineering overview (supplier health, open incidents, DLQ pending, contract violations), per-supplier detail view
10. **Reliability Roadmap** — Top 20 improvements, 8-dimension maturity score, risk analysis

---

## API Endpoints — Reliability Layer (/api/reliability/*)

| Method | Endpoint | Part | Description |
|--------|----------|------|-------------|
| GET | /api/reliability/resilience/config | P1 | Resilience configuration |
| PUT | /api/reliability/resilience/config | P1 | Update supplier resilience |
| GET | /api/reliability/resilience/stats | P1 | Resilience stats |
| GET | /api/reliability/sandbox/config | P2 | Sandbox configuration |
| PUT | /api/reliability/sandbox/config | P2 | Update sandbox |
| POST | /api/reliability/sandbox/call | P2 | Execute sandbox call |
| GET | /api/reliability/sandbox/log | P2 | Sandbox call history |
| GET | /api/reliability/retry/config | P3 | Retry configuration |
| POST | /api/reliability/dlq | P3 | Enqueue to DLQ |
| GET | /api/reliability/dlq | P3 | List DLQ entries |
| POST | /api/reliability/dlq/{id}/retry | P3 | Retry DLQ entry |
| DELETE | /api/reliability/dlq/{id} | P3 | Discard DLQ entry |
| GET | /api/reliability/dlq/stats | P3 | DLQ statistics |
| POST | /api/reliability/idempotency/check | P4 | Check idempotency |
| GET | /api/reliability/idempotency/stats | P4 | Idempotency stats |
| GET | /api/reliability/versions | P5 | Version registry |
| POST | /api/reliability/versions | P5 | Register version |
| POST | /api/reliability/versions/deprecate | P5 | Deprecate version |
| GET | /api/reliability/versions/history | P5 | Version history |
| POST | /api/reliability/contracts/validate | P6 | Validate contract |
| GET | /api/reliability/contracts/status | P6 | Contract status |
| GET | /api/reliability/metrics/suppliers | P7 | Supplier metrics |
| GET | /api/reliability/metrics/latency/{code} | P7 | Latency percentiles |
| GET | /api/reliability/metrics/error-rate | P7 | Error rate timeline |
| GET | /api/reliability/metrics/success-rate | P7 | Success rate summary |
| POST | /api/reliability/incidents | P8 | Create incident |
| GET | /api/reliability/incidents | P8 | List incidents |
| POST | /api/reliability/incidents/{id}/acknowledge | P8 | Acknowledge |
| POST | /api/reliability/incidents/{id}/resolve | P8 | Resolve |
| POST | /api/reliability/incidents/detect | P8 | Auto-detect issues |
| GET | /api/reliability/incidents/stats | P8 | Incident stats |
| GET | /api/reliability/dashboard | P9 | Dashboard overview |
| GET | /api/reliability/dashboard/supplier/{code} | P9 | Supplier detail |
| GET | /api/reliability/roadmap | P10 | Roadmap + maturity |
| GET | /api/reliability/maturity | P10 | Maturity score |

---

## MongoDB Collections — Reliability Layer (13 total)

| Collection | Part | TTL |
|------------|------|-----|
| rel_resilience_events | P1 | 30 days |
| rel_resilience_config | P1 | None |
| rel_sandbox_config | P2 | None |
| rel_sandbox_log | P2 | 7 days |
| rel_dead_letter_queue | P3 | None |
| rel_retry_config | P3 | None |
| rel_idempotency_store | P4 | 24h |
| rel_request_dedup | P4 | 60s |
| rel_api_versions | P5 | None |
| rel_version_history | P5 | None |
| rel_contract_schemas | P6 | None |
| rel_contract_violations | P6 | 90 days |
| rel_metrics | P7 | 30 days |
| rel_incidents | P8 | None |
| rel_supplier_status | P8/P9 | None |

---

## Pending / Backlog

### P0 — Critical
- God Router decomposition (ops_finance.py -> domain routers)
- Replace mock adapters with real supplier integrations (Paximum, AviationStack)
- Implement real Celery task bodies
- Enforce RBAC permission checks on ALL existing endpoints (middleware)
- Migrate secret encryption from base64 to Vault/KMS

### P1 — High
- Frontend governance admin panel (React dashboard)
- Frontend reliability dashboard (React)
- API-level permission middleware enforcement
- Auto-log all payment/refund operations to compliance
- Alert deduplication and rate limiting
- Auto-incident detection scheduler (Celery beat)
- Slack/email notification integration for security alerts
- Row-level tenant isolation on all collections
- DLQ consumer workers (Celery)
- Prometheus metrics exporter for reliability
- Redis-backed distributed rate limiter

### P2 — Medium
- GDS connectivity (Amadeus, Sabre)
- Supplier sandbox for staging/QA
- Booking reconciliation
- Dynamic pricing
- GDPR data retention automation
- Audit log export to S3/GCS
- Schema drift alerting
- Supplier SLA tracking

### P3 — Future
- ML-based supplier ranking
- Predictive failure detection
- Multi-region failover
- Fraud detection
- ABAC (attribute-based access control)
- ML-based insider threat detection
- ML anomaly detection on metrics

---

## Test Credentials
- **Super Admin:** agent@acenta.test / agent123 (super_admin + agency_admin)
- **Agency User:** agency1@demo.test / agency123

## Key Files
- `/app/backend/app/domain/reliability/` — Reliability layer domain (10 services)
- `/app/backend/app/routers/reliability.py` — Reliability API router (35 endpoints)
- `/app/backend/app/domain/governance/` — Governance layer domain
- `/app/backend/app/routers/governance.py` — Governance API router (37 endpoints)
- `/app/backend/app/suppliers/` — Supplier ecosystem
- `/app/backend/app/suppliers/operations/` — Operations layer
- `/app/memory/reliability_roadmap.md` — Reliability roadmap doc
- `/app/memory/governance_roadmap.md` — Governance roadmap doc
- `/app/test_reports/iteration_69.json` — Reliability test report (40/40 passed)
- `/app/test_reports/iteration_5.json` — Governance test report (37/37 passed)
