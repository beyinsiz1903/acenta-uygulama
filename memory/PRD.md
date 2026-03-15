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
                 → No Credentials?  → Simulation Mode
```
- Credentials stored in `supplier_credentials` MongoDB collection
- Each supplier independently configurable (mode, base_url, key_id, api_key)
- Validation tests run against real sandbox when configured
- Metrics tracked: latency, error_rate, response_diff

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
- `supplier_sync_metrics`: Per-sync performance metrics (latency, error_rate, api_calls)

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

### Phase: Sandbox Integration (MEGA PROMPT #38) — COMPLETED 2026-03-15
**Backend APIs:**
- `GET /api/inventory/supplier-config` — Get all supplier sandbox configs
- `POST /api/inventory/supplier-config` — Set supplier credentials
- `DELETE /api/inventory/supplier-config/{supplier}` — Remove credentials
- `POST /api/inventory/sandbox/validate` — Run sandbox validation tests
- `GET /api/inventory/supplier-metrics` — Supplier performance metrics

**Frontend:**
- Sandbox Konfigurasyon panel with per-supplier mode/status display
- Credential Ekle form (supplier, mode, base_url, key_id, api_key)
- Test/Remove buttons per configured supplier
- Sandbox validation result display with per-test pass/fail
- Mod column added to Sync Status and Job History tables
- Kaynak (Source) column added to Revalidations table

**Ratehawk Sandbox Adapter:**
- Real API adapter: region_search, hotel_search, price extraction
- Credential validation against RateHawk overview endpoint
- Sandbox URL: `https://api-sandbox.worldota.net`
- Production URL: `https://api.worldota.net`
- Auth: Basic (base64 of key_id:api_key)

**Testing:**
- Backend: 21/21 tests passed (100%)
- Frontend: 100% UI verification passed
- Previous: 38/38 original tests passed

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

## Upcoming Tasks (Prioritized)

### P0 — KPI Dashboard with Real Data
- Supplier Drift Rate KPI (drift > 2% / total bookings per supplier)
- Drift Severity colored display
- Price Drift Timeline Graph (x: time, y: diff%, group: supplier)

### P1 — Paximum Sandbox
- Paximum sandbox adapter (same pattern as Ratehawk)
- Inventory sync, search, price, availability with real data

### P2 — Pilot Phase
- 3 pilot agencies with real traffic
- 3 real bookings, 3 invoices, 3 accounting sync PASS
- 0 critical reconciliation mismatch

### P3+ — Future
- WWTatil search validation
- Accounting provider integrations (Luca, Parasut, Logo, Mikro)
- Financial Analytics, Tax Reporting
- APScheduler → Celery Beat migration
- Refactoring (after pilot complete)

## Known Issues
- P3: GitHub sync issue (platform-level, deferred)
- P4: Nested button HTML warning (de-prioritized)
- Redis unavailable in preview (MongoDB fallback working)

## Strictly Prohibited (CTO Directive)
- No refactoring until pilot validation complete
- No CI/CD work or scheduler migration until pilot phase done
