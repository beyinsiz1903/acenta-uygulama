# PRD — Travel Distribution SaaS Platform (Syroce)

## Original Problem Statement
The CTO is guiding the refactoring of a monolithic application into a stable, scalable SaaS platform. The platform is a B2B travel distribution system for agencies to manage bookings, pricing, inventory, and customer relationships.

## Core Requirements
1. **Multi-Tenant Architecture** — Strict tenant isolation via `organization_id` on every document
2. **Booking Truth Model** — Single source of truth for booking state with proper state machine
3. **Event-Driven Architecture** — Transactional outbox pattern with async consumers
4. **Domain-Driven Design** — Modular domain boundaries (booking, pricing, inventory, etc.)
5. **Audit & Compliance** — Full audit trail for all state changes

## User Personas
- **Super Admin** — Platform-wide management, migration oversight
- **Agency Admin** — Organization-level management
- **Sales/Ops** — Day-to-day booking and customer management

## Architecture

### Backend
- **Framework:** FastAPI
- **Database:** MongoDB (Motor async driver)
- **Queue:** Celery + Redis (broker DB 1, results DB 2, cache DB 0)
- **Pattern:** Transactional Outbox → Celery Worker → Consumer Handlers

### Event System (P0 #4 — COMPLETED)
- **Outbox Table:** `outbox_events` collection — events produced by command handlers
- **Outbox Consumer:** Periodic Celery beat task (every 5s) polls pending events
- **Dispatch Table:** Maps event types to consumer handlers (10 event types, 35+ handlers)
- **Consumers (First Wave):**
  1. `send_booking_notification` — In-app notification records
  2. `send_booking_email` — Email queue (via email_outbox collection)
  3. `update_billing_projection` — Monthly billing/revenue aggregation
  4. `update_reporting_projection` — Daily events + funnel metrics
  5. `dispatch_webhook` — External webhook delivery to registered endpoints
- **Guarantees:** At-least-once delivery, idempotent consumers, dead-letter queue
- **Admin API:** Health, stats, pending/failed events, manual trigger, retry

### Key Collections
- `outbox_events` — Transactional outbox (status: pending → processing → dispatched/dead_letter)
- `outbox_consumer_results` — Idempotency tracking (event_id + handler unique)
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
- [x] 5 first-wave consumers: notification, email, billing, reporting, webhook
- [x] Admin outbox monitoring API (8 endpoints)
- [x] Event dispatch table (10 event types, 35+ handlers)
- [x] Supervisor configs for Redis, Celery worker, Celery beat

## Prioritized Backlog

### P0 — COMPLETED
All P0 tasks have been addressed.

### P1 — Next Sprint
1. **Event-Driven Core Expansion** — Add more domain-specific workers and event types
2. **Router Consolidation Phase 2** — Physical merge of fragmented router files into domain modules
3. **API Response Standardization** — Standard envelope (success/error), pagination, trace IDs
4. **Cache Strategy** — L0 (in-memory), L1 (Redis), L2 (MongoDB) caching layers

### P2 — Future
1. **Product Packaging** — Core/Pro/Enterprise tier feature gating
2. **API Versioning** — /api/v1/ namespace
3. **Webhook System UI** — Frontend for managing webhook subscriptions
4. **New Supplier Adapters** — Hotelbeds, Juniper
5. **Frontend Persona Separation** — Sales/Ops/Finance views
6. **Enterprise SLA Monitoring**
