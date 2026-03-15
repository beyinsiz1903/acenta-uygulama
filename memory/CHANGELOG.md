# Syroce Changelog

## 2026-03-15 — Inventory Sync Engine (MEGA PROMPT #37)
- **Architecture Decision**: CTO approved Option B — Travel Inventory Platform (not API Aggregator)
- **Backend**: Created `inventory_sync_service.py` with full sync engine, cached search, revalidation
- **Backend**: Created `inventory_sync_router.py` with 6 API endpoints
- **Frontend**: Created `InventorySyncDashboardPage.jsx` with KPIs, sync controls, cached search
- **MongoDB**: 6 new collections (supplier_inventory, supplier_prices, supplier_availability, inventory_sync_jobs, inventory_index, inventory_revalidations)
- **Testing**: 28/28 backend tests PASS, 100% frontend verified
- **Key Metric**: Cached search latency ~1.7ms (vs 300ms+ from supplier API)

## 2026-03-15 — Supplier Response Diff (Previous Session)
- Implemented `supplier_response_diff` metric (search_price → revalidation_price → diff %)
- Added to pilot dashboard KPIs and simulation results
- 9/9 backend tests PASS, frontend 100% verified
- 10/10 simulation flows PASS

## Previous Sessions
- Pilot flow simulation system
- Pilot dashboard with Flow Health, Supplier Metrics, Finance Metrics
- Supplier adapters (Ratehawk, Paximum, WWTatil, TBO)
- Full travel ERP platform features
