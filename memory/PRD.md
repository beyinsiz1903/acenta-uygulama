# PRD — Travel Distribution SaaS Platform (Syroce)

## Original Problem Statement
The CTO is guiding the refactoring of a monolithic application into a stable, scalable SaaS platform. The platform is a B2B travel distribution system for agencies to manage bookings, pricing, inventory, and customer relationships.

## Core Requirements
1. **Multi-Tenant Architecture** — Strict tenant isolation via `organization_id` on every document
2. **Booking Truth Model** — Single source of truth for booking state with proper state machine
3. **Event-Driven Architecture** — Transactional outbox pattern with async consumers
4. **Domain-Driven Design** — Modular domain boundaries (booking, pricing, inventory, etc.)
5. **Audit & Compliance** — Full audit trail for all state changes
6. **API Contract Stability** — Standard response envelope, versioning, trace IDs

## User Personas
- **Super Admin** — Platform-wide management, migration oversight
- **Agency Admin** — Organization-level management
- **Sales/Ops** — Day-to-day booking and customer management
- **External Developer** — API consumer via versioned endpoints + webhooks

## Architecture

### Backend
- **Framework:** FastAPI
- **Database:** MongoDB (Motor async driver)
- **Queue:** Celery + Redis (broker DB 1, results DB 2, cache DB 0)
- **Pattern:** Transactional Outbox → Celery Worker → Consumer Handlers

### Event System (P0 #4 — COMPLETED + HARDENED)
- **Outbox Table:** `outbox_events` collection — events produced by command handlers
- **EventPublisher:** Infrastructure adapter (`event_publisher.py`) — domain layer never touches Celery/Redis directly. Transport is swappable (Redis today, Kafka tomorrow).
- **Outbox Consumer:** Periodic Celery beat task (every 5s) polls pending events, uses EventPublisher transport
- **Dispatch Table:** Maps event types to consumer handlers (10 event types, 35+ handlers)
- **Consumers (First Wave):**
  1. `send_booking_notification` — In-app notification records
  2. `send_booking_email` — Email queue (via email_outbox collection)
  3. `update_billing_projection` — Monthly billing/revenue aggregation
  4. `update_reporting_projection` — Daily events + funnel metrics
  5. `dispatch_webhook` — External webhook delivery to registered endpoints
- **Guarantees:** At-least-once delivery, idempotent consumers (two-layer: Redis + MongoDB unique index), dead-letter queue
- **Admin API:** Health, stats, pending/failed events, dead-letter visibility, manual trigger, retry, bulk retry

### API Response Standard (COMPLETED)
- **Envelope:** All JSON API responses wrapped in `{ok, data, meta}` format
- **Error format:** `{ok: false, error: {code, message, details}, meta}`
- **Meta:** `{trace_id, timestamp, latency_ms, api_version}`
- **Exclusions:** `/health`, `/api/health`, `/`, `/docs`, `/redoc`, static files

### API Versioning (COMPLETED)
- **Canonical:** `/api/v1/...` — all endpoints accessible via versioned path
- **Legacy:** `/api/...` — backward compatible, returns deprecation headers
- **Headers:** `X-API-Version: v1`, `X-API-Deprecated: true` (on legacy), `X-API-Sunset: 2026-09-01`
- **Mechanism:** Transparent path-rewrite middleware, zero router changes

### Key Collections
- `outbox_events` — Transactional outbox (status: pending → processing → dispatched/dead_letter)
- `outbox_consumer_results` — Idempotency tracking (event_id + handler unique index + Redis fast-path)
- `outbox_consumer_log` — Audit trail for consumer processing
- `outbox_dead_letters` — Failed events after max retries
- `booking_notifications` — In-app notifications from consumer
- `email_outbox` — Email queue from consumer
- `billing_projections` — Monthly billing aggregations
- `reporting_daily_events` — Daily event counters
- `reporting_funnel` — Monthly funnel stage counts
- `webhook_subscriptions` — Registered webhook endpoints per org
- `webhook_deliveries` — Webhook delivery records

## What's Been Implemented
- [x] Booking truth model with state machine
- [x] Tenant isolation (organization_id enforcement)
- [x] Orphan order recovery (evidence-based migration + quarantine)
- [x] Celery + Redis + Outbox Consumer (P0 #4) — 2026-03-18
- [x] Outbox Consumer Hardening — 2026-03-18
  - EventPublisher transport abstraction (Celery/Redis decoupled)
  - Two-layer idempotency (Redis fast-path + MongoDB unique constraint)
  - Dead-letter visibility (dedicated endpoint, bulk retry, stats breakdown)
- [x] API Response Standardization — 2026-03-18
- [x] API Versioning (/api/v1/) — 2026-03-18
- [x] 5 first-wave consumers: notification, email, billing, reporting, webhook
- [x] Admin outbox monitoring API (11 endpoints)
- [x] Event dispatch table (10 event types, 35+ handlers)
- [x] Supervisor configs for Redis, Celery worker, Celery beat

## Prioritized Backlog

### P0 — COMPLETED
All P0 tasks have been addressed.

### P0.5 — Next
1. **Webhook System Productization** — subscription API, HMAC secret, delivery log, retry visibility, failure dashboard

### P1 — Next Sprint
1. **Router Consolidation Phase 2** — Physical merge of fragmented router files into domain modules
2. **Event-Driven Core Expansion** — Add more domain-specific workers and event types
3. **Cache Strategy** — L0 (in-memory), L1 (Redis), L2 (MongoDB) caching layers

### P2 — Future
1. **Product Packaging** — Core/Pro/Enterprise tier feature gating
2. **New Supplier Adapters** — Hotelbeds, Juniper
3. **Frontend Persona Separation** — Sales/Ops/Finance views
4. **Enterprise SLA Monitoring**
5. **Rate Limiting Enhancement** — per-tenant rate limits
