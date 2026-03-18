# Roadmap — Travel Distribution SaaS

## COMPLETED
- [x] P0 #1: Booking Truth Model
- [x] P0 #2: Tenant Isolation Hardening
- [x] P0 #3: Orphan Order Recovery (Evidence-Based Migration)
- [x] P0 #4: Celery + Redis + Outbox Consumer (5 First-Wave Consumers)

## P1 — Next Sprint
- [ ] Event-Driven Core Expansion (more domain workers/events)
- [ ] API Response Standardization (envelope, pagination, trace IDs)
- [ ] Router Consolidation Phase 2 (physical merge into domain modules)
- [ ] Cache Strategy Definition & Implementation (L0/L1/L2)

## P2 — Future
- [ ] Product Packaging (Core/Pro/Enterprise tiers)
- [ ] API Versioning (/api/v1/)
- [ ] Webhook Management UI (frontend)
- [ ] New Supplier Adapters (Hotelbeds, Juniper)
- [ ] Frontend Persona Separation (sales/ops/finance views)
- [ ] Enterprise SLA Monitoring

## Known Debt
- [ ] yarn.lock frontend dependency mismatch (recurring, P3)
