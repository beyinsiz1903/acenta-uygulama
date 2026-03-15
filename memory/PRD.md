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

## User Personas
- **Super Admin** (agent@acenta.test): Full platform control
- **Agency Admin** (agency1@demo.test): Agency-level operations
- **CTO**: Strategic decisions, pilot validation oversight

## Tech Stack
- **Backend**: FastAPI + MongoDB + Redis
- **Frontend**: React + Tailwind + Shadcn/UI + Recharts
- **3rd Party**: Stripe, APScheduler, Supplier adapters (Ratehawk, Paximum, WWTatil, TBO)

## Collections (MongoDB)
### Inventory Sync Engine (NEW — MEGA PROMPT #37)
- `supplier_inventory`: Hotel/product records per supplier
- `supplier_prices`: Cached prices per hotel per date per supplier
- `supplier_availability`: Room availability per hotel per date
- `inventory_sync_jobs`: Sync job tracking (status, records, timing)
- `inventory_index`: Flattened search-optimized documents
- `inventory_revalidations`: Booking-time revalidation records with drift severity

### Existing Collections
- `pilot_agencies`, `pilot_metrics`, `pilot_incidents`

## Implemented Features

### Phase: Simulation Complete ✅
- 10/10 successful simulation flows
- `supplier_response_diff` metric (search_price → revalidation_price → diff %)
- Pilot Dashboard with KPIs (Flow Health, Supplier Metrics, Finance Metrics, Diff Metrics)

### Phase: Inventory Sync Engine ✅ (MEGA PROMPT #37)
**Backend APIs:**
- `POST /api/inventory/sync/trigger` — Trigger supplier sync (simulation mode)
- `GET /api/inventory/sync/status` — Sync status for all 4 suppliers
- `GET /api/inventory/sync/jobs` — Sync job history
- `GET /api/inventory/search` — Cached search (Redis → MongoDB fallback, ~1.7ms latency)
- `GET /api/inventory/stats` — Comprehensive inventory statistics
- `POST /api/inventory/revalidate` — Price revalidation with drift severity

**Frontend:**
- Inventory Sync Dashboard at `/app/admin/inventory-sync`
- KPI cards (Hotels, Prices, Availability, Search Index, Sync Jobs, Redis Cache)
- Supplier Sync Status table with per-supplier sync controls
- Cached Search panel (confirms NO supplier API calls)
- City breakdown, Revalidation history with severity badges
- Sync job history

**Supplier Sync Config:**
| Supplier | Interval | Status |
|----------|----------|--------|
| Ratehawk | 5 min | active |
| Paximum | 15 min | active |
| WWTatil | 60 min | active |
| TBO | 30 min | pending |

**Drift Severity Classification:**
- 0-2%: Normal (green)
- 2-5%: Warning (amber)
- 5-10%: High (orange)
- 10%+: Critical (red)

## Upcoming Tasks (Prioritized)

### P0 — Ertelenmiş KPI Güncellemeleri
- Supplier Drift Rate KPI (drift > 2% olan booking / toplam booking per supplier)
- Drift Severity renkli gösterim
- Price Drift Timeline Grafiği (x: zaman, y: diff%, group: supplier)

### P1 — Sandbox Phase
- Ratehawk sandbox entegrasyonu (gerçek search, price, availability)
- Paximum sandbox entegrasyonu
- WWTatil sandbox test
- Sandbox Success Criteria: Search Success > 95%, Latency < 2s, Error Rate < 3%, Price Drift < 5%

### P2 — Pilot Phase
- 3 pilot agency gerçek trafik
- 3 real bookings, 3 invoices, 3 accounting sync PASS
- 0 critical reconciliation mismatch

### P3+ — Future
- Accounting provider entegrasyonları (Luca, Parasut, Logo, Mikro)
- Core finance modules (Financial Analytics, Tax Reporting)
- APScheduler → Celery Beat migrasyonu
- Refactoring (pilot tamamlandıktan sonra)

## Known Issues
- P3: GitHub sync issue (platform-level, deferred)
- P4: Nested button HTML warning (de-prioritized)
- Redis unavailable in preview (MongoDB fallback working)

## Strictly Prohibited (CTO Directive)
- No refactoring until pilot validation complete
- No CI/CD work or scheduler migration until pilot phase done
