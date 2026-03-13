# Syroce — Travel SaaS Platform PRD

## Problem Statement
Enterprise travel SaaS platform serving B2B travel agencies. The platform provides supplier ecosystem, booking orchestration, operations layer, governance layer, integration reliability layer, and production activation layer.

## Current Phase: Platform Hardening Phase
Architecture maturity score: 3.15/10 (hardening readiness) | 9.3/10 (architectural completeness)

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
- Redis recovery
- God Router decomposition (6 finance routers)
- RBAC enforcement middleware
- Reliability pipeline wiring
- PDF/Voucher pipeline (WeasyPrint)
- Notification delivery service (Resend)
- Celery task skeletons
- Supplier adapter skeletons (Paximum, Amadeus, AviationStack)
- Frontend Production Dashboard

### Platform Hardening Phase (Complete - Feb 13, 2026)
All 10 parts implemented and tested (17/17 backend + 11/11 frontend):

1. **Supplier Traffic Testing** — sandbox/shadow/canary/production modes for 3 suppliers
2. **Worker Deployment Strategy** — 5 Celery pools, DLQ consumers, auto-scaling rules
3. **Observability Stack** — 17 Prometheus metrics, 4 Grafana dashboards, 6 alert rules, OpenTelemetry
4. **Performance Testing** — 3 load profiles (up to 500 agencies), 4 scenarios, 7 SLA targets
5. **Multi-Tenant Safety** — 20 collection audit, 7 isolation scenarios
6. **Secret Management Migration** — 9 secrets inventory, 4-phase migration plan
7. **Incident Response Playbooks** — 3 playbooks (supplier outage, queue backlog, payment failure)
8. **Auto-Scaling Strategy** — 4 component configs (API, workers, Redis, MongoDB)
9. **Disaster Recovery** — 3 scenarios (region outage, DB corruption, queue loss)
10. **Hardening Checklist** — 50 tasks, maturity scoring

## Key API Endpoints
- `/api/hardening/status` — Combined hardening status
- `/api/hardening/traffic/*` — Supplier traffic testing
- `/api/hardening/workers/status` — Worker pools
- `/api/hardening/observability/*` — Observability stack
- `/api/hardening/performance/*` — Performance testing
- `/api/hardening/tenant-safety/audit` — Tenant isolation
- `/api/hardening/secrets/status` — Secret management
- `/api/hardening/incidents/*` — Incident playbooks
- `/api/hardening/scaling/status` — Auto-scaling
- `/api/hardening/dr/plan` — Disaster recovery
- `/api/hardening/checklist` — Hardening checklist

## Frontend Routes
- `/app/admin/platform-hardening` — Platform Hardening Dashboard (11 tabs)
- `/app/admin/production-activation` — Production Activation Dashboard

## Prioritized Backlog

### P0 — Go-Live Blockers (6 remaining)
1. Migrate secrets to Vault/KMS
2. Remove hardcoded AviationStack API key
3. Deploy Redis HA
4. Deploy MongoDB ReplicaSet
5. JWT secret rotation
6. Full tenant isolation verification

### P1 — High Priority
7. Deploy Prometheus + Grafana
8. OpenTelemetry instrumentation
9. Load testing execution
10. Supplier failover testing

### P2 — Important
11. Kubernetes HPA for API servers
12. KEDA for worker scaling
13. Automated backups with validation
14. Graceful shutdown

### P3 — Future
15. Chaos engineering
16. CDN for static assets
17. Blue-green deployments
18. SLO/SLI tracking
19. GitOps with ArgoCD

## Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
