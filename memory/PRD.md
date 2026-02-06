# PRD — SaaS Platform (Multi-Tenant ERP)

## Platform Status: Production-Grade Hybrid Revenue SaaS

### Implemented Stack

**Feature Engine (PROMPT A–E)**
- Feature guards (require_b2b_feature, require_tenant_feature)
- FeatureContext + dynamic menu filtering
- Admin tenant features UI (plan dropdown + add-on grid)

**Observability (PROMPT F)**
- Audit logs (all admin + billing actions)
- B2B event logging (listing, match_request, status changes)
- Activity timeline in MatchRequestDetailDrawer
- Admin audit log page with filters

**Plan Inheritance (PROMPT G)**
- tenant_capabilities: plan + add_ons = effective_features
- Soft-deprecate: legacy tenant_features fallback
- Plan matrix: starter (5), pro (8), enterprise (10 modules)

**Billing & Subscription (PROMPT H)**
- BillingProvider ABC (Stripe real + Iyzico stub)
- SubscriptionManager: subscribe, cancel, downgrade-preview
- Stripe webhook engine (idempotent)
- Plan catalog (DB seeded, super_admin API)
- Subscription visibility UI (status badges, grace period, renewal countdown)

**Usage & Monetization**
- Usage ledger (idempotent, source_event_id unique)
- Quota logic (soft enforcement, audit on exceeded)
- In-app quota notification banners (>=80% warning, >=100% critical)
- Stripe metered push (shadow mode, ₺0/unit)
- Stripe product provisioning (4 guardrails: mode gate, idempotency, dry_run, audit)

**Revenue Analytics**
- MRR (gross + at_risk), plan distribution
- Quota bucket distribution (0-20%, 20-50%, 50-80%, 80-100%, 100%+)
- Enterprise candidate heuristic
- MRR trend chart (3-month lookback)
- Billing ops widget (push status, finalize history, cron status)

**Operations**
- Period finalize job (lock, reconciliation, partial failure safe)
- APScheduler cron (monthly, Europe/Istanbul)
- Slack billing alerts (best-effort, severity-based emoji)

### Test Coverage
- 63+ backend integration tests

### Strategic Documents
- `docs/billing/overage-migration.md` — Decision framework, pricing strategy, 3-phase rollout
- `docs/escrow/escrow-domain-design.md` — Domain model, state machine, financial flow, risk matrix
- `docs/escrow/legal-compliance-checklist.md` — Turkey regulation, Stripe Connect analysis, 10 critical questions, GO/NO-GO matrix

## Roadmap

### Blocked (External Dependency)
- Escrow Phase 1 — awaiting legal counsel opinion on BDDK scope

### Next (After Shadow Cycle)
- Active overage pricing (data-driven decision)
- Usage email notifications

### Future
- Escrow implementation (post legal clearance)
- Self-Service B2B Onboarding
- B2C Storefront/CMS/SEO Layer

## Credentials
- Admin: admin@acenta.test / admin123
- Agency: agency1@acenta.test / agency123
