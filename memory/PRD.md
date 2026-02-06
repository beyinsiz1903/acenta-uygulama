# PRD — Feature Capability Engine + Observability (Multi-Tenant ERP)

## Original Problem Statement
Build a modular multi-tenant SaaS ERP platform for travel agencies (B2B). The Feature Capability Engine gates module access per tenant based on plan/features. Observability layer provides audit logging and event tracking.

## What's Implemented

### PROMPT A — Backend Feature Guards ✅
- `require_b2b_feature(key)` / `require_tenant_feature(key)` guards
- Applied to: `b2b_exchange.py`, `reports.py`, `crm_customers.py`, `inventory.py`

### PROMPT B — Tenant Features Endpoint ✅
- `GET /api/tenant/features`

### PROMPT C — Frontend FeatureContext ✅
- `FeatureContext.jsx` + `useFeatures()` hook + dynamic menu filtering

### PROMPT D — Admin Feature Management API ✅
- `GET /api/admin/tenants` (list + search)
- `GET/PATCH /api/admin/tenants/{tenantId}/features`

### PROMPT E — Admin Tenant Feature UI ✅
- `/app/admin/tenant-features` — checkbox grid + plan templates (Starter/Pro/Enterprise)

### PROMPT F — Observability + Audit Log ✅
- **Audit Logs**: `audit_logs` collection, `audit_log_repository.py`, `audit_log_service.py`
  - Feature update PATCH writes `tenant_features.updated` with before/after state
  - `GET /api/admin/audit-logs` — admin-only, filterable by tenant_id/action, cursor pagination
- **B2B Events**: `b2b_events` collection, `b2b_event_repository.py`, `b2b_event_service.py`
  - Events: `listing.created`, `listing.updated`, `match_request.created`, `match_request.status_changed`
  - `GET /api/b2b/events` — tenant-scoped, feature guarded, filterable
  - All event writes are best-effort (try/catch, never blocks core flow)
- **Admin Audit Log Page**: `/app/admin/audit-logs` — filters, diff summary, "Daha fazla yükle"
- **Activity Timeline**: `MatchRequestDetailDrawer` → "Aktivite" section shows B2B events

### Earlier Work (B2B Phase 1) ✅
- B2B Agency Network, MatchRequestDetailDrawer, Admin subtree guard

## Test Coverage
- 27 backend integration tests passing (13 B2B + 12 feature flags/audit)
- Frontend UI tested via testing agent: all features verified

## Key Files
- `backend/app/repositories/audit_log_repository.py`, `b2b_event_repository.py`
- `backend/app/services/audit_log_service.py`, `b2b_event_service.py`
- `backend/app/routers/admin_audit_logs.py`, `b2b_events.py`
- `frontend/src/pages/admin/AdminAuditLogPage.jsx`
- `frontend/src/pages/partners/components/MatchRequestDetailDrawer.jsx` (ActivityTimeline)

## DB Collections
- `tenant_features`: `{ tenant_id (unique), plan, features[], created_at, updated_at }`
- `audit_logs`: `{ id, scope, tenant_id, actor_*, action, before, after, metadata, created_at }`
- `b2b_events`: `{ id, event_type, entity_type, entity_id, listing_id, *_tenant_id, actor_*, payload, created_at }`

## Event Types (B2B)
| event_type | entity_type | payload |
|---|---|---|
| listing.created | listing | title, base_price, status |
| listing.updated | listing | title, base_price, status |
| match_request.created | match_request | requested_price, currency |
| match_request.status_changed | match_request | from, to, requested_price, platform_fee_amount |

## Prioritized Backlog
### P1
- Payment Orchestration Engine (iyzico escrow)
- ERP modül haritası + plan matrisi (müşteri segmentlerine göre)
### P2
- Self-Service B2B Onboarding
- Real Paraşüt integration
### P3
- B2C Storefront/CMS/SEO Layer

## Credentials
- Admin: admin@acenta.test / admin123
- Agency: agency1@acenta.test / agency123
