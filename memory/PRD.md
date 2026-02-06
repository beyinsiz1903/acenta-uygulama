# PRD — Plan Inheritance Engine (Multi-Tenant ERP)

## Original Problem Statement
Build a modular multi-tenant SaaS ERP with Plan Inheritance: plan_defaults + add_ons = effective_features.

## What's Implemented

### PROMPT A–E: Feature Capability Engine ✅
- Backend guards, tenant features endpoint, FeatureContext, Admin UI, Tenant Feature Management

### PROMPT F: Observability + Audit Log ✅
- `audit_logs` + `b2b_events` collections, admin audit page, activity timeline in drawer

### PROMPT G: Plan Inheritance Engine ✅
- **Plan Matrix** (`constants/plan_matrix.py`): starter (5), pro (8), enterprise (10 modules)
- **Tenant Capabilities** (`tenant_capabilities` collection): `{ tenant_id, plan, add_ons }`
- **Effective Features** = plan_defaults + add_ons (via `FeatureService.get_effective_features`)
- **Soft-Deprecate**: Falls back to legacy `tenant_features` when no capabilities doc exists
- **Admin API**: `PATCH /plan`, `PATCH /add-ons` with validation + audit logging
- **Admin UI**: Plan dropdown + Add-on checkbox grid, plan features disabled with "Plan" badge
- **Migration Script**: `scripts/migrate_tenant_features_to_capabilities.py`

## DB Collections
- `tenant_capabilities`: `{ tenant_id (unique), plan, add_ons[], created_at, updated_at }`
- `tenant_features`: Legacy (soft-deprecated, fallback read)
- `audit_logs`: `{ id, scope, tenant_id, actor_*, action, before, after, metadata, created_at }`
- `b2b_events`: `{ id, event_type, entity_type, entity_id, payload, created_at }`

## Plan Matrix
| Plan | Modules |
|---|---|
| Starter | dashboard, reservations, crm, inventory, reports |
| Pro | + accounting, webpos, partners |
| Enterprise | + b2b, ops |

## Test Coverage
- 34 backend integration tests (13 B2B + 12 feature flags + 8 plan inheritance + 1 audit)

## Key API Endpoints
- `PATCH /api/admin/tenants/{id}/plan` — Set plan (starter/pro/enterprise)
- `PATCH /api/admin/tenants/{id}/add-ons` — Set add-on modules
- `GET /api/admin/tenants/{id}/features` — Get effective features + plan_matrix
- `GET /api/tenant/features` — Tenant self-service (effective features + source)

## Prioritized Backlog
### P1
- Usage-based billing hooks
- Stripe/Iyzico subscription mapping
### P2
- Self-Service B2B Onboarding, Real Paraşüt integration
### P3
- B2C Storefront/CMS/SEO Layer

## Credentials
- Admin: admin@acenta.test / admin123
- Agency: agency1@acenta.test / agency123
