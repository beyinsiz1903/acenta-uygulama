# Roadmap — Travel Distribution SaaS

## COMPLETED
- [x] P0 #1: Booking Truth Model
- [x] P0 #2: Tenant Isolation Hardening
- [x] P0 #3: Orphan Order Recovery (Evidence-Based Migration)
- [x] P0 #4: Celery + Redis + Outbox Consumer (5 First-Wave Consumers)
- [x] Outbox Consumer Hardening (EventPublisher, Idempotency, DLQ Visibility)
- [x] API Response Standardization (Envelope Middleware)
- [x] API Versioning (/api/v1/ Path Rewrite)
- [x] P0.5: Webhook System Productization (Subscription CRUD, HMAC, Retry, Circuit Breaker, Admin)

## P1 — Next Sprint
- [ ] Router Consolidation Phase 2 (physical merge into domain modules)
- [ ] Event-Driven Core Expansion (more domain workers/events)
- [ ] Cache Strategy Definition & Implementation (L0/L1/L2)

## P2 — Future
- [ ] Product Packaging (Core/Pro/Enterprise tiers)
- [ ] New Supplier Adapters (Hotelbeds, Juniper)
- [ ] Frontend Persona Separation (sales/ops/finance views)
- [ ] Enterprise SLA Monitoring
- [ ] Rate Limiting Enhancement (per-tenant)

## Known Debt
- [ ] yarn.lock frontend dependency mismatch (recurring, P3)
