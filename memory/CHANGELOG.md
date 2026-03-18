# Changelog

## 2026-03-18 (Session 2)

### Orphan Order Organization Recovery (P1 — Data Integrity) — COMPLETE
- Created production-grade, evidence-based two-phase migration script: `scripts/orphan_order_migration.py`
- Phase 1 (Analyze): 8 evidence strategies with CTO-specified confidence levels:
  - agency_direct (1.0), tenant_direct (0.95), invoice_chain (0.95)
  - demo_seed_single_org (0.9), customer_exact_match (0.9)
  - created_by_user_org (0.7), test_artifact_single_org (0.7)
  - legacy_org_id_single_org (0.4)
- Phase 2 (Apply): Only auto-fixes >=0.9 confidence with approved strategies
- Decision matrix: auto_fix / manual_review / quarantine / unresolved
- Rollback by batch_id supported with full audit trail
- 8 demo_seed orders auto-applied (confidence 0.9)
- 78 test/legacy orders quarantined for manual review (37 test artifacts + 41 legacy)
- Admin API: 6 endpoints for monitoring, audit, quarantine review
- Audit collection: `tenant_migration_audit` (full evidence chain per record)
- Quarantine collection: `tenant_migration_quarantine` (manual approve/reject workflow)
- 38 tests passing (26 API + 12 unit, 100% pass rate)

## 2026-03-18

### Tenant Isolation Hardening (P0 #3) — COMPLETE
- Created `app/modules/tenant/` module with full enforcement layer
- `TenantScopedRepository`: base class enforcing organization_id in all queries (find/update/delete/aggregate/insert)
- `TenantContext`: FastAPI dependency for strict tenant context injection
- Cross-tenant access detection: `TenantFilterBypassAttempt` exception (logged as CRITICAL)
- Admin bypass whitelist: 14 global collections, 32 tenant-scoped collections
- Admin API: health check, violation viewer, index enforcer, orphan finder, scope summary
- Exception handlers: TenantIsolationError → 403 responses
- Hardened `base_repository.py`: `with_org_filter` now rejects cross-tenant override, `with_tenant_filter` defaults strict
- `organization_id` indexes created on 11 previously unindexed collections
- Health score: 96.9% (only `orders` collection has orphaned documents)
- 41 unit tests + 13 API tests = 54 total, 100% pass rate

## 2026-02-25

### Unified Booking State Machine (P0 #1) — COMPLETE
- Created `app/modules/booking/` module with canonical state model
- States: DRAFT → QUOTED → OPTIONED → CONFIRMED → COMPLETED → CANCELLED → REFUNDED
- Separate fulfillment_status (NONE/TICKETED/VOUCHERED/BOTH) and payment_status tracks
- Command-based transitions: quote, option, confirm, cancel, complete, mark-ticketed, mark-vouchered, mark-refunded
- Optimistic locking with version field (409 Conflict on concurrent writes)
- Full history tracking in booking_history collection
- Event outbox in outbox_events collection (pending → for future consumers)
- Policy validation layer (business rules separate from state machine)
- Legacy state migration script (7 bookings migrated successfully)
- Backward-compatible shims for old imports (with deprecation warnings)
- 25 unit tests passing + 29 API integration tests (54 total, 100% pass rate)

### Router Domain Consolidation Phase 1 (P0 #2) — COMPLETE
- Created 10 domain aggregate modules under `app/modules/`
  - auth, identity, b2b, supplier, finance, crm, operations, enterprise, system, booking
- New domain-based registry: `app/bootstrap/domain_router_registry.py`
- 115 routers consolidated into domain aggregates
- 119 remaining routers organized into clear sections
- Old registry preserved as reference (app/bootstrap/router_registry.py)
- All endpoints verified working — zero breaking changes
- Router Domain Manifest created at `/app/backend/ROUTER_DOMAIN_MANIFEST.md`
