# PRD — Feature Capability Engine (Multi-Tenant ERP)

## Original Problem Statement
Build a modular multi-tenant SaaS ERP platform for travel agencies (B2B). The Feature Capability Engine gates module access per tenant based on plan/features.

## What's Implemented (Dec 2025)

### PROMPT A — Backend Feature Guards
- `require_b2b_feature(key)` — for B2B routes (uses `get_b2b_tenant_context`)
- `require_tenant_feature(key)` — for middleware-resolved routes (uses `request.state.tenant_id`)
- Guards applied to: `b2b_exchange.py`, `reports.py`, `crm_customers.py`, `inventory.py`

### PROMPT B — Tenant Features Endpoint
- `GET /api/tenant/features` — returns enabled features for current tenant

### PROMPT C — Frontend FeatureContext
- `FeatureContext.jsx`: React context with `useFeatures()` hook
- `FeatureProvider` wraps `AppShell`
- Menu items filtered by `hasFeature()` + `requiredFeature` field

### PROMPT D — Admin Feature Management API
- `GET /api/admin/tenants` — list tenants (with search)
- `GET /api/admin/tenants/{tenantId}/features` — admin get features
- `PATCH /api/admin/tenants/{tenantId}/features` — admin update features

### PROMPT E — Admin Tenant Feature UI
- `/app/admin/tenant-features` page with:
  - Left panel: Tenant list with search, status badges, ID copy
  - Right panel: Feature checkboxes (9 modules), plan templates (Starter/Pro/Enterprise)
  - Dirty state detection, reset, save with toast
- Admin nav entry: "Tenant Özellikleri"
- Config files: `featureCatalog.js`, `featurePlans.js`

### Earlier Work (B2B Phase 1)
- B2B Agency Network: listings, match requests, status transitions
- B2B UI: PartnerB2BNetworkPage, MatchRequestDetailDrawer
- Admin subtree guard, comprehensive integration tests

## Test Coverage
- 23 backend integration tests passing (13 B2B + 10 feature flags)
- Frontend UI tested via Playwright: tenant selection, feature toggle, plan templates, save/reset, access control

## Key Files
- `backend/app/security/feature_flags.py`
- `backend/app/routers/tenant_features.py`, `admin_tenant_features.py`
- `backend/app/services/feature_service.py`
- `frontend/src/pages/admin/AdminTenantFeaturesPage.jsx`
- `frontend/src/contexts/FeatureContext.jsx`
- `frontend/src/config/featureCatalog.js`, `featurePlans.js`, `menuConfig.js`

## DB Schema
- `tenant_features`: `{ tenant_id (unique), plan, features[], created_at, updated_at }`

## Prioritized Backlog

### P1
- Observability (Phase 1.3): Event logging and metrics for B2B module
- Payment Orchestration Engine (iyzico escrow)

### P2
- Self-Service B2B Onboarding
- Real Paraşüt integration
- Data type migration: booking.amount float → decimal

### P3
- B2C Storefront/CMS/SEO Layer

## Credentials
- Admin: admin@acenta.test / admin123
- Agency: agency1@acenta.test / agency123
