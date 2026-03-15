# Syroce — Travel Platform PRD

## Original Problem Statement
Enterprise Travel Agency SaaS + Multi-Supplier Distribution Engine + Revenue Optimization + Platform Scalability + Live Operations + Market Launch + Per-Agency Credential Management + Growth Engine + **Automated e-Invoice / e-Archive Architecture**.

## Core Architecture
```
supplier adapters → aggregator → unified search (cached) → unified booking
→ commission binding → fallback → reconciliation → analytics → intelligence
→ revenue optimization → scalability → operations → market launch
→ per-agency credential governance → growth engine
→ INVOICE ENGINE → e-document provider → accounting sync
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

### Phase 8: Per-Agency Supplier Credential Management — Mar 13, 2026
AES-256 encrypted credential storage, supplier-specific forms (WWTatil, Paximum, RateHawk, TBO), RBAC, audit logging, enable/disable toggle, token caching

### Phase 9: Growth Engine (MEGA PROMPT #29) — Mar 13, 2026
10 Components: Agency Acquisition Funnel, Lead & Demo Management, Referral System, Activation Metrics, Customer Success Dashboard, Supplier Expansion, Growth KPIs, Onboarding Automation, Agency Segmentation, Full Growth Report. 22 API endpoints, 7-tab dashboard.

### Phase 10: Invoice Engine — Phase 1 (MEGA PROMPT #30) — Mar 15, 2026

**Invoice Engine Foundation — Faz 1 Complete:**

1. **Invoice Domain Model** — Full entity model with tenant isolation, booking linkage, customer billing profile, tax breakdown, currency breakdown, line items, audit trail
2. **Invoice State Machine** — 10 states: draft → ready_for_issue → issuing → issued → failed → cancelled → refunded → sync_pending → synced → sync_failed. Strict transition validation.
3. **Booking → Invoice Transformation** — Hotel/Tour full support, Flight/Transfer/Activity placeholder. Idempotent creation (same booking = same invoice). Line item generation with tax calculation.
4. **E-Document Decision Engine** — B2B+VKN → e-Fatura, B2C+TCKN → e-Arsiv, no integrator → draft_only. Agency policy override support.
5. **Invoice API** — 10 endpoints: create-from-booking, create-manual, list, dashboard, detail, issue, cancel, transition, booking-check, events
6. **"Faturayi Kes" UI** — Invoice Engine dashboard with stats (total, issued, failed, revenue), 3-step wizard (type select → customer info → lines/booking), filter buttons, invoice table with actions, detail modal with event timeline
7. **Booking Integration** — "Faturayi Kes" button in BookingDetailDrawer, auto-checks existing invoice, idempotent creation

**Backend:** 10 API endpoints via `/api/invoices/*`
**Frontend:** AdminEFaturaPage (Invoice Engine) with dashboard, wizard, table, detail modal
**Testing:** 32/32 backend + all frontend tests PASS (iteration_93)
**E-Document Provider:** MOCKED (MockEFaturaProvider) — real integration in Faz 2

---

## Key API Endpoints

### Invoice Engine (Phase 10 — NEW)
- `POST /api/invoices/create-from-booking` — Create invoice from booking (idempotent)
- `POST /api/invoices/create-manual` — Create manual invoice with lines
- `GET /api/invoices` — List invoices with status/source_type filters
- `GET /api/invoices/dashboard` — Dashboard stats (total, issued, failed, financials)
- `GET /api/invoices/{invoice_id}` — Invoice detail
- `POST /api/invoices/{invoice_id}/issue` — Issue via e-document provider
- `POST /api/invoices/{invoice_id}/cancel` — Cancel invoice
- `POST /api/invoices/{invoice_id}/transition` — Manual state transition
- `GET /api/invoices/booking/{booking_id}` — Check booking invoice status
- `GET /api/invoices/{invoice_id}/events` — Event timeline

### Growth Engine (Phase 9)
- `GET /api/growth/funnel` — Funnel stages with conversion rates
- `GET/POST /api/growth/leads` — Lead CRUD
- `PUT /api/growth/leads/{lead_id}/stage` — Stage progression
- `GET/POST /api/growth/demos` — Demo management
- `GET/POST /api/growth/referrals` — Referral system
- `PUT /api/growth/referrals/{id}/status` — Referral status + rewards
- `GET /api/growth/activation` — All activations
- `GET /api/growth/activation/{agency_id}` — Agency activation score
- `POST /api/growth/activation/{agency_id}/event` — Record event
- `GET /api/growth/customer-success` — Success dashboard
- `GET /api/growth/kpis` — Growth KPIs
- `GET /api/growth/report` — Full growth report

### Supplier Credentials (Phase 8)
- `GET/POST/DELETE /api/supplier-credentials/*` — Agency CRUD
- `GET/POST/PUT/DELETE /api/supplier-credentials/admin/*` — Super admin
- `GET /api/supplier-credentials/admin/audit-log` — Audit trail

---

## DB Collections

### Invoice Engine (NEW)
- `invoices` — Invoice documents with state machine, booking linkage, customer profile, lines, totals
- `invoice_events` — Audit trail for invoice lifecycle events

### Growth Engine
- `growth_leads`, `growth_demos`, `growth_referrals`, `growth_activation_events`, `growth_onboarding_tasks`, `growth_supplier_requests`

### Credentials
- `credential_audit_log`

---

## Prioritized Backlog

### P0 — Invoice Engine Phase 2 (Next)
- EDM e-document integrator adapter (issue, status, PDF download, cancel)
- Tenant-based integrator credential management (AES-256 encrypted)
- Real e-Fatura / e-Arsiv issuing through EDM API
- Integrator test connection
- PDF generation and download

### P1 — Invoice Engine Phase 3
- Luca accounting sync adapter
- Customer creation in accounting system
- Invoice sync with retry
- Accounting sync status tracking
- Finance/accounting dashboard

### P2 — Invoice Engine Phase 4 & Backlog
- Logo / Parasut / Mikro accounting adapters
- Automation rules (auto-create invoice, auto-send PDF, auto-sync)
- Invoice reconciliation (booking vs invoice vs accounting)
- Customer billing profile reuse
- Tax breakdown visibility enhancement
- Currency breakdown display

### P3 — Platform Backlog
- Real supplier credential validation with live APIs
- Onboard first 3 pilot agencies
- Lead capture form for landing page
- Email automation for onboarding
- A/B test infrastructure
- Churn prediction
- PyMongo AutoReconnect fix
- LEGACY_ROLE_ALIASES cleanup

---

## Code Architecture (Invoice Engine)

```
backend/app/
├── domain/invoice/
│   ├── models.py           # Domain entities, builders
│   ├── state_machine.py    # State transitions, validation
│   ├── decision_engine.py  # e-Fatura/e-Arsiv decision
│   └── booking_transform.py # Booking → Invoice mapping
├── services/
│   ├── invoice_engine.py   # Core service layer
│   └── efatura/            # Existing provider layer (mock)
│       ├── service.py
│       └── provider.py
├── routers/
│   ├── invoice_engine.py   # New: /api/invoices/*
│   └── efatura.py          # Legacy: /api/efatura/*
frontend/src/
├── pages/
│   └── AdminEFaturaPage.jsx # Invoice Engine dashboard + wizard
├── components/
│   └── BookingDetailDrawer.jsx # "Faturayi Kes" button
```
