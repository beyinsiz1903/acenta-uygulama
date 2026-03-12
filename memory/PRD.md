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

## Current Architecture Version: 5.0 (Governance Layer)

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
1. **RBAC System** — 6 hierarchical roles (super_admin > ops_admin > finance_admin > agency_admin > agent > support), role inheritance
2. **Permission Model** — 46 fine-grained permissions (resource.action format), wildcard matching, user permission resolution
3. **Audit Logging** — Full change tracking (who/what/when/before/after), hash-based tamper detection, category filtering
4. **Secret Management** — Encrypted storage, version-tracked rotation, access logging, rotation status monitoring
5. **Tenant Security** — Cross-tenant access blocking, violation logging, isolation health scoring, collection coverage analysis
6. **Compliance Logging** — Hash-chain integrity (GENESIS-linked), financial operation logging, chain verification, tax audit support
7. **Data Access Policies** — Configurable rules (allow/deny), role-based conditions, 4 default policies, policy evaluation engine
8. **Security Alerting** — 10 alert types, 5 severity levels, detect suspicious login/privilege escalation/mass data access, full lifecycle (open->ack->resolve)
9. **Admin Governance Panel** — Aggregated dashboard, user governance profile inspection, cross-domain overview
10. **Governance Roadmap** — Top 25 improvements, dynamic security maturity score, risk analysis (critical/high/medium)

---

## API Endpoints — Governance Layer (/api/governance/*)

| Method | Endpoint | Part | Description |
|--------|----------|------|-------------|
| POST | /api/governance/rbac/seed | P1 | Seed RBAC roles & permissions |
| GET | /api/governance/rbac/roles | P1 | List all roles with hierarchy |
| GET | /api/governance/rbac/hierarchy | P1 | Role hierarchy tree |
| GET | /api/governance/rbac/permissions | P2 | List all 46 permissions |
| PUT | /api/governance/rbac/roles | P1 | Update role permissions |
| GET | /api/governance/rbac/user-permissions | P2 | Resolve user effective permissions |
| GET | /api/governance/rbac/check-permission | P2 | Check specific permission |
| GET | /api/governance/audit/logs | P3 | Search audit logs |
| GET | /api/governance/audit/logs/{id} | P3 | Get audit entry |
| GET | /api/governance/audit/stats | P3 | Audit statistics |
| POST | /api/governance/secrets | P4 | Store/rotate secret |
| GET | /api/governance/secrets | P4 | List secrets (masked) |
| GET | /api/governance/secrets/{name}/value | P4 | Retrieve secret value |
| DELETE | /api/governance/secrets/{name} | P4 | Delete secret |
| GET | /api/governance/secrets/rotation/status | P4 | Rotation status |
| GET | /api/governance/tenant/isolation-report | P5 | Tenant isolation report |
| GET | /api/governance/tenant/violations | P5 | List violations |
| POST | /api/governance/tenant/validate-access | P5 | Validate tenant boundary |
| POST | /api/governance/compliance/log | P6 | Log financial operation |
| GET | /api/governance/compliance/logs | P6 | Search compliance logs |
| GET | /api/governance/compliance/verify-chain | P6 | Verify chain integrity |
| GET | /api/governance/compliance/summary | P6 | Compliance summary |
| POST | /api/governance/data-policies | P7 | Create data policy |
| GET | /api/governance/data-policies | P7 | List data policies |
| POST | /api/governance/data-policies/evaluate | P7 | Evaluate data access |
| PUT | /api/governance/data-policies/{id} | P7 | Update policy |
| DELETE | /api/governance/data-policies/{id} | P7 | Delete policy |
| POST | /api/governance/data-policies/seed | P7 | Seed default policies |
| POST | /api/governance/security/alerts | P8 | Create security alert |
| GET | /api/governance/security/alerts | P8 | List security alerts |
| POST | /api/governance/security/alerts/{id}/acknowledge | P8 | Acknowledge alert |
| POST | /api/governance/security/alerts/{id}/resolve | P8 | Resolve alert |
| GET | /api/governance/security/dashboard | P8 | Security dashboard |
| POST | /api/governance/security/detect/suspicious-login | P8 | Detect suspicious login |
| GET | /api/governance/panel/overview | P9 | Governance overview |
| GET | /api/governance/panel/user/{email} | P9 | User governance profile |
| GET | /api/governance/roadmap | P10 | Roadmap + maturity score |

---

## New MongoDB Collections (Governance Layer)

| Collection | Purpose | TTL |
|------------|---------|-----|
| gov_roles | RBAC role definitions | None |
| gov_permissions | Permission catalog | None |
| gov_audit_log | Governance audit trail | 90 days |
| gov_secrets | Encrypted secret storage | None |
| gov_secret_history | Secret rotation history | None |
| gov_secret_access_log | Secret access tracking | 30 days |
| gov_tenant_violations | Cross-tenant violation log | 90 days |
| gov_compliance_log | Financial compliance records | None |
| gov_data_policies | Data access policy rules | None |
| gov_security_alerts | Security alert lifecycle | 180 days |

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
- API-level permission middleware enforcement
- Auto-log all payment/refund operations to compliance
- Alert deduplication and rate limiting
- Auto-incident detection scheduler (Celery beat)
- Slack/email notification integration for security alerts
- Row-level tenant isolation on all collections

### P2 — Medium
- GDS connectivity (Amadeus, Sabre)
- Supplier sandbox environment
- Booking reconciliation
- Dynamic pricing
- GDPR data retention automation
- Audit log export to S3/GCS

### P3 — Future
- ML-based supplier ranking
- Predictive failure detection
- Multi-region failover
- Fraud detection
- ABAC (attribute-based access control)
- ML-based insider threat detection

---

## Test Credentials
- **Super Admin:** agent@acenta.test / agent123 (super_admin + agency_admin)
- **Agency User:** agency1@demo.test / agency123

## Key Files
- `/app/backend/app/domain/governance/` — Governance layer domain
- `/app/backend/app/routers/governance.py` — Governance API router (37 endpoints)
- `/app/backend/app/suppliers/` — Supplier ecosystem
- `/app/backend/app/suppliers/operations/` — Operations layer
- `/app/backend/app/routers/ops_supplier_operations.py` — Operations API router
- `/app/memory/governance_roadmap.md` — Governance roadmap doc
- `/app/memory/operations_roadmap.md` — Operations roadmap doc
- `/app/test_reports/iteration_68.json` — Governance test report (37/37 passed)
- `/app/test_reports/iteration_4.json` — Operations test report (30/30 passed)
