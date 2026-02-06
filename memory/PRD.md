# PRD — Feature Capability Engine (Multi-Tenant ERP)

## Original Problem Statement
Build a modular multi-tenant SaaS ERP platform for travel agencies (B2B). The Feature Capability Engine gates module access per tenant based on plan/features. Implementation is divided into 4 phases (PROMPT A–D).

## Core Requirements
1. **Tenant-level feature gating**: Each tenant has a `tenant_features` collection controlling which modules (B2B, CRM, Reports, etc.) they can access.
2. **Backend guards**: FastAPI dependencies that check features before allowing endpoint access.
3. **Frontend integration**: React context + dynamic menu filtering based on enabled features.
4. **Admin management**: Admin UI/API for managing tenant features.

## Architecture
- **Backend**: FastAPI + MongoDB, Repository Pattern, Multi-Tenant via `TenantResolutionMiddleware`
- **Frontend**: React + React Router + Shadcn UI
- **Feature Engine**: `tenant_features` collection → `FeatureService` → guards (`require_b2b_feature`, `require_tenant_feature`)

## What's Implemented (Dec 2025)

### PROMPT A — Backend Feature Guards ✅
- `backend/app/security/feature_flags.py`: Two guard factories
  - `require_b2b_feature(key)` — for B2B routes (uses `get_b2b_tenant_context`)
  - `require_tenant_feature(key)` — for middleware-resolved routes (uses `request.state.tenant_id`)
- Guards applied to: `b2b_exchange.py`, `reports.py`, `crm_customers.py`, `inventory.py`
- `backend/app/constants/features.py`: ALL_FEATURE_KEYS list
- `backend/app/repositories/tenant_feature_repository.py`: Mongo repository
- `backend/app/services/feature_service.py`: Service layer

### PROMPT B — Tenant Features Endpoint ✅
- `GET /api/tenant/features` — returns enabled features for current tenant

### PROMPT C — Frontend FeatureContext ✅
- `frontend/src/contexts/FeatureContext.jsx`: React context with `useFeatures()` hook
- `FeatureProvider` wraps `AppShell`
- `legacyNav` items have `requiredFeature` field
- Menu items are filtered by `hasFeature()` during render
- `filterMenuByFeatures()` utility in `menuConfig.js`

### PROMPT D — Admin Feature Management ✅
- `GET /api/admin/tenants/{tenantId}/features` — admin get features
- `PATCH /api/admin/tenants/{tenantId}/features` — admin update features
- Validates feature keys against `ALL_FEATURE_KEYS`
- Admin endpoints whitelisted from `TenantResolutionMiddleware`

### Earlier Work (B2B Phase 1) ✅
- B2B Agency Network: listings, match requests, status transitions
- B2B UI: PartnerB2BNetworkPage, MatchRequestDetailDrawer
- Admin subtree guard for `/app/admin/*`
- Comprehensive integration tests (13 B2B tests)

## Test Coverage
- 23 integration tests passing (13 B2B + 10 feature flags)
- Tests cover: feature guard enforcement, feature CRUD, admin RBAC, B2B exchange flow

## DB Schema
- `tenant_features`: `{ tenant_id: string (unique), plan: string, features: string[], created_at, updated_at }`

## Key Files
- `backend/app/security/feature_flags.py`
- `backend/app/routers/tenant_features.py`
- `backend/app/routers/admin_tenant_features.py`
- `backend/app/services/feature_service.py`
- `backend/app/constants/features.py`
- `frontend/src/contexts/FeatureContext.jsx`
- `frontend/src/config/menuConfig.js`
- `frontend/src/components/AppShell.jsx`

## Prioritized Backlog

### P0
- (none — current sprint complete)

### P1
- Admin UI page for managing tenant features (frontend form with checkboxes)
- Observability (Phase 1.3): Event logging and metrics for B2B module

### P2
- Payment Orchestration Engine (iyzico escrow)
- Self-Service B2B Onboarding
- Real Paraşüt integration
- Data type migration: booking.amount float → decimal

### P3
- B2C Storefront/CMS/SEO Layer

## Credentials
- Admin: admin@acenta.test / admin123
- Agency: agency1@acenta.test / agency123
