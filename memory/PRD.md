# PRD — SaaS Platform (Multi-Tenant ERP)

## Implemented

### Feature Engine (A–E) ✅
### Observability (F) ✅
### Plan Inheritance (G) ✅
### Billing + Subscription (H) ✅
### Usage Tracking + Quota ✅
### Revenue Analytics Dashboard ✅
### In-App Quota Notification ✅
### MRR Trend Chart ✅
### Stripe Product Provisioning ✅

### Stripe Metered Billing Push ✅
- `UsagePushService`: usage_ledger → `stripe.SubscriptionItem.create_usage_record`
- Push tracking: pushed_at, stripe_usage_record_id, push_attempts, last_push_error
- Idempotency key: `usage:{tenant_id}:{metric}:{source_event_id}`
- Shadow mode: metered price ₺0/unit
- `POST /api/admin/billing/usage-push` — trigger push job
- `POST /api/admin/billing/tenants/{id}/setup-metered-item` — attach metered item to subscription

### Subscribe/Cancel UI ✅
- Cancel button in SubscriptionPanel (confirm dialog, cancel_at_period_end default)

## Test Coverage: 63 backend integration tests

## Backlog
### P1: Usage email notifications, Period finalize job (cron)
### P2: Escrow & Payment Orchestration
### P3: B2C Storefront/CMS/SEO Layer
