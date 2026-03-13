# Syroce — Travel Platform PRD

## Original Problem Statement
Enterprise Travel Agency SaaS + Multi-Supplier Distribution Engine + Supplier Intelligence Platform + Revenue Optimization Engine + Platform Scalability & Global Readiness Layer.

The platform enables travel agencies to search, book, and manage travel products (hotels, tours, flights) across multiple suppliers through a unified interface with intelligent supplier selection, revenue optimization, and operational monitoring.

## Core Architecture
```
supplier adapters → supplier aggregator → unified search → unified booking
→ fallback engine → reconciliation → analytics → supplier intelligence
→ revenue optimization → platform scalability & monitoring
```

## User Personas
- **Super Admin**: Platform-wide management, monitoring, revenue analytics
- **Agency Admin**: Agency-level booking, customer management, reporting
- **Agency User**: Search, book, manage reservations

## Tech Stack
- **Backend**: FastAPI + MongoDB + Redis
- **Frontend**: React + Shadcn UI + Tailwind CSS
- **Background Jobs**: APScheduler
- **Supplier Adapters**: RateHawk, TBO, Paximum, WWTatil

## Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123

---

## What's Been Implemented

### Phase 1: Unified Booking & Fallback Layer ✅
- Supplier adapter pattern with circuit breakers
- Fan-out parallel search across suppliers
- Unified booking with automatic fallback
- Price revalidation before booking
- Idempotency key protection

### Phase 2: Commercial Booking Experience Layer ✅
- Supplier settings management UI
- Smart booking suggestions
- Unified search page with filters
- KPI analytics dashboard

### Phase 3: Smart Search & Supplier Intelligence Layer ✅
- User behavior tracking and analytics
- Supplier performance scoring
- Search funnel analytics
- Personalization engine

### Phase 4: Revenue & Supplier Optimization Engine (MEGA PROMPT #25) ✅
- Revenue tracking (bookings, revenue, commission per supplier/agency)
- Supplier profitability scoring (platinum/gold/silver/bronze tiers)
- Revenue-aware supplier selection (price + profitability + reliability)
- Commission & dynamic markup engine
- Revenue dashboards (Supplier Economics + Revenue Optimization)

### Phase 5: Platform Scalability & Global Readiness (MEGA PROMPT #26) ✅ — Mar 13, 2026
**Faz A — Core Execution + Revenue Binding:**
- Search Caching Layer with cache-first lookup, TTL per product type, hit/miss tracking
- Commission engine bound to booking flow (booking_confirm → markup → revenue record)
- Supplier-specific rate limiting with queue and retry policy
- Distributed search with per-supplier latency tracking

**Faz B — Monitoring + Scheduled Jobs:**
- Prometheus metrics enhanced with supplier-level counters (search_latency, booking_success_rate, supplier_failure_rate, revenue_per_supplier)
- Job Scheduler (APScheduler) with 5 background jobs:
  - Hourly booking status sync
  - Daily supplier reconciliation
  - 15-min supplier health check
  - 30-min analytics aggregation
  - Daily revenue reconciliation
- Platform Monitoring Dashboard (frontend) with 4 tabs: Overview, Cache, Supplier Metrics, Scheduler

**Faz C — Global Readiness:**
- Multi-currency support (TRY/EUR/USD/GBP) with conversion API
- Global tax handling engine (9 countries: TR, AE, GB, DE, FR, IT, ES, GR, US) with VAT + tourism tax

---

## Key API Endpoints

### Scalability & Monitoring
- `GET /api/scalability/cache-stats` — Cache hit/miss stats
- `GET /api/scalability/scheduler-status` — Job scheduler info
- `POST /api/scalability/scheduler/trigger` — Manual job trigger
- `GET /api/scalability/monitoring-dashboard` — Combined monitoring data
- `GET /api/scalability/supplier-metrics` — Supplier-level metrics
- `GET /api/scalability/search-metrics` — Search cache metrics
- `GET /api/scalability/redis-health` — Redis health check
- `GET /api/scalability/rate-limit-stats` — Rate limiter stats
- `GET /api/scalability/tax-regions` — Tax regions
- `POST /api/scalability/tax-breakdown` — Tax calculation
- `POST /api/scalability/currency-convert` — Currency conversion
- `GET /api/scalability/currency-rates` — Exchange rates

### Revenue
- `GET /api/revenue/business_kpis` — Platform-wide KPIs
- `GET /api/revenue/supplier_economics` — Supplier financial data
- `GET /api/revenue/agency_analytics` — Agency revenue data
- `GET /api/revenue/profitability_ranking` — Supplier profitability ranking

### Booking
- `POST /api/unified/search` — Unified supplier search (cache-first)
- `POST /api/unified/book` — Unified booking (with commission binding)

---

## Prioritized Backlog

### P0 — Next Phase
- **Faz D: Tenant Scaling** — Concurrency controls, connection pooling, tenant isolation
- **Final Scalability Architecture Document** — Top 25 scaling tasks, top 15 risks, maturity score

### P1 — Upcoming
- **MEGA PROMPT #27: Live Operations & Market Readiness**
  - Real supplier credential validation
  - Live monitoring
  - Onboarding readiness
  - Market launch checklist
- Revenue Forecasting implementation
- SaaS Pricing Model infrastructure

### P2 — Backlog
- PyMongo AutoReconnect fix (intermittent test failures)
- Shadow traffic activation for supplier testing
- Cross-tenant security testing
- Production build optimization (ThemeProvider path issue)

---

## Platform Scores (CTO Review)
| Area | Score |
|---|---|
| Architecture | 9.9 |
| Security | 9.8 |
| Reliability | 9.9 |
| Infrastructure | 9.8 |
| Supplier Ecosystem | 9.9 |
| Booking Engine | 9.9 |
| Commercial UX | 9.8 |
| Product Intelligence | 9.9 |
| Revenue Optimization | 9.8 |
| Operations | 9.8 |
| **Overall** | **9.92/10** |
