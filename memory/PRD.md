# Syroce — Travel SaaS Platform PRD

## Original Problem Statement
Enterprise multi-tenant travel B2B SaaS platform for agencies. Includes search, booking, pricing, payments, supplier integrations, and ops management.

## Architecture
- **Frontend:** React + Tailwind + Shadcn/UI
- **Backend:** FastAPI + MongoDB + Redis + Celery
- **Suppliers:** RateHawk (hotel), TBO (hotel+flight+tour), Paximum (hotel+transfer+activity), WWTatil (tour)
- **Booking Core:** Orchestrator + State Machine + Failover Engine + Registry

## Completed Features

### Phase 1-2: Core Platform (DONE)
- Authentication, multi-tenancy, RBAC
- Hotel/flight search and booking
- Pricing, payments, CRM, Admin dashboards

### Phase 3: Production Hardening (DONE)
- Security, reliability, DLQ, monitoring, 15+ tabs

### Multi-Tenant Supplier Integration (DONE)
- AES-256 encrypted per-agency credential storage
- Connection testing, 4 supplier cards UI

### Supplier Adapter Pattern + Aggregator (DONE)
- Base Adapter interface, 4 real adapters, Aggregator, Capability Matrix

### Unified Booking & Fallback Layer (DONE)
- Real Adapter Bridges (RateHawk, TBO, Paximum, WWTatil)
- Registry Integration: 9 adapters, capability metadata, product type routing
- Unified Search: Fan-out across suppliers
- Price Revalidation: <2% silent, 2-5% warn, 5-10% approval, >10% abort
- Booking Execution with fallback chains
- Reconciliation: Price/status mismatch detection
- Audit & Observability: In-memory metrics + MongoDB audit trail

### Commercial Booking Experience Layer (DONE)
- Unified Search Page with 5 product types, supplier filtering, comparison view
- 5-step Booking Flow (travellers, billing, revalidation, confirm, result)
- Price Drift UX and Fallback UX
- Reconciliation Dashboard with KPI cards, mismatch table, audit trail

### Smart Search & Supplier Intelligence Layer (DONE - 13 Mar 2026)
- **Search Analytics Engine:**
  - Tracks 5 core funnel events: search, result_view, supplier_select, booking_start, booking_confirm
  - Persists to `search_analytics` MongoDB collection
  - Updates `recent_searches` and `destination_popularity` collections automatically
  - Daily search/booking aggregation for charts
  - Revenue per supplier tracking from booking confirmations
- **Supplier Performance Scoring:**
  - Weighted formula: 0.35*price + 0.25*success_rate + 0.15*latency + 0.15*cancel_reliability + 0.10*fallback_inverse
  - Generates tags: best_price, fastest_confirmation, most_reliable, best_cancellation
  - Default recommendations when no data
- **Smart Search Suggestions UI:**
  - Son Aramalar (Recent Searches) - clickable to re-run
  - Populer Destinasyonlar (Popular Destinations) - clickable with count badges
  - En Iyi Supplier'lar (Best Suppliers) - 3 categories with colored badges
- **KPI Analytics Dashboard (`/app/admin/analytics-kpi`):**
  - 6 KPI metric cards: Toplam Arama, Toplam Rezervasyon, Donusum Orani, Toplam Gelir, Basari Orani, Fallback Orani
  - Donusum Hunisi (Conversion Funnel): 5 steps with drop-off percentages
  - Gunluk Arama & Rezervasyon chart
  - 3 tabs: Genel Bakis, Supplier Performans, Gelir
  - Time filter: Son 7/30/90 gun + Refresh
- **Frontend Event Tracking:** result_view, supplier_select events auto-tracked
- **Test report:** 34/34 backend + 100% frontend (iteration_83)

## Intelligence API Endpoints
- `GET /api/intelligence/suggestions` — Recent searches, popular destinations, supplier recommendations
- `GET /api/intelligence/funnel` — Conversion funnel metrics (5 stages + rates)
- `GET /api/intelligence/daily-stats` — Daily search/booking counts for charts
- `GET /api/intelligence/supplier-scores` — Weighted supplier performance scores
- `GET /api/intelligence/supplier-recommendations` — Top 3 category recommendations
- `GET /api/intelligence/supplier-revenue` — Revenue per supplier
- `POST /api/intelligence/track` — Track frontend funnel events
- `GET /api/intelligence/kpi-summary` — Aggregated KPI summary

## Supplier Capability Matrix

| Supplier | Hotel | Flight | Tour | Transfer | Activity |
|----------|-------|--------|------|----------|----------|
| RateHawk | Yes   | -      | -    | -        | -        |
| TBO      | Yes   | Yes    | Yes  | -        | -        |
| Paximum  | Yes   | -      | -    | Yes      | Yes      |
| WWTatil  | -     | -      | Yes  | -        | -        |

## New DB Collections
- `search_analytics` — Funnel event tracking
- `recent_searches` — Per-org recent search history
- `destination_popularity` — Global destination popularity
- `booking_audit_log` — Audit trail events
- `unified_bookings` — Bookings via unified flow

## Remaining Backlog

### P0
- Activate real supplier connections with live API credentials
- End-to-end booking test with a real supplier

### P1
- Smart Supplier Selection (weighted auto-selection in booking flow)
- Search Caching & Optimization
- Agency Behavior Personalization
- Scheduled reconciliation jobs

### P2
- SaaS Pricing Model
- Prometheus/Grafana metrics
- Shadow traffic activation
- Cross-tenant security testing
- PyMongo AutoReconnect fix

## Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
