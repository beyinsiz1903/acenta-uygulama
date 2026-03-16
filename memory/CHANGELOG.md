# Syroce Travel SaaS - Changelog

## 2026-03-16 — Cache Alert, Warming & Global Diagnostics
### Added
- **Cache Hit Rate Alert**: Auto-alert when hit_rate < 70% threshold after 10+ requests
  - GET `/api/pricing-engine/cache/alerts` - Active alerts + history
  - POST `/api/pricing-engine/cache/alerts/clear` - Clear alert history
  - Frontend amber alert banner with ALERT badge in cache stats bar
- **Pricing Cache Warming**: Precompute pricing for popular routes
  - POST `/api/pricing-engine/cache/warm/{supplier}` - Warm cache per supplier
  - GET `/api/pricing-engine/cache/popular-routes` - View tracked popular routes
  - Auto-warm after supplier sync (inventory_sync_service.py hooks)
  - Per-supplier warming button (Flame icon) in telemetry panel
- **Global Cache Diagnostics**: Comprehensive scaling metrics
  - GET `/api/pricing-engine/cache/diagnostics` - Full diagnostic report
  - Metrics: global_hit_rate, total_entries, memory_usage_mb, evictions, utilization_pct, uptime, supplier_count
  - Frontend diagnostics panel with 6 metric cards
- Enhanced cache stats bar with Evictions and Memory fields
- Testing: 35 backend + 15 frontend tests passed (iteration_131)

### Modified
- `backend/app/services/pricing_distribution_engine.py` - PricingCache: alert system, query tracking, memory estimation, eviction counting
- `backend/app/routers/pricing_engine_router.py` - 5 new endpoints (alerts, diagnostics, warming, popular-routes)
- `backend/app/services/inventory_sync_service.py` - Post-sync cache warming hooks
- `frontend/src/pages/PricingEnginePage.jsx` - Alert banner, diagnostics panel, warming buttons

## 2026-03-16 — Cache Telemetry & Cache Invalidation
- Extended cache metrics: per-supplier breakdown, latency tracking, invalidation log
- Supplier-aware invalidation: automatic clearing on sync and price changes
- 19 backend + 10 frontend tests (iteration_130)

## 2026-03-16 — Pricing Trace ID & Pricing Cache
- Trace ID (prc_xxxxxxxx) for debugging, In-memory TTL cache (300s, 5000 max)
- 21 backend + 15 frontend tests (iteration_129)

## 2026-03-16 — Pricing Engine Enhancements
- Pricing Explainability, Rule Precedence, Margin Guardrails
- 17 backend + 12 frontend tests (iteration_128)

## 2026-03-16 — Pricing & Distribution Engine
- 7-step pricing pipeline, Channel pricing, Rule engine, Promotion layer, Price Simulator
- 23 backend + 9 frontend tests (iteration_127)
