# Roadmap — SaaS Platform

## Completed ✅

### Foundation (PROMPT A–E)
- Feature Capability Engine: guards, FeatureContext, Admin UI, Plan + Add-on model

### Observability (PROMPT F)
- Audit logs, B2B events, Activity timeline, Admin audit page

### Plan Inheritance (PROMPT G)
- plan_defaults + add_ons = effective_features, tenant_capabilities collection

### Billing Core (PROMPT H)
- BillingProvider ABC (Stripe + Iyzico stub)
- SubscriptionManager, Webhook engine (idempotent), Plan catalog (DB seeded)
- Subscription visibility UI

### Usage & Monetization
- Usage ledger (idempotent), Quota logic (soft enforcement)
- In-app quota notification banners
- Stripe metered push (shadow mode)
- Stripe product provisioning (4 guardrails)
- Revenue analytics dashboard (MRR, plan distribution, quota buckets, enterprise candidates)

### Operations
- Period finalize job (lock, reconciliation)
- APScheduler cron (monthly, Europe/Istanbul)
- Billing ops widget (push status, finalize history)
- Slack billing alerts (best-effort)

---

## In Progress 🟡

### Shadow Cycle Observation
- Collecting usage data for 1 full billing cycle
- Monitoring: push errors, finalize reconciliation, quota distribution
- Decision framework documented in `docs/billing/overage-migration.md`

---

## Upcoming 🟠

### Active Overage Pricing
- Real metered price creation in Stripe
- Quota-aware push (only bill above free tier)
- Phased rollout: new subs → opt-in → full
- See: `docs/billing/overage-migration.md`

### Usage Email Notifications
- Monthly summary email (usage, quota, overage amount)
- >80% quota warning email
- >100% exceeded notification

---

## Future 🔴

### Escrow & Payment Orchestration (PRE-DESIGN COMPLETE)
- Domain model designed: `docs/escrow/escrow-domain-design.md`
- 6 entities: EscrowTransaction, EscrowAccount, Settlement, FeeAllocation, DisputeCase
- State machine: pending_funding → funded → service_confirmed → releasing → released
- Financial model: gross - platform_fee - provider_commission = net_seller
- 3-phase implementation: Core MVP → Operations → Advanced
- Decision: Stripe Connect recommended for V1
- **Next**: Legal review (BDDK) → Phase 1 implementation

### Self-Service B2B Onboarding
- Tenant self-registration
- Plan selection + Stripe checkout
- Auto-provisioning

### B2C Storefront/CMS/SEO Layer
- Public-facing storefront
- CMS pages
- SEO optimization

---

## Technical Debt (Low Priority)
- Replace seed Stripe price IDs with real provisioned IDs
- Stripe real Products for all plan/interval combinations
- Remove legacy tenant_features collection (after full migration)
- Pre-aggregate usage data for performance (if ledger grows large)
