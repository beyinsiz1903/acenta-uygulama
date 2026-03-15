# Syroce Travel Platform — Product Requirements Document

## Original Problem Statement
CTO-driven Travel ERP platform (Syroce) with multi-supplier booking engine, revenue engine, invoice engine, accounting sync, finance ops, growth engine, pilot validation, and supplier drift monitoring. The platform is transitioning from a **Travel API Aggregator** to a **Travel Inventory Platform** (CTO decision — Option B).

## Core Architecture Decision (MEGA PROMPT #37)
**Travel Inventory Platform** — Enterprise architecture pattern used by Booking.com, Expedia, Travelport:
```
Supplier API → Inventory Sync Engine → MongoDB → Redis Cache → Search Engine
Search → Cache (NOT supplier API)
Booking → Supplier API (revalidation with diff tracking)
```

## Sandbox Architecture (MEGA PROMPT #38)
**Config-Driven Supplier Integration** — Sandbox-ready adapter pattern:
```
Credential Check → Has Credentials? → Real API (sandbox/production)
                 → No Credentials?  → Simulation Mode (if allowed)
                 → Simulation Disabled? → Error (production guard)
```
- Credentials stored in `supplier_credentials` MongoDB collection
- Each supplier independently configurable (mode, base_url, key_id, api_key)
- Validation tests run against real sandbox when configured
- Metrics tracked: latency, error_rate, success_rate, availability_rate, response_diff
- `SUPPLIER_SIMULATION_ALLOWED` config flag controls simulation fallback

## Supplier Health & KPI System (CTO Directive — Session 2026-03-15)
**Supplier Health Monitoring:**
```
GET /api/inventory/supplier-health
→ latency_avg, error_rate, success_rate, availability_rate
→ last_sync, last_validation
→ status: healthy | degraded | down
```

**KPI Dashboard:**
- Supplier Drift Rate: drift > 2% / total revalidations
- Drift Severity: 0-2% normal (green), 2-5% warning (amber), 5-10% high (orange), 10%+ critical (red)
- Price Drift Timeline: x=time, y=diff%, group=supplier (Recharts LineChart)
- Price Consistency: 1 - drift_rate (reliability engine input)

## User Personas
- **Super Admin** (agent@acenta.test): Full platform control
- **Agency Admin** (agency1@demo.test): Agency-level operations
- **CTO**: Strategic decisions, pilot validation oversight

## Tech Stack
- **Backend**: FastAPI + MongoDB + Redis
- **Frontend**: React + Tailwind + Shadcn/UI + Recharts
- **3rd Party**: Stripe, APScheduler, Supplier adapters (Ratehawk, Paximum, WWTatil, TBO)

## Collections (MongoDB)
### Inventory Sync Engine (MEGA PROMPT #37)
- `supplier_inventory`: Hotel/product records per supplier
- `supplier_prices`: Cached prices per hotel per date per supplier
- `supplier_availability`: Room availability per hotel per date
- `inventory_sync_jobs`: Sync job tracking (status, records, timing)
- `inventory_index`: Flattened search-optimized documents
- `inventory_revalidations`: Booking-time revalidation records with drift severity

### Sandbox Config (MEGA PROMPT #38)
- `supplier_credentials`: Supplier API credentials and config (mode, base_url, validation_status)
- `supplier_sync_metrics`: Per-sync performance metrics (latency, error_rate, success_rate, availability_rate, api_calls)

### Existing Collections
- `pilot_agencies`, `pilot_metrics`, `pilot_incidents`

## Implemented Features

### Phase: Simulation Complete
- 10/10 successful simulation flows
- `supplier_response_diff` metric (search_price → revalidation_price → diff %)
- Pilot Dashboard with KPIs

### Phase: Inventory Sync Engine (MEGA PROMPT #37)
**Backend APIs:**
- `POST /api/inventory/sync/trigger` — Trigger supplier sync (simulation or real)
- `GET /api/inventory/sync/status` — Sync status for all 4 suppliers
- `GET /api/inventory/sync/jobs` — Sync job history
- `GET /api/inventory/search` — Cached search (~1.7ms latency)
- `GET /api/inventory/stats` — Comprehensive inventory statistics
- `POST /api/inventory/revalidate` — Price revalidation with drift severity

### Phase: Sandbox Integration (MEGA PROMPT #38)
**Backend APIs:**
- `GET /api/inventory/supplier-config` — Get all supplier sandbox configs
- `POST /api/inventory/supplier-config` — Set supplier credentials
- `DELETE /api/inventory/supplier-config/{supplier}` — Remove credentials
- `POST /api/inventory/sandbox/validate` — Run sandbox validation tests (with price_consistency)
- `GET /api/inventory/supplier-metrics` — Supplier performance metrics

**Ratehawk Sandbox Adapter:**
- Real API adapter: region_search, hotel_search, price extraction
- Credential validation against RateHawk overview endpoint
- Sandbox URL: `https://api-sandbox.worldota.net`
- Auth: Basic (base64 of key_id:api_key)

### Phase: Supplier Health & KPI Dashboard (2026-03-15) — COMPLETED
**Backend APIs:**
- `GET /api/inventory/supplier-health` — Supplier health status (healthy/degraded/down) with latency_avg, error_rate, success_rate, availability_rate, last_sync, last_validation
- `GET /api/inventory/kpi/drift` — KPI drift data: drift_rate, price_consistency, severity_breakdown, supplier_drift_rates, price_drift_timeline

**Backend Enhancements:**
- `SUPPLIER_SIMULATION_ALLOWED` config flag (production guard for simulation fallback)
- Enhanced metrics recording with `success_rate_pct` and `availability_rate_pct`
- Price consistency metric: `1 - drift_rate` (for reliability engine)
- Supplier health status calculation: healthy (>95% success, <2s latency), degraded (>80%), down

**Frontend — KPI Dashboard:**
- Drift Rate KPI card with color-coded severity
- Price Consistency KPI card (1 - drift_rate)
- Revalidasyonlar count card
- Sapma Sayisi (drift > 2%) card
- Drift Severity stacked bar chart (Recharts BarChart) per supplier
- Per-supplier severity table (Normal/Warning/High/Critical/Drift Rate/Consistency)
- Price Drift Timeline line chart (Recharts LineChart) with severity-colored dots
- Supplier Health panel with status badges (Healthy/Degraded/Down)

**Testing:**
- Backend: 25/25 tests passed (100%)
- Frontend: 100% UI verification passed

## Supplier Sync Config
| Supplier | Interval | Status | Sandbox Ready |
|----------|----------|--------|---------------|
| Ratehawk | 5 min | active | YES |
| Paximum | 15 min | active | NO (next phase) |
| WWTatil | 60 min | active | NO (future) |
| TBO | 30 min | pending | NO (future) |

## Drift Severity Classification
- 0-2%: Normal (green)
- 2-5%: Warning (amber)
- 5-10%: High (orange)
- 10%+: Critical (red)

## Sandbox Success Criteria (CTO Directive)
| Metric | Target |
|--------|--------|
| Search success | >95% |
| Latency | <2s |
| Error rate | <3% |
| Price drift | <5% |

## Upcoming Tasks (Prioritized)

### P0 — Real Ratehawk Sandbox Validation
- CTO provides credentials → implement actual API calls in ratehawk_sync_adapter.py
- Test: search, price, availability, revalidation against real sandbox
- Measure: supplier_latency, supplier_error_rate, supplier_success_rate, supplier_response_diff

### P1 — Paximum Sandbox
- Paximum sandbox adapter (same pattern as Ratehawk)
- Inventory sync, search, price, availability with real data

### P2 — Supplier Reliability Engine (MEGA PROMPT #39)
- Supplier reliability score calculation
- Supplier drift monitoring
- Supplier failover logic
- Supplier health dashboard (auto-select most reliable supplier)

### P3 — Pilot Phase
- 3 pilot agencies with real traffic
- 3 real bookings, 3 invoices, 3 accounting sync PASS
- 0 critical reconciliation mismatch

### P4+ — Future
- WWTatil search validation
- Accounting provider integrations (Luca, Parasut, Logo, Mikro)
- Financial Analytics, Tax Reporting
- APScheduler → Celery Beat migration
- Refactoring (after pilot complete)

## Known Issues
- P3: GitHub sync issue (platform-level, deferred)
- P4: Nested button HTML warning (de-prioritized)
- Redis unavailable in preview (MongoDB fallback working)
- Recharts width/height -1 console warning (cosmetic, charts render correctly)

## Strictly Prohibited (CTO Directive)
- No refactoring until pilot validation complete
- No CI/CD work or scheduler migration until pilot phase done
- Do not work on Paximum, WWTatil, Reliability Engine until Ratehawk sandbox validated
