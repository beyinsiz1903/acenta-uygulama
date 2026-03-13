# Syroce — Travel Agency SaaS Platform

## Product Requirements Document (PRD)

### Original Problem Statement
Enterprise travel SaaS platform with supplier ecosystem, booking orchestration, operations layer, governance layer, and integration reliability layer. Built on Domain-Driven Design with MongoDB, FastAPI, Redis, Celery.

### User Personas
- **Super Admin**: Full platform access, manages all tenants, system config
- **Ops Admin**: Operations management, supplier overrides, incident resolution
- **Finance Admin**: Payment overrides, refund approvals, settlement management
- **Agency Admin**: Agency-level management, bookings, settings
- **Agent**: Standard booking agent, CRM operations
- **Support**: Read-only troubleshooting access

### Core Architecture
```
/app/backend/app/
├── domain/
│   ├── reliability/       # Integration Reliability Layer
│   ├── governance/        # RBAC, Audit, Secrets, Compliance
│   ├── suppliers/         # Supplier contracts, adapters
│   └── operations/        # Booking lifecycle, financials
├── routers/
│   ├── production.py              # NEW - Production Activation API
│   ├── ops_finance_accounts.py    # DECOMPOSED from ops_finance.py
│   ├── ops_finance_refunds.py     # DECOMPOSED
│   ├── ops_finance_settlements.py # DECOMPOSED
│   ├── ops_finance_documents.py   # DECOMPOSED
│   ├── ops_finance_suppliers.py   # DECOMPOSED
│   ├── reliability.py             # Reliability API
│   ├── governance.py              # Governance API
│   └── suppliers_ecosystem.py     # Supplier API
├── middleware/
│   └── rbac_middleware.py  # NEW - Default-deny RBAC enforcement
├── services/
│   ├── voucher_service.py      # NEW - WeasyPrint PDF pipeline
│   ├── delivery_service.py     # NEW - Resend/Slack/Webhook delivery
│   └── production_readiness.py # NEW - Go-live certification
├── suppliers/
│   └── real_integrations.py    # NEW - Paximum/AviationStack/Amadeus skeletons
└── tasks/
    └── production_tasks.py     # NEW - Real Celery task bodies
```

### What's Been Implemented

#### Phase 1: Foundation (Complete)
- Multi-tenant SaaS with agency management
- Booking lifecycle (search, hold, confirm, cancel)
- Financial operations (accounts, payments, refunds, settlements)
- Pricing engine with rules and markup
- CRM and customer management

#### Phase 2: Enterprise Layers (Complete)
- Supplier Ecosystem Layer (adapters, failover, registry)
- Operations Layer (playbooks, incidents, financials)
- Governance Layer (RBAC, audit, secrets, compliance)
- Integration Reliability Layer (resilience, retry, contract validation)

#### Phase 3: Production Activation Layer (JUST COMPLETED - March 2026)
- **P0 - Redis Recovery**: Installed and verified Redis health
- **P0 - Reliability Pipeline Wiring**: Every supplier call passes through timeout → retry → contract validation → metrics → incident logging → degrade/disable
- **P0 - RBAC Enforcement Middleware**: Default-deny permission checks on all API routes
- **P0 - God Router Decomposition**: ops_finance.py (2453 lines) → 5 domain routers
- **P1 - Real Celery Task Bodies**: Voucher generation, email, Slack alerts, cleanup, incident escalation
- **P1 - PDF/Voucher Pipeline**: WeasyPrint with branded templates, QR codes, localization
- **P1 - Notification Delivery**: Resend (primary), Slack/webhook (secondary) with audit log
- **P2 - Frontend Dashboard**: Production Activation page with 5 tabs
- **P2 - Secret Management Migration**: Env-based → Vault/KMS migration path
- **P2 - Supplier Integration Prep**: Paximum, AviationStack, Amadeus adapter skeletons
- **P2 - Production Readiness Certification**: 30 tasks, risk matrix, maturity score

### Testing Status
- Reliability Layer: 40/40 tests (iteration_6.json)
- Production Activation Layer: 21/21 backend + 5/5 frontend tabs (iteration_70.json)

### Current Scores
- Production Readiness: 80%
- Platform Maturity: 7.5/10 (near_ready)
- Go-Live Ready: YES (0 critical failures)

### Mocked Services
- Resend email (no RESEND_API_KEY)
- Slack webhook (no SLACK_WEBHOOK_URL)
- Celery tasks (Redis available but worker not running in preview)

### Prioritized Backlog

#### P0 (Critical - Next)
- Live supplier integrations (Paximum first)
- Configure Resend API key for real email delivery
- Celery worker deployment with beat scheduler

#### P1 (High Priority)
- Supplier dashboard enhancements
- Audit drill-down UI
- Live refresh (WebSocket/SSE) for dashboards
- DLQ consumer implementation
- Secret rotation automation

#### P2 (Future)
- Multi-language voucher templates
- Cross-tenant isolation enforcement
- Prometheus alerting rules
- Performance testing and tuning
- API versioning documentation

### Key API Endpoints
- `/api/production/pipeline/status` - Pipeline health
- `/api/production/readiness` - Readiness certification
- `/api/production/readiness/tasks` - Top 30 tasks
- `/api/production/readiness/secrets` - Secret inventory
- `/api/production/vouchers/generate` - PDF voucher generation
- `/api/production/notifications/email` - Email dispatch
- `/api/production/suppliers/integrations` - Supplier configs
- `/api/ops/finance/accounts` - Finance accounts (decomposed)
- `/api/ops/finance/refunds` - Refund cases (decomposed)
- `/api/ops/finance/settlements` - Settlements (decomposed)

### Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
