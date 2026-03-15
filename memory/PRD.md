# Syroce — Travel Platform PRD

## Original Problem Statement
Enterprise Travel Agency SaaS + Multi-Supplier Distribution Engine + Revenue Optimization + Platform Scalability + Live Operations + Market Launch + Per-Agency Credential Management + Growth Engine + **Automated e-Invoice / e-Archive Architecture** + **Automated Accounting Operations Layer**.

## Core Architecture
```
supplier adapters -> aggregator -> unified search (cached) -> unified booking
-> commission binding -> fallback -> reconciliation -> analytics -> intelligence
-> revenue optimization -> scalability -> operations -> market launch
-> per-agency credential governance -> growth engine
-> INVOICE ENGINE -> e-document provider (EDM) -> accounting sync (Luca)
-> ACCOUNTING OPERATIONS (customer matching, sync queue, auto-sync rules, scheduler)
```

## Credentials
- Super Admin: admin@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123

---

## Completed Phases

### Phase 1-4: Foundation
Unified Booking, Fallback, Commercial UX, Intelligence, Revenue Optimization

### Phase 5: Scalability (MEGA PROMPT #26)
Search Caching, Commission Binding, Rate Limiting, Job Scheduler, Prometheus, Multi-Currency, Tax

### Phase 6: Operations (MEGA PROMPT #27)
Validation Framework, Capability Matrix, Cache/Fallback/Rate Limit Tests, Launch Readiness

### Phase 7: Market Launch (MEGA PROMPT #28)
Pilot Agency Tracking, Usage Metrics, Feedback System, SaaS Pricing, Launch Dashboard

### Phase 8: Per-Agency Supplier Credential Management -- Mar 13, 2026
AES-256 encrypted credential storage, supplier-specific forms (WWTatil, Paximum, RateHawk, TBO), RBAC, audit logging, enable/disable toggle, token caching

### Phase 9: Growth Engine (MEGA PROMPT #29) -- Mar 13, 2026
10 Components: Agency Acquisition Funnel, Lead & Demo Management, Referral System, Activation Metrics, Customer Success Dashboard, Supplier Expansion, Growth KPIs, Onboarding Automation, Agency Segmentation, Full Growth Report. 22 API endpoints, 7-tab dashboard.

### Phase 10: Invoice Engine -- Phase 1 (MEGA PROMPT #30) -- Mar 15, 2026
Invoice Domain Model, State Machine (10 states), Booking -> Invoice Transformation, E-Document Decision Engine, Invoice API (10 endpoints), "Faturayi Kes" UI, Booking Integration. 32/32 backend tests PASS.

### Phase 11: Invoice Engine -- Phase 2 (MEGA PROMPT #31) -- Mar 15, 2026

**E-Document Provider Activation -- Faz 2 Complete:**

1. **Base Integrator Interface** -- ABC with 5 methods
2. **EDM Adapter** -- Full implementation with real API support + simulation fallback
3. **AES-256-GCM Credential Encryption**
4. **Tenant Integrator Credential Management**
5. **Updated Invoice Engine** -- Decision engine + real integrator adapter
6. **Status Check** -- On-demand + background sync
7. **PDF Download**
8. **Frontend Updates** -- Entegrator settings, SAGLAYICI column, PDF Indir, Durum Kontrol

### Phase 12: Invoice Engine -- Phase 3 (MEGA PROMPT #32) -- Mar 15, 2026

**Luca Muhasebe Senkronizasyon Katmani -- Faz 3 Complete:**

1. **BaseAccountingIntegrator ABC** -- 4 methods
2. **LucaIntegrator Adapter** -- Simulation mode
3. **Accounting Sync Service** -- Idempotent sync with error classification
4. **Credential Management** -- AES-256-GCM encrypted
5. **Accounting Dashboard API** -- Stats endpoint
6. **Invoice Updates** -- accounting_status fields
7. **Frontend: Muhasebe Dashboard**
8. **Frontend: Luca Sync from Invoice Engine**

### Phase 12.5: Automated Accounting Operations Layer -- Mar 15, 2026

**Customer Matching + Sync Queue + Auto-Sync Rules + Background Scheduler:**

1. **Customer Matching Service** -- `accounting_customers` collection. Match order: VKN -> TCKN -> email -> phone -> manual. VKN uniqueness enforced per tenant. Redis cache with fallback. get_or_create_customer auto-creates via Luca adapter.
2. **Accounting Sync Queue** -- `accounting_sync_jobs` collection. Status: pending/processing/synced/failed/retrying. Retry backoff: 5m, 15m, 1h, 6h, 24h. Max 5 attempts. Idempotent by provider+invoice_id. Invoice state NOT changed on accounting failure.
3. **Auto Sync Rule Engine** -- `auto_sync_rules` collection. Triggers: invoice_issued, invoice_approved, manual_trigger. Filters: invoice_type, agency_plan. CRUD API with enable/disable toggle.
4. **Background Scheduler** -- APScheduler jobs: retry queue every 2min, status polling every 10min. Integrated into existing scheduler infrastructure.
5. **Enhanced Accounting Dashboard** -- 6 KPIs: synced, failed, pending, retry queue, customers (with unmatched count), Luca status. 3 tabs: overview (sync jobs), automation (rules), customers (cari hesaplar). Full CRUD for rules and customer management.

**Backend:** 15+ new API endpoints via `/api/accounting/*`
**Frontend:** Enhanced AdminAccountingPage with tabs, rules panel, customer panel
**Testing:** 25/25 backend + all frontend tests PASS (iteration_96)
**Luca Adapter:** SIMULATION mode (real API requires production credentials)

---

## Key API Endpoints

### Accounting Operations (Phase 12.5 -- NEW)
- `GET /api/accounting/dashboard` -- Enhanced stats with customer_stats, active_rules, queue data
- `GET /api/accounting/sync-jobs` -- List sync jobs with filters
- `POST /api/accounting/sync/{invoice_id}` -- Queue-based sync
- `POST /api/accounting/retry` -- Retry by job_id
- `POST /api/accounting/customers/create` -- Create customer (VKN unique)
- `POST /api/accounting/customers/match` -- Match by VKN/TCKN/email/phone
- `POST /api/accounting/customers/get-or-create` -- Auto match/create
- `GET /api/accounting/customers` -- List with search
- `PUT /api/accounting/customers/{id}` -- Manual override
- `POST /api/accounting/rules` -- Create auto-sync rule
- `GET /api/accounting/rules` -- List rules
- `PUT /api/accounting/rules/{id}` -- Update/toggle rule
- `DELETE /api/accounting/rules/{id}` -- Delete rule

### Accounting Sync (Phase 12)
- `GET /api/accounting/providers` -- List providers
- `POST /api/accounting/credentials` -- Save credentials
- `GET /api/accounting/credentials` -- List credentials
- `DELETE /api/accounting/credentials/{provider}` -- Delete
- `POST /api/accounting/test-connection` -- Test connection
- `GET /api/accounting/sync-logs` -- Legacy compat

### Integrator Management (Phase 11)
- `GET /api/integrators/providers` -- List e-doc providers
- `POST /api/integrators/credentials` -- Save credentials
- `GET /api/integrators/credentials` -- List credentials
- `DELETE /api/integrators/credentials/{provider}` -- Delete
- `POST /api/integrators/test-connection` -- Test
- `GET /api/integrators/invoices/{id}/pdf` -- Download PDF

### Invoice Engine (Phase 10 + 11)
- `POST /api/invoices/create-from-booking`
- `POST /api/invoices/create-manual`
- `GET /api/invoices` -- List with filters
- `GET /api/invoices/dashboard` -- Stats
- `GET /api/invoices/{id}` -- Detail
- `POST /api/invoices/{id}/issue` -- Issue via EDM
- `POST /api/invoices/{id}/cancel`
- `POST /api/invoices/{id}/transition`
- `GET /api/invoices/booking/{booking_id}`
- `GET /api/invoices/{id}/events`
- `GET /api/invoices/{id}/status-check`

---

## DB Collections

### Accounting Operations (NEW)
- `accounting_customers` -- Customer matching: tenant_id, provider, external_customer_id, name, vkn, tckn, email, phone, match_method, created_at
- `accounting_sync_jobs` -- Sync queue: job_id, tenant_id, invoice_id, provider, status, attempt_count, last_attempt, next_retry, error_type, error_message, external_ref
- `auto_sync_rules` -- Rule engine: rule_id, tenant_id, rule_name, trigger_event, provider, invoice_type, agency_plan, requires_approval, enabled

### Invoice Engine
- `invoices` -- Invoice documents with state machine, accounting_status, accounting_ref
- `invoice_events` -- Audit trail
- `tenant_integrators` -- Per-tenant credentials (AES-256-GCM)
- `accounting_sync_logs` -- Legacy sync logs

---

## Prioritized Backlog

### P0 -- Completed
All phases through Phase 12.5 are complete.

### P1 -- MEGA PROMPT #33: Reconciliation & Finance Operations
- Booking vs Invoice vs Accounting reconciliation
- Mismatch detection (missing_invoice, missing_sync, amount_mismatch, tax_mismatch, duplicate_accounting_entry)
- Finance operations queue
- Financial alerts
- Automated correction workflows

### P1 -- Multi-provider Architecture
- Logo / Parasut / Mikro adapter contracts (base_adapter pattern)
- Provider capability matrix
- Provider-specific constraints

### P2 -- Platform Backlog
- Real supplier credential validation with live APIs
- Manual Intervention Queue (ops queue)
- Dashboard Enhancement (aging, mismatch view)
- Observability & Alerts (Prometheus metrics for accounting)
- PyMongo AutoReconnect fix
- LEGACY_ROLE_ALIASES cleanup
- Onboard first 3 pilot agencies
- Email automation for onboarding

---

## Code Architecture (Accounting Operations Layer)

```
backend/app/
  accounting/
    __init__.py
    credential_encryption.py
    tenant_integrator_service.py
    accounting_sync_service.py        # Legacy sync service
    customer_matching_service.py      # NEW: Customer matching (VKN/TCKN/email/phone)
    sync_queue_service.py             # NEW: Queue-based sync with retry backoff
    auto_sync_rules_service.py        # NEW: Auto-sync rule engine
    accounting_scheduler.py           # NEW: Background scheduler jobs
    integrators/
      __init__.py
      base_integrator.py
      base_accounting_integrator.py
      edm_integrator.py
      luca_integrator.py
      registry.py
  routers/
    accounting_sync.py                # ENHANCED: 15+ endpoints
    invoice_engine.py
    integrator_management.py
  bootstrap/
    scheduler_app.py                  # MODIFIED: Added accounting scheduler
frontend/src/
  pages/
    AdminAccountingPage.jsx           # ENHANCED: Tabs, Rules, Customers
    AdminEFaturaPage.jsx              # Luca sync button (unchanged)
```
