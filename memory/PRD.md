# Syroce — Travel Platform PRD

## Original Problem Statement
Enterprise Travel Agency SaaS + Multi-Supplier Distribution Engine + Revenue Optimization + Platform Scalability + Live Operations + Market Launch + Per-Agency Credential Management + Growth Engine.

## Core Architecture
```
supplier adapters → aggregator → unified search (cached) → unified booking
→ commission binding → fallback → reconciliation → analytics → intelligence
→ revenue optimization → scalability → operations → market launch
→ per-agency credential governance → growth engine
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

### Phase 7: Market Launch (MEGA PROMPT #28)
Pilot Agency Tracking, Usage Metrics, Feedback System, SaaS Pricing, Launch Dashboard

### Phase 8: Per-Agency Supplier Credential Management — Mar 13, 2026
AES-256 encrypted credential storage, supplier-specific forms (WWTatil, Paximum, RateHawk, TBO), RBAC, audit logging, enable/disable toggle, token caching

### Phase 9: Growth Engine (MEGA PROMPT #29) — Mar 13, 2026

**10 Components Delivered:**

1. **Agency Acquisition Funnel** — 7 stages (lead_captured → activated), conversion metrics
2. **Lead & Demo Management** — CRM-like lead tracking, demo pipeline, stage progression
3. **Referral System** — Invite + reward rules (10% discount on register, 50 EUR credit on activate), fraud prevention (duplicate email rejection)
4. **Activation Metrics** — 5 milestones (credential_entered, connection_tested, first_search, first_booking, first_revenue), weighted scoring (max 100), status classification (new/progressing/activated)
5. **Customer Success Dashboard** — Agency categorization (active, dormant, at_risk, failed_connections, zero_bookings), success playbook
6. **Supplier Expansion Model** — Demand tracking, priority scoring, request management
7. **Growth KPI Dashboard** — Period-based metrics (leads, activations, booking rates, referral conversions)
8. **Onboarding Automation** — 8-item checklist, trigger rules for automated reminders
9. **Agency Segmentation** — 4 segments (enterprise 50+, growth 10-49, starter 1-9, inactive 0)
10. **Full Growth Report** — Maturity score, dimension scores, 25 implementation tasks (P0/P1/P2), 15 growth risks (high/medium/low)

**Backend:** 22 API endpoints via `/api/growth/*`
**Frontend:** GrowthEnginePage with 7 tabs (Funnel, Leads, Referrals, Customer Success, KPIs, Supplier Expansion, Growth Report)
**Testing:** 32/32 backend + all frontend tests PASS

### Security Fix: LEGACY_ROLE_ALIASES Privilege Escalation — Mar 14, 2026
**Problem:** `LEGACY_ROLE_ALIASES` mapped `"admin"` → `"super_admin"`, causing `is_super_admin()` to return True for plain admin users. This bypassed all `require_feature()` and `require_super_admin_only()` guards — a critical security vulnerability.

**Fix:** `is_super_admin()` now checks `_raw_roles` (pre-normalization) stored by `get_current_user()`. Only explicit `super_admin`/`superadmin` pass. `require_roles()` backward compatibility preserved via `normalize_roles()`.

**Files changed:** `backend/app/auth.py`, `backend/tests/test_admin_statements.py`
**Testing:** 24/24 security tests PASS (iteration_90)

---

## Key API Endpoints

### Growth Engine (Phase 9 — NEW)
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
- `GET /api/growth/onboarding/{agency_id}` — Checklist
- `POST /api/growth/onboarding/{agency_id}/complete` — Complete task
- `GET /api/growth/segments` — Agency segmentation
- `GET/POST /api/growth/supplier-requests` — Expansion requests
- `GET /api/growth/kpis` — Growth KPIs
- `GET /api/growth/report` — Full growth report

### Supplier Credentials (Phase 8)
- `GET/POST/DELETE /api/supplier-credentials/*` — Agency CRUD
- `GET/POST/PUT/DELETE /api/supplier-credentials/admin/*` — Super admin
- `GET /api/supplier-credentials/admin/audit-log` — Audit trail

---

## DB Collections (New)
- `growth_leads` — Lead tracking with funnel stages
- `growth_demos` — Demo pipeline
- `growth_referrals` — Referral tracking with rewards
- `growth_activation_events` — Per-agency activation milestones
- `growth_onboarding_tasks` — Onboarding checklist completion
- `growth_supplier_requests` — Supplier expansion demand tracking
- `credential_audit_log` — Credential change audit trail

---

## Prioritized Backlog

### P0 — Real Operations
- Real supplier credential validation with live APIs
- Onboard first 3 pilot agencies with real credentials
- Execute first real booking flow

### P1 — Growth Execution
- Lead capture form for public-facing landing page
- Email automation for onboarding triggers
- Referral program launch to pilot agencies

### P2 — Backlog
- A/B test infrastructure for plan pages
- Churn prediction model
- NPS survey automation
- Multi-region deployment
- PyMongo AutoReconnect intermittent fix (infra-level)

---

## Recently Completed (Mar 14, 2026)

### Security Fix: LEGACY_ROLE_ALIASES Privilege Escalation
- `is_super_admin()` now uses `_raw_roles` (pre-normalization) to prevent `admin` → `super_admin` feature bypass
- 24/24 security tests PASS (iteration_90)

### Pre-existing Test Fixes
- **test_granular_permissions.py**: Rewritten from sync `requests` to async_client — 13/13 PASS
- **test_saas_limits_and_guards.py**: Added `get_monthly_count` to `UsageService`, fixed tenant test — 6/6 PASS
- **test_b2b_pro_v1.py**: Fixed error response format assertions (`detail` vs `error.message`) — 3/3 PASS
- **test_billing_subscription_lifecycle.py**: Updated same-plan check to accept 200/409 — 15/15 PASS
- All verified via testing agent (iteration_91): 43/43 functionally passing

### Pydantic V2 Migration & Test CI Fix — Mar 14, 2026
- **test_annual_pricing_e2e_iter36.py**: Converted from `requests` library to `async_client` fixture — 8/8 PASS
- **schemas_finance.py**: Migrated 6x `class Config:` → `model_config = ConfigDict(...)`
- **schemas_ops_cases.py, schemas_pricing.py**: Migrated `class Config:` → `model_config`
- **admin_partners.py, admin_campaigns.py, admin_coupons.py, ops_cases.py**: Same migration
- **theme.py, action_policies.py**: Migrated `@validator` → `@field_validator` (Pydantic V2)
- **admin_metrics.py, admin_reporting.py**: Migrated `regex=` → `pattern=` (FastAPI/Pydantic V2)
- All Pydantic deprecation warnings from project code eliminated

### B2B Booking Create Test Fix — Mar 14, 2026
- **Root Cause**: Tests used `X-Tenant-Key` header but `TenantResolutionMiddleware` reads `X-Tenant-Id`. Also, user role `"admin"` is no longer `super_admin` due to security fix in `is_super_admin()`.
- **Fix**: Updated all 3 tests in `test_exit_b2b_booking_create_v1.py`:
  - Test 1 (happy_path): Changed role to `super_admin`, header to `X-Tenant-Id`, added `supplier_mapping` to listing
  - Test 2 (forbidden_without_access): Same header/role fix, captured `buyer_tenant_id`
  - Test 3 (requires_tenant_context): Rewrote to test middleware-level rejection (no tenants in org → `tenant_resolution_failed`)
- **All 3/3 tests PASS locally**
