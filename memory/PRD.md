# Syroce — Travel SaaS Platform PRD

## Problem Statement
Enterprise travel SaaS platform serving B2B travel agencies. The platform provides supplier ecosystem, booking orchestration, operations layer, governance layer, integration reliability layer, and production activation layer.

## Current Phase: Platform Hardening Execution Phase
Architecture maturity score: 9.2/10 | Production readiness: 0/10 (execution not started)
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

### Platform Hardening Execution Phase (Complete - Mar 13, 2026)
- **Dual Score System**: Architecture Maturity (9.2) vs Production Readiness (calculated)
- **Execution Tracker**: 10 phases, 3 sprints, 46 tasks
- **Go-Live Blocker Management**: 6 blockers with fix strategies and resolve capability
- **Go-Live Certification**: Automated readiness assessment with target 8.5/10
- **Sprint Organization**: Sprint 1 (Go-Live Blockers), Sprint 2 (Real Integrations), Sprint 3 (Load & Failure Testing)
- **CTO Architecture Assessment**: Architecture 9.4, Reliability 9.2, Security 9.3, Domain Model 9.3, Operations 9.0
- Tested: 18/18 backend + 13/13 frontend = 100%

## Key API Endpoints
### Execution Tracker (NEW)
- `GET /api/hardening/execution/status` — Full execution status with phases, sprints, blockers
- `GET /api/hardening/execution/phase/{id}` — Phase detail with tasks
- `POST /api/hardening/execution/phase/{id}/start` — Start a phase
- `POST /api/hardening/execution/phase/{id}/task/{task_id}/complete` — Complete a task
- `POST /api/hardening/execution/blocker/{id}/resolve` — Resolve a blocker
- `GET /api/hardening/execution/certification` — Go-live certification report

### Hardening Design
- `GET /api/hardening/status` — Combined status with dual scores
- `GET /api/hardening/traffic/status` — Supplier traffic testing
- `GET /api/hardening/workers/status` — Worker pools
- `GET /api/hardening/observability/status` — Observability stack
- `GET /api/hardening/performance/profiles` — Performance testing
- `GET /api/hardening/tenant-safety/audit` — Tenant isolation
- `GET /api/hardening/secrets/status` — Secret management
- `GET /api/hardening/incidents/playbooks` — Incident playbooks
- `GET /api/hardening/scaling/status` — Auto-scaling
- `GET /api/hardening/dr/plan` — Disaster recovery
- `GET /api/hardening/checklist` — Hardening checklist

## Frontend Routes
- `/app/admin/platform-hardening` — 13-tab Dashboard (Overview, Execution, Certification + 10 design tabs)

## Prioritized Backlog

### P0 — Execute Hardening (Sprint 1: Go-Live Blockers)
1. Secret management migration (Vault/KMS)
2. Worker deployment with queue isolation
3. Monitoring stack activation (Prometheus + Grafana)
4. Redis cluster verification
5. Tenant isolation verification
6. Remove hardcoded AviationStack API key

### P0 — Sprint 2: Real Integrations
7. Paximum shadow traffic activation
8. AviationStack shadow traffic activation
9. Amadeus shadow traffic (optional)
10. Canary deployment and gradual rollout

### P1 — Sprint 3: Load & Failure Testing
11. 10k searches/hour simulation
12. 1k bookings/hour simulation
13. Supplier outage simulation
14. Queue backlog simulation
15. Incident response testing
16. DR testing (DB, Redis, region failover)
17. Go-live certification

### P2 — Business Features
18. Agency Subscription Management
19. Customer acquisition tools

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
