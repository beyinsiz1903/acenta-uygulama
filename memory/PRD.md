# Syroce — Travel Agency Operating System (PRD)

## Core Product
Multi-tenant SaaS platform for travel agencies. Manages bookings, finance, suppliers, B2B distribution, and internal operations.

## Tech Stack
- **Backend:** FastAPI, Motor, Pydantic, Celery, Redis
- **Frontend:** React, Shadcn/UI
- **Database:** MongoDB
- **Infrastructure:** Redis (cache, rate limiting, Celery broker)
- **Architecture:** Event-Driven, CQRS-lite, Circuit Breaker, Distributed Rate Limiting
- **Observability:** OpenTelemetry, Prometheus-ready

## Current Architecture Version: 3.0 (Supplier Ecosystem)

---

## What's Been Implemented

### Phase 1 — Core Platform (Complete)
- Multi-tenant agency management
- User auth with JWT (role-based)
- Booking CRUD
- Finance (accounts, transactions, payments, invoices)
- Customer management
- Document management
- Web catalog & WebPOS
- Google Sheets & AviationStack integrations

### Phase 2 — Enterprise Infrastructure (Complete)
- Celery + Redis async task queue
- Redis-based distributed rate limiting (token bucket)
- Event-driven architecture (Redis Pub/Sub)
- Circuit breaker pattern (pybreaker)
- OpenTelemetry instrumentation
- MongoDB index optimization
- Infrastructure monitoring router (/api/infra/*)

### Phase 3 — Supplier Ecosystem (Complete - 2026-03-12)
**14-part production-grade supplier integration architecture:**

1. **Supplier Adapter Contracts** — ABC with 7 lifecycle methods (healthcheck, search, availability, pricing, hold, confirm, cancel), typed error hierarchy, normalized schemas (20+ Pydantic models)

2. **5 Supplier Adapters** — Mock implementations for hotel, flight, tour, insurance, transport (full lifecycle support)

3. **Inventory Aggregation** — Multi-supplier parallel fan-out, deduplication, normalization, sorting, pagination, degraded mode

4. **Booking State Machine** — 13 states, 22 transitions, atomic MongoDB state updates with event emission, rollback map

5. **Booking Orchestration Engine** — Full lifecycle (search → price validate → hold → payment → confirm → voucher), retry with exponential backoff, failover, compensation

6. **Supplier Failover Engine** — Weighted composite scoring (health 40%, price 30%, reliability 30%), automatic fallback chain, audit logging

7. **Supplier Health Scoring** — 5-metric formula (latency, error rate, timeout rate, confirmation rate, freshness), 4 health states, auto-disable at score < 40

8. **Redis Inventory Cache** — Per-product-type TTL (flight: 5min, hotel: 15min, tour: 30min), stale-while-revalidate, cache invalidation API

9. **Pricing Engine** — 6-stage pipeline (markup → channel → tier → commission → promo → currency), 4 agency tiers (starter/standard/premium/enterprise)

10. **Channel Manager** — B2B partner CRUD, supplier/product access control, credit limits, API key generation, approval workflow

11. **Domain Events** — 15 event types, 5 handlers registered (search, booking, failover, health, cancellation)

12. **Database Design** — 7 new collections, 20 indexes (with TTL policies), full tenant isolation

13. **API Router** — 18 endpoints under /api/suppliers/ecosystem/*, role-based auth

14. **Architecture Documentation** — /app/memory/supplier_ecosystem_architecture.md (complete with diagrams, schemas, top 50 tasks, top 20 risks, maturity score)

---

## API Endpoints — Supplier Ecosystem

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/suppliers/ecosystem/search | Multi-supplier search |
| POST | /api/suppliers/ecosystem/availability | Availability check |
| POST | /api/suppliers/ecosystem/pricing | Price validation |
| POST | /api/suppliers/ecosystem/hold | Create hold |
| POST | /api/suppliers/ecosystem/confirm | Confirm booking |
| POST | /api/suppliers/ecosystem/cancel | Cancel booking |
| POST | /api/suppliers/ecosystem/orchestrate | Full booking flow |
| GET  | /api/suppliers/ecosystem/health | Health dashboard |
| POST | /api/suppliers/ecosystem/health/{code}/compute | Compute health score |
| GET  | /api/suppliers/ecosystem/failover-logs | Failover audit |
| GET  | /api/suppliers/ecosystem/orchestration-runs | Orchestration history |
| GET  | /api/suppliers/ecosystem/partners | List partners |
| POST | /api/suppliers/ecosystem/partners | Create partner |
| POST | /api/suppliers/ecosystem/partners/{id}/approve | Approve partner |
| GET  | /api/suppliers/ecosystem/cache/stats | Cache stats |
| POST | /api/suppliers/ecosystem/cache/invalidate | Invalidate cache |
| GET  | /api/suppliers/ecosystem/registry | Adapter registry |
| GET  | /api/suppliers/ecosystem/booking-states | State machine info |

---

## Pending / Backlog

### P0 — Critical
- Replace mock adapters with real supplier integrations (Paximum, AviationStack)
- God Router decomposition (ops_finance.py → domain routers)
- Implement real Celery task bodies (voucher PDF, email)

### P1 — High
- Implement RBAC (role-based access control)
- Supplier onboarding API
- Booking amendment flow
- Multi-currency support in pricing engine
- Webhook receiver for supplier push notifications

### P2 — Medium
- GDS connectivity (Amadeus, Sabre)
- Supplier sandbox environment
- Booking reconciliation
- Dynamic pricing based on demand
- Grafana dashboards

### P3 — Future
- ML-based supplier ranking
- A/B testing for pricing rules
- Multi-region deployment
- Booking fraud detection

---

## Test Credentials
- **Agency Admin:** agent@acenta.test / agent123
- **Agency User:** agency1@demo.test / agency123

## Key Files
- `/app/backend/app/suppliers/` — Supplier ecosystem domain
- `/app/memory/supplier_ecosystem_architecture.md` — Architecture docs
- `/app/test_reports/iteration_66.json` — Full test report (23/23 passed)
