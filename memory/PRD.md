# Syroce — Travel Platform PRD

## Original Problem Statement
Enterprise Travel Agency SaaS + Multi-Supplier Distribution Engine + Revenue Optimization + Platform Scalability + Live Operations + Market Launch + Per-Agency Credential Management + Growth Engine + **Automated e-Invoice / e-Archive Architecture**.

## Core Architecture
```
supplier adapters -> aggregator -> unified search (cached) -> unified booking
-> commission binding -> fallback -> reconciliation -> analytics -> intelligence
-> revenue optimization -> scalability -> operations -> market launch
-> per-agency credential governance -> growth engine
-> INVOICE ENGINE -> e-document provider (EDM) -> accounting sync (Luca)
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

1. **Base Integrator Interface** -- ABC with 5 methods: test_connection(), issue_invoice(), get_status(), download_pdf(), cancel_invoice()
2. **EDM Adapter** -- Full implementation with real API support + simulation fallback. EDM-compatible UBL payload builder. Placeholder PDF generation.
3. **AES-256-GCM Credential Encryption** -- Master key derived from JWT_SECRET. Encrypt/decrypt/mask functions.
4. **Tenant Integrator Credential Management** -- Per-tenant credential CRUD in `tenant_integrators` collection. Encrypted storage. Masked display.
5. **Updated Invoice Engine** -- Decision engine checks `has_active_integrator()`. Issue flow uses real integrator adapter. Provider info stored on invoice.
6. **Status Check** -- On-demand status polling from integrator. Background sync job for bulk status updates.
7. **PDF Download** -- Download invoice PDF from integrator or simulation placeholder.
8. **Frontend Updates** -- Entegrator settings panel with save/test/delete. SAGLAYICI column in invoice table. e-Belge Bilgileri in detail modal. PDF Indir and Durum Kontrol buttons.

### Phase 12: Invoice Engine -- Phase 3 (MEGA PROMPT #32) -- Mar 15, 2026

**Luca Muhasebe Senkronizasyon Katmani -- Faz 3 Complete:**

1. **BaseAccountingIntegrator ABC** -- 4 methods: test_connection(), sync_invoice(), get_sync_status(), create_customer()
2. **LucaIntegrator Adapter** -- Full Luca API adapter with simulation fallback. Builds Luca-compatible invoice/customer payloads.
3. **Accounting Sync Service** -- Idempotent sync queue (invoice_id + provider unique). Execute sync with attempt tracking. Error classification (auth_failed, validation_failed, duplicate_record, provider_unreachable, transient_error). Manual retry support.
4. **Credential Management** -- Reuses existing AES-256-GCM encrypted tenant_integrators system. Luca-specific fields: username, password, company_id, endpoint.
5. **Accounting Dashboard API** -- Stats: total_syncs, success, failed, pending, last_sync_at, last_error, providers status.
6. **Invoice Updates** -- accounting_status and accounting_ref fields on invoice documents. Muhasebe column in invoice table showing sync state.
7. **Frontend: Muhasebe Senkronizasyon Page** -- Dashboard with 5 stat cards, sync logs table with filters, Luca credential settings panel.
8. **Frontend: Luca Sync from Invoice Engine** -- "Luca" button on issued invoices to trigger sync directly.

**Backend:** 8 new API endpoints via `/api/accounting/*`
**Frontend:** AdminAccountingPage with dashboard + sync logs + settings. Modified AdminEFaturaPage with Muhasebe column and Luca sync button.
**Testing:** 14/14 backend + all frontend tests PASS (iteration_95)
**Luca Adapter:** SIMULATION mode (real API requires production credentials)

---

## Key API Endpoints

### Accounting Sync (Phase 12 -- NEW)
- `GET /api/accounting/providers` -- List accounting providers (Luca)
- `POST /api/accounting/credentials` -- Save accounting credentials (AES-256-GCM)
- `GET /api/accounting/credentials` -- List configured accounting integrators (masked)
- `DELETE /api/accounting/credentials/{provider}` -- Delete credentials
- `POST /api/accounting/test-connection` -- Test accounting system connection
- `POST /api/accounting/sync/{invoice_id}` -- Sync issued invoice to accounting system
- `POST /api/accounting/retry` -- Manual retry for failed syncs
- `GET /api/accounting/sync-logs` -- List sync logs with filters
- `GET /api/accounting/dashboard` -- Accounting sync dashboard stats

### Integrator Management (Phase 11)
- `GET /api/integrators/providers` -- List supported providers
- `POST /api/integrators/credentials` -- Save integrator credentials
- `GET /api/integrators/credentials` -- List configured integrators (masked)
- `DELETE /api/integrators/credentials/{provider}` -- Delete credentials
- `POST /api/integrators/test-connection` -- Test integrator connection
- `GET /api/integrators/invoices/{id}/pdf` -- Download invoice PDF

### Invoice Engine (Phase 10 + 11)
- `POST /api/invoices/create-from-booking` -- Create invoice from booking (idempotent)
- `POST /api/invoices/create-manual` -- Create manual invoice with lines
- `GET /api/invoices` -- List invoices with filters
- `GET /api/invoices/dashboard` -- Dashboard stats
- `GET /api/invoices/{id}` -- Invoice detail
- `POST /api/invoices/{id}/issue` -- Issue via EDM adapter
- `POST /api/invoices/{id}/cancel` -- Cancel invoice
- `POST /api/invoices/{id}/transition` -- Manual state transition
- `GET /api/invoices/booking/{booking_id}` -- Check booking invoice
- `GET /api/invoices/{id}/events` -- Event timeline
- `GET /api/invoices/{id}/status-check` -- Check status from integrator

---

## DB Collections

### Invoice Engine
- `invoices` -- Invoice documents with state machine, booking linkage, customer profile, lines, totals, accounting_status, accounting_ref
- `invoice_events` -- Audit trail for invoice lifecycle events
- `tenant_integrators` -- Per-tenant integrator credentials (AES-256-GCM encrypted)
- `accounting_sync_logs` -- Accounting sync tracking: sync_id, invoice_id, provider, external_accounting_ref, sync_status, sync_attempt_count, last_error, last_error_type (NEW)

---

## Prioritized Backlog

### P0 -- Completed
All phases through Phase 12 are complete.

### P1 -- Invoice Engine Phase 4 & Backlog
- Logo / Parasut / Mikro accounting adapters
- Automation rules (auto-create invoice, auto-send PDF, auto-sync)
- "Otomatik kes" checkbox on booking confirmation
- Invoice reconciliation (booking vs invoice vs accounting)
- Customer billing profile reuse
- Tax breakdown visibility enhancement
- Background job for status polling (APScheduler/Celery)

### P2 -- Platform Backlog
- Real supplier credential validation with live APIs
- Onboard first 3 pilot agencies
- Lead capture form for landing page
- Email automation for onboarding
- A/B test infrastructure
- Churn prediction
- PyMongo AutoReconnect fix
- LEGACY_ROLE_ALIASES cleanup

---

## Code Architecture (Invoice Engine + Integrators + Accounting)

```
backend/app/
  accounting/
    __init__.py
    credential_encryption.py        # AES-256-GCM encrypt/decrypt
    tenant_integrator_service.py    # Tenant credential CRUD
    accounting_sync_service.py      # NEW: Accounting sync queue + execution
    integrators/
      __init__.py
      base_integrator.py            # ABC for e-document integrators (5 methods)
      base_accounting_integrator.py # NEW: ABC for accounting integrators (4 methods)
      edm_integrator.py             # EDM adapter (real + simulation)
      luca_integrator.py            # NEW: Luca adapter (real + simulation)
      registry.py                   # Provider registry (e-doc + accounting)
  domain/invoice/
    models.py                       # Domain entities, builders
    state_machine.py                # State transitions
    decision_engine.py              # e-Fatura/e-Arsiv decision
    booking_transform.py            # Booking -> Invoice mapping
  services/
    invoice_engine.py               # Core service (EDM + accounting)
  routers/
    invoice_engine.py               # /api/invoices/*
    integrator_management.py        # /api/integrators/*
    accounting_sync.py              # NEW: /api/accounting/*
frontend/src/
  pages/
    AdminEFaturaPage.jsx            # Invoice Engine + Muhasebe column + Luca sync
    AdminAccountingPage.jsx         # NEW: Muhasebe Senkronizasyon dashboard
  components/
    BookingDetailDrawer.jsx         # "Faturayi Kes" button
```
