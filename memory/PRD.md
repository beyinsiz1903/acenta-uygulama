# Syroce — Travel Platform PRD

## Original Problem Statement
Enterprise Travel Agency SaaS + Multi-Supplier Distribution Engine + Revenue Optimization + Platform Scalability + Live Operations + Market Launch + Per-Agency Credential Management + Growth Engine + **Automated e-Invoice / e-Archive Architecture**.

## Core Architecture
```
supplier adapters -> aggregator -> unified search (cached) -> unified booking
-> commission binding -> fallback -> reconciliation -> analytics -> intelligence
-> revenue optimization -> scalability -> operations -> market launch
-> per-agency credential governance -> growth engine
-> INVOICE ENGINE -> e-document provider (EDM) -> accounting sync
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

**Backend:** 5 new API endpoints via `/api/integrators/*`, 1 new endpoint via `/api/invoices/{id}/status-check`
**Frontend:** IntegratorSettings component, enhanced InvoiceDetail with PDF/status, Provider column
**Testing:** 23/23 backend + all frontend tests PASS (iteration_94)
**E-Document Provider:** EDM adapter in SIMULATION mode (real API requires production credentials)

---

## Key API Endpoints

### Integrator Management (Phase 11 -- NEW)
- `GET /api/integrators/providers` -- List supported providers
- `POST /api/integrators/credentials` -- Save integrator credentials (AES-256-GCM)
- `GET /api/integrators/credentials` -- List configured integrators (masked)
- `DELETE /api/integrators/credentials/{provider}` -- Delete credentials
- `POST /api/integrators/test-connection` -- Test integrator connection
- `GET /api/integrators/invoices/{id}/pdf` -- Download invoice PDF

### Invoice Engine (Phase 10 + 11)
- `POST /api/invoices/create-from-booking` -- Create invoice from booking (idempotent)
- `POST /api/invoices/create-manual` -- Create manual invoice with lines
- `GET /api/invoices` -- List invoices with status/source_type filters
- `GET /api/invoices/dashboard` -- Dashboard stats
- `GET /api/invoices/{id}` -- Invoice detail
- `POST /api/invoices/{id}/issue` -- Issue via EDM adapter
- `POST /api/invoices/{id}/cancel` -- Cancel invoice
- `POST /api/invoices/{id}/transition` -- Manual state transition
- `GET /api/invoices/booking/{booking_id}` -- Check booking invoice status
- `GET /api/invoices/{id}/events` -- Event timeline
- `GET /api/invoices/{id}/status-check` -- Check status from integrator (NEW)

---

## DB Collections

### Invoice Engine
- `invoices` -- Invoice documents with state machine, booking linkage, customer profile, lines, totals
- `invoice_events` -- Audit trail for invoice lifecycle events
- `tenant_integrators` -- Per-tenant integrator credentials (AES-256-GCM encrypted) (NEW)

---

## Prioritized Backlog

### P0 -- Invoice Engine Phase 3 (Next)
- Luca accounting sync adapter
- Customer creation in accounting system
- Invoice sync with retry
- Accounting sync status tracking
- Finance/accounting dashboard

### P1 -- Invoice Engine Phase 4 & Backlog
- Logo / Parasut / Mikro accounting adapters
- Automation rules (auto-create invoice, auto-send PDF, auto-sync)
- "Otomatik kes" checkbox on booking confirmation
- Invoice reconciliation (booking vs invoice vs accounting)
- Customer billing profile reuse
- Tax breakdown visibility enhancement

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

## Code Architecture (Invoice Engine + Integrators)

```
backend/app/
  accounting/
    __init__.py
    credential_encryption.py        # AES-256-GCM encrypt/decrypt
    tenant_integrator_service.py    # Tenant credential CRUD
    integrators/
      __init__.py
      base_integrator.py            # ABC interface (5 methods)
      edm_integrator.py             # EDM adapter (real + simulation)
      registry.py                   # Provider registry
  domain/invoice/
    models.py                       # Domain entities, builders
    state_machine.py                # State transitions
    decision_engine.py              # e-Fatura/e-Arsiv decision
    booking_transform.py            # Booking -> Invoice mapping
  services/
    invoice_engine.py               # Core service (updated for EDM)
    efatura/                        # Legacy provider layer
  routers/
    invoice_engine.py               # /api/invoices/*
    integrator_management.py        # /api/integrators/* (NEW)
    efatura.py                      # Legacy /api/efatura/*
frontend/src/
  pages/
    AdminEFaturaPage.jsx            # Invoice Engine dashboard + wizard + integrator settings
  components/
    BookingDetailDrawer.jsx         # "Faturayi Kes" button
```
