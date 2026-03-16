# Syroce Changelog

## 2026-03-16 — OMS Phase 2: Financial Linkage
- Implemented Order → Ledger → Settlement chain
- Auto-post to ledger on order confirm (double-entry: agency receivable, supplier payable, platform revenue)
- Auto-reverse ledger entries on order cancel
- Settlement run linkage endpoint
- Financial status tracking: not_posted → posted → partially_settled → settled → reversed
- Enhanced financial summary with 5 metrics
- 3 new backend services (financial_linkage, ledger_query, settlement_query)
- 8 new API endpoints
- Frontend: Ledger Entries table, Settlement card, Financial Status badges
- **Test**: 36/36 passed (iteration 138-139)

## 2026-03-16 — OMS Phase 1 Improvements
- Order Number Strategy: ORD-YYYY-NNNNNN format
- Order Search Endpoint: GET /api/orders/search with 10+ filters
- Optimistic Locking: version field, 409 Conflict on mismatch
- **Test**: 25/25 passed (iteration 138)

## Previous — OMS Phase 1: Order Core Layer
- Order CRUD, state machine, event sourcing
- 4 core services: order_service, order_transition_service, order_event_service, order_mapping_service
- Orders list and detail pages
- **Test**: 23/23 passed (iteration 137)
