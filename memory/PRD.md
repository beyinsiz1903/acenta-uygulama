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
- Search Analytics Engine: 5 funnel events, aggregation, destination popularity
- Supplier Performance Scoring: weighted formula (price 35%, success 25%, latency 15%, cancel 15%, fallback 10%)
- Smart Search Suggestions UI: Recent, Popular, Best Suppliers
- KPI Analytics Dashboard (`/app/admin/analytics-kpi`)
- Test: 34/34 backend + 100% frontend

### Revenue & Supplier Optimization Engine (DONE - 13 Mar 2026)
- **Supplier Revenue Analytics:** Revenue contribution, bookings, avg value per supplier
- **Supplier Profitability Scoring:** Weighted formula (commission 30%, success 25%, fallback 15%, latency 15%, cancel risk 15%) with tier ranking (platinum/gold/silver/bronze)
- **Revenue-Aware Supplier Selection:** Weighted ranking (price 35%, reliability 25%, profitability 25%, preference 15%)
- **Commission Management Model:** Supplier commission, platform markup, agency markup tracking
- **Smart Markup Engine:** Dynamic rules by supplier, destination, season, agency tier; CRUD API
- **Revenue Forecasting:** Linear regression on historical data, supplier projections, agency growth trends
- **Supplier Economics Dashboard (`/app/admin/supplier-economics`):**
  - 6 commission summary cards
  - 3 tabs: Genel Bakis (economics table), Karlilik Skoru (profitability cards + table), Markup Kurallari (rules panel)
- **Revenue Optimization Dashboard (`/app/admin/revenue-optimization`):**
  - 6 GMV cards (GMV, Platform Geliri, Toplam Rez., Ort. Deger, Aktif Acenta, Aktif Supplier)
  - 4 tabs: Genel Bakis (funnel + destinations + suppliers + profitability), Tahmin (forecast), Acenta Analizi, Supplier Geliri
- **Test:** 38/38 backend + 100% frontend (iteration_84)

## Revenue API Endpoints
- `GET /api/revenue/supplier-analytics` — Supplier revenue analytics
- `GET /api/revenue/agency-analytics` — Agency revenue analytics
- `GET /api/revenue/gmv-summary` — Gross Merchandise Value
- `GET /api/revenue/profitability-scores` — Supplier profitability with tiers
- `GET /api/revenue/commission-summary` — Commission aggregation
- `GET /api/revenue/markup-rules` — List active markup rules
- `POST /api/revenue/markup-rules` — Create/update markup rule
- `DELETE /api/revenue/markup-rules/{rule_id}` — Deactivate rule
- `POST /api/revenue/calculate-markup` — Calculate markup for booking
- `GET /api/revenue/supplier-economics` — Combined economics view
- `GET /api/revenue/forecast` — Revenue/booking forecasting
- `GET /api/revenue/business-kpi` — Complete business KPI dashboard
- `GET /api/revenue/destination-revenue` — Revenue by destination
- `POST /api/revenue/supplier-selection` — Revenue-aware supplier ranking

## Intelligence API Endpoints
- `GET /api/intelligence/suggestions` — Recent searches, popular destinations, supplier recommendations
- `GET /api/intelligence/funnel` — Conversion funnel metrics
- `GET /api/intelligence/daily-stats` — Daily search/booking counts
- `GET /api/intelligence/supplier-scores` — Supplier performance scores
- `GET /api/intelligence/supplier-recommendations` — Top 3 recommendations
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

## New DB Collections (Revenue Phase)
- `commission_records` — Commission/markup records per booking
- `markup_rules` — Smart markup rule engine configuration

## Remaining Backlog

### P0
- Activate real supplier connections with live API credentials
- End-to-end booking test with a real supplier

### P1
- Search Caching & Optimization
- Agency Behavior Personalization
- Scheduled reconciliation jobs (hourly booking sync, daily reconciliation, price mismatch detection)

### P2
- SaaS Pricing Model
- Prometheus/Grafana metrics
- Shadow traffic activation
- Cross-tenant security testing
- PyMongo AutoReconnect fix

## Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
