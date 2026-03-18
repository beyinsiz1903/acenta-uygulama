# Changelog

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
