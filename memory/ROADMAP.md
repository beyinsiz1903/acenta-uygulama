# Roadmap — Travel Distribution SaaS

## 30-Day Plan (Hafta 1-4)

### Hafta 1-2 (DONE)
- [x] Booking State Machine Unification
- [x] Router Domain Consolidation Phase 1
- [x] Tenant Isolation Hardening

### Hafta 3
- [ ] Celery + Redis async queue setup
- [ ] Outbox consumer workers (email, billing, notification)
- [ ] Event dispatch table + retry/dead-letter

### Hafta 4
- [ ] API Response standardization
- [ ] Router Consolidation Phase 2 (admin, inventory, public)
- [ ] /api/v1/ versioning plan

## 60-Day Plan (Ay 2)
- [ ] Cache strategy (L0 memory, L1 Redis, L2 DB)
- [ ] API versioning (/api/v1/)
- [ ] Router Consolidation Phase 3 (merge files per domain)
- [ ] New supplier adapters (Hotelbeds)
- [ ] Supplier Quote Comparator

## 90-Day Plan (Ay 3)
- [ ] Webhook system
- [ ] Audit log hash-chain
- [ ] Product packaging (Core/Pro/Enterprise)
- [ ] Frontend persona separation (sales/ops/finance)
- [ ] Settlement automation

## Backlog / P2
- yarn.lock inconsistency fix
- Full regression test suite
- Juniper supplier adapter
- Enterprise SLA monitoring
