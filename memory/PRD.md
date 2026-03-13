# Syroce — Travel Platform PRD

## Original Problem Statement
Enterprise Travel Agency SaaS + Multi-Supplier Distribution Engine + Revenue Optimization + Platform Scalability + Live Operations + Market Launch & First Customers.

## Core Architecture
```
supplier adapters → aggregator → unified search (cached) → unified booking
→ commission binding → fallback → reconciliation → analytics → intelligence
→ revenue optimization → scalability → operations → market launch
→ per-agency supplier credential management
```

## Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123

---

## Completed Phases

### Phase 1-4: Foundation
Unified Booking, Fallback, Commercial UX, Intelligence, Revenue Optimization

### Phase 5: Scalability (MEGA PROMPT #26)
Search Caching, Commission Binding, Rate Limiting, Job Scheduler, Prometheus, Multi-Currency, Tax

### Phase 6: Operations (MEGA PROMPT #27)
Validation Framework, Capability Matrix, Cache/Fallback/Rate Limit Tests, Launch Readiness

### Phase 7: Market Launch (MEGA PROMPT #28) — Mar 13, 2026
Pilot Agency Tracking, Usage Metrics, Feedback System, SaaS Pricing, Launch Dashboard

### Phase 8: Per-Agency Supplier Credential Management — Mar 13, 2026

**Backend:**
- AES-256 encrypted credential storage (Fernet)
- Supplier-specific field validation (WWTatil, Paximum, RateHawk, TBO)
- CRUD endpoints for agencies (own) and admin (any agency)
- Real supplier API connection testing
- Enable/Disable toggle with test-gate (must PASS before enabling)
- Credential audit logging (save, test, enable, disable, delete)
- Token caching per supplier per agency
- Masked credential display (****1234)

**RBAC:**
- super_admin: manage ALL agencies' credentials
- agency_admin: manage only own tenant credentials
- 403 enforcement on admin endpoints

**Frontend:**
- AdminSupplierCredentialsPage: agencies list + audit log tabs
- Agency detail view: 4 supplier cards with supplier-specific forms
- Masked sensitive fields, Test/Edit/Enable/Disable/Remove actions
- SupplierSettingsTab (agency self-service): updated with enable/disable

**DB Collections:**
- `supplier_credentials`: per-agency encrypted credentials with status
- `supplier_tokens`: cached authentication tokens per supplier
- `credential_audit_log`: action audit trail

---

## Key API Endpoints

### Supplier Credentials (Phase 8 — NEW)
- `GET /api/supplier-credentials/supported` — List supported suppliers + fields
- `GET /api/supplier-credentials/my` — Own agency credentials (masked)
- `POST /api/supplier-credentials/save` — Save credentials for own agency
- `DELETE /api/supplier-credentials/{supplier}` — Delete own credential
- `POST /api/supplier-credentials/test/{supplier}` — Test connection
- `PUT /api/supplier-credentials/toggle/{supplier}` — Enable/Disable
- `GET /api/supplier-credentials/admin/agencies` — All agencies summary (super_admin)
- `GET /api/supplier-credentials/admin/agency/{org_id}` — Agency credentials (super_admin)
- `POST /api/supplier-credentials/admin/agency/{org_id}/save` — Save for agency (super_admin)
- `DELETE /api/supplier-credentials/admin/agency/{org_id}/{supplier}` — Delete for agency
- `PUT /api/supplier-credentials/admin/agency/{org_id}/toggle/{supplier}` — Toggle for agency
- `GET /api/supplier-credentials/admin/audit-log` — Audit log with optional org filter

---

## Prioritized Backlog

### P0 — Real Operations
- Real supplier credential validation with live APIs
- Shadow traffic activation
- Revenue forecasting

### P1 — MEGA PROMPT #29: Growth Engine
- Agency acquisition funnel
- Referral system
- Supplier expansion
- Growth analytics

### P2 — Backlog
- PyMongo AutoReconnect fix
- Secret rotation & expiry alerts
- Credential health dashboard
- Multi-region deployment
- White-label support
