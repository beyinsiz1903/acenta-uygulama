# Syroce — Travel SaaS Platform PRD

## Problem Statement
Enterprise travel SaaS platform serving B2B travel agencies. The platform provides supplier ecosystem, booking orchestration, operations layer, governance layer, integration reliability layer, and production activation layer.

## Current Phase: Platform Hardening Execution Phase
Architecture maturity score: 9.2/10 | Production readiness: 6.2/10
Target: Production readiness >= 8.5/10

## Core Tech Stack
- **Backend**: FastAPI, Motor (async MongoDB), Celery, Redis, WeasyPrint, Resend
- **Frontend**: React, Shadcn UI, Lucide Icons
- **Database**: MongoDB
- **Infrastructure**: Redis, Kubernetes

## Users / Personas
- **Super Admin**: Full platform control, hardening dashboard access
- **Agency Admin**: Agency operations, bookings, reports
- **Ops Admin**: Operations monitoring, incident response

## What's Been Implemented

### Production Activation Layer (Complete)
- Redis recovery, God Router decomposition, RBAC enforcement
- PDF/Voucher pipeline, Notification delivery, Celery tasks
- Supplier adapters (Paximum, Amadeus, AviationStack)

### Platform Hardening Design Phase (Complete)
All 10 parts designed and tested (28/28 tests):
1. Supplier Traffic Testing — sandbox/shadow/canary/production modes
2. Worker Deployment Strategy — 5 Celery pools, DLQ, auto-scaling
3. Observability Stack — 17 Prometheus metrics, 4 Grafana dashboards, 6 alerts
4. Performance Testing — 3 load profiles, 4 scenarios, 7 SLA targets
5. Multi-Tenant Safety — 20 collection audit, 7 isolation scenarios
6. Secret Management — 9 secrets inventory, 4-phase migration plan
7. Incident Response — 3 playbooks (supplier, queue, payment)
8. Auto-Scaling Strategy — 4 components (API, workers, Redis, MongoDB)
9. Disaster Recovery — 3 scenarios (region, DB, queue)
10. Hardening Checklist — 50 tasks, maturity scoring

### Platform Hardening Execution Tracker (Complete - Mar 13, 2026)
- **Dual Score System**: Architecture Maturity (9.2) vs Production Readiness (calculated)
- **Execution Tracker**: 10 phases, 3 sprints, 46 tasks
- **Go-Live Blocker Management**: 6 blockers with fix strategies
- Tested: 31/31 backend + frontend = 100%

### Production Activation Engine (Complete - Mar 13, 2026)
**11 new activation endpoints with REAL infrastructure data:**
1. **Infrastructure Health** (`/api/hardening/activation/infrastructure`): Real Redis (healthy, latency, memory, queue depths), Celery (worker count, queues, DLQ), MongoDB (latency, collections, data size)
2. **Secret Audit** (`/api/hardening/activation/secrets`): 9 secrets scanned, risk levels, rotation policy, production-readiness percentage
3. **Supplier Verification** (`/api/hardening/activation/suppliers`): 3 suppliers (Paximum, AviationStack, Amadeus), deployment strategy tracking
4. **Performance Baseline** (`/api/hardening/activation/performance`): Real MongoDB read latency, Redis latency, MongoDB ping latency with SLA targets
5. **Incident Simulation** (`/api/hardening/activation/incident/{type}`): 3 incident types (supplier_outage, queue_backlog, payment_failure) with playbook execution
6. **Tenant Isolation** (`/api/hardening/activation/tenant-isolation`): 20 collections scanned, cross-tenant read/write/API tests
7. **Real-time Metrics** (`/api/hardening/activation/metrics`): Aggregated from Prometheus, Redis queues, MongoDB business data
8. **Go-Live Dry Run** (`/api/hardening/activation/dry-run`): 5-step pipeline (Search -> Price -> Book -> Voucher -> Notify)
9. **Onboarding Readiness** (`/api/hardening/activation/onboarding`): 5 checks (agency, pricing, payment, email, users) with workflow
10. **Go-Live Certification** (`/api/hardening/activation/certification`): Weighted 5-dimension scoring (Infrastructure 25%, Security 25%, Reliability 20%, Observability 15%, Operations 15%)

**7 new frontend tabs:**
- Go-Live (default, certification dashboard)
- Infrastructure (live Redis/Celery/MongoDB health)
- Performance (SLA pass rate, latency tests)
- Incidents (simulation buttons)
- Isolation (collection audit table)
- Dry Run (5-step pipeline)
- Onboarding (readiness checks)

Tested: 35/35 backend + 7/7 frontend tabs = 100%

## Current Production Readiness Score: 6.2/10
| Dimension | Score | Weight |
|-----------|-------|--------|
| Infrastructure | 6.7 | 25% |
| Security | 0.8 | 25% |
| Reliability | 10.0 | 20% |
| Observability | 8.0 | 15% |
| Operations | 7.5 | 15% |

### Active Risks
- Weak/default secrets detected (severity: high)
- Celery workers not deployed (severity: high)

## Key API Endpoints

### Production Activation (NEW)
- `GET /api/hardening/activation/infrastructure` — Real infra health
- `GET /api/hardening/activation/secrets` — Secret audit
- `GET /api/hardening/activation/suppliers` — Supplier status
- `GET /api/hardening/activation/performance` — Performance baseline
- `POST /api/hardening/activation/incident/{type}` — Incident simulation
- `GET /api/hardening/activation/tenant-isolation` — Isolation tests
- `GET /api/hardening/activation/metrics` — Real-time metrics
- `GET /api/hardening/activation/dry-run` — Go-live dry run
- `GET /api/hardening/activation/onboarding` — Onboarding readiness
- `GET /api/hardening/activation/certification` — Full certification

### Execution Tracker
- `GET /api/hardening/execution/status` — Full execution status
- `POST /api/hardening/execution/phase/{id}/start` — Start phase
- `POST /api/hardening/execution/phase/{id}/task/{task_id}/complete` — Complete task
- `POST /api/hardening/execution/blocker/{id}/resolve` — Resolve blocker
- `GET /api/hardening/execution/certification` — Certification report

## Frontend Routes
- `/app/admin/platform-hardening` — 16-tab Dashboard (7 activation + 9 design/execution)

## Prioritized Backlog

### P0 — Raise Security Score (currently 0.8)
1. Rotate all weak/default secrets (JWT_SECRET, STRIPE keys, etc.)
2. Remove hardcoded AviationStack API key from codebase
3. Enable secret rotation policies

### P0 — Raise Infrastructure Score (currently 6.7)
4. Deploy Celery workers (currently no_workers)
5. Configure Redis cluster for cache/queue isolation

### P1 — Real Supplier Activation
6. Activate Paximum shadow traffic
7. Activate AviationStack with valid API key
8. Canary deployment and gradual rollout

### P1 — Load Testing
9. 10k searches/hour simulation
10. 1k bookings/hour simulation
11. Bottleneck analysis

### P2 — Tenant Isolation Improvements
12. Add org_id/tenant_id to all collections without it
13. Create compound indexes for tenant queries

### P2 — Go-Live
14. Complete all blocker resolutions
15. Final certification with score >= 8.5
16. First customer onboarding

## Go-Live Blockers (6 Open)
| ID | Blocker | Risk | Est. Hours |
|---|---|---|---|
| BLK-001 | Secrets in .env files | critical | 8h |
| BLK-002 | Hardcoded AviationStack key | critical | 1h |
| BLK-003 | No real supplier integration | critical | 16h |
| BLK-004 | No production monitoring | critical | 8h |
| BLK-005 | Worker deployment not isolated | high | 6h |
| BLK-006 | Tenant isolation unverified | critical | 4h |

## Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
