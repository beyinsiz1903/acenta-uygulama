# PRD — SaaS Billing & Plan Engine (Multi-Tenant ERP)

## Original Problem Statement
Build a modular multi-tenant SaaS ERP with Plan Inheritance + Billing Abstraction for travel agencies.

## What's Implemented

### PROMPT A–E: Feature Capability Engine ✅
### PROMPT F: Observability + Audit Log ✅
### PROMPT G: Plan Inheritance Engine ✅
- Plan Matrix (starter/pro/enterprise), tenant_capabilities, effective_features = plan_defaults + add_ons

### PROMPT H: Billing Abstraction + Subscription Mapping ✅
- **BillingProvider ABC**: Provider-agnostic interface (create_customer, create/update/cancel_subscription)
- **StripeBillingProvider**: Real Stripe SDK implementation
- **IyzicoBillingProvider**: Stub with capabilities flags (subscriptions=False)
- **SubscriptionManager**: Orchestrates plan changes through provider → tenant_capabilities
- **Billing Repository**: 4 collections (billing_customers, billing_subscriptions, billing_plan_catalog, billing_webhook_events)
- **Webhook Engine**: Stripe webhook with idempotency (billing_webhook_events dedup)
  - Handles: invoice.paid, subscription.updated/deleted, payment_failed
  - Grace period (7 days) on payment failure instead of immediate freeze
- **Plan Catalog**: DB-seeded pricing (Starter ₺499, Pro ₺999, Enterprise ₺2499/mo)
- **Admin API**: subscribe, cancel, downgrade-preview, plan-catalog, plan-catalog/seed
- **Audit**: All billing actions logged to audit_logs

## DB Collections
| Collection | Purpose |
|---|---|
| tenant_capabilities | Plan + add_ons per tenant |
| billing_customers | Provider customer mapping |
| billing_subscriptions | Active subscriptions (status, period_end, grace_period) |
| billing_plan_catalog | Plan pricing (plan, interval, currency, provider_price_id) |
| billing_webhook_events | Webhook idempotency (provider_event_id unique) |
| audit_logs | All admin + billing actions |
| b2b_events | B2B lifecycle events |

## Key API Endpoints
| Endpoint | Auth | Purpose |
|---|---|---|
| PATCH /api/admin/tenants/{id}/plan | admin | Set plan |
| PATCH /api/admin/tenants/{id}/add-ons | admin | Set add-ons |
| POST /api/admin/billing/tenants/{id}/subscribe | admin | Create/update subscription |
| POST /api/admin/billing/tenants/{id}/cancel-subscription | admin | Cancel subscription |
| POST /api/admin/billing/tenants/{id}/downgrade-preview | admin | Preview feature loss |
| POST /api/admin/billing/plan-catalog/seed | super_admin | Seed prices |
| POST /api/webhook/stripe-billing | public | Stripe webhooks |

## Test Coverage
- 34+ backend integration tests across: B2B, feature flags, plan inheritance, billing
- Frontend UI tested via testing agent

## Prioritized Backlog
### P1
- Admin UI: subscription status + billing panel on tenant features page
- Usage-based billing hooks (b2b.match_request metered)
### P2
- Real Stripe Products/Prices creation (currently using seed IDs)
- Self-Service B2B Onboarding
### P3
- Escrow & Payment Orchestration (B2B transaction fees)
- B2C Storefront/CMS/SEO Layer

## Credentials
- Admin: admin@acenta.test / admin123
- Agency: agency1@acenta.test / agency123
