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
7. **Webhook Platform Capability** — Productized webhook system for external integrations

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

### Event System (COMPLETED + HARDENED)
- **Outbox Table:** `outbox_events` collection
- **EventPublisher:** Infrastructure adapter — domain layer never touches Celery/Redis directly
- **Outbox Consumer:** Periodic Celery beat task (every 5s)
- **Dispatch Table:** Maps event types to consumer handlers (13 event types, 45+ handlers)
- **First-Wave Consumers:** notification, email, billing, reporting, webhook
- **Guarantees:** At-least-once delivery, idempotent consumers, dead-letter queue

### API Response Standard (COMPLETED)
- **Envelope:** `{ok, data, meta}` format for all JSON API responses
- **Meta:** `{trace_id, timestamp, latency_ms, api_version}`

### API Versioning (COMPLETED)
- **Canonical:** `/api/v1/...`
- **Legacy:** `/api/...` with deprecation headers

### Webhook System (COMPLETED — P0.5)
- **Subscription Model:** Organization-scoped, multi-endpoint, event-filtered
- **Security:** HMAC-SHA256 signing, HTTPS-only, SSRF protection, secret rotation
- **Delivery Contract:** Standard headers (X-Webhook-Event, X-Webhook-Delivery-Id, X-Webhook-Timestamp, X-Webhook-Signature)
- **Retry Policy:** 6 attempts with exponential backoff (0s, 60s, 300s, 900s, 3600s, 21600s)
- **Idempotency:** subscription_id + event_id unique constraint
- **Circuit Breaker:** Per-subscription automatic pause after 5 consecutive failures
- **Supported Events:** booking.created, booking.quoted, booking.optioned, booking.confirmed, booking.cancelled, booking.completed, booking.refunded, invoice.created, payment.received, payment.refunded
- **Admin Surface:** Health, stats, delivery logs, dead-letter, manual replay, circuit reset

### Key Collections
- `outbox_events`, `outbox_consumer_results`, `outbox_consumer_log`, `outbox_dead_letters`
- `booking_notifications`, `email_outbox`
- `billing_projections`, `reporting_daily_events`, `reporting_funnel`
- `webhook_subscriptions` — Registered webhook endpoints per org (with secret, circuit state)
- `webhook_deliveries` — Delivery records with idempotency (subscription_id + event_id unique)
- `webhook_delivery_attempts` — Individual attempt logs per delivery

## What's Been Implemented
- [x] Booking truth model with state machine
- [x] Tenant isolation (organization_id enforcement)
- [x] Orphan order recovery (evidence-based migration + quarantine)
- [x] Celery + Redis + Outbox Consumer (5 first-wave consumers)
- [x] Outbox Consumer Hardening (EventPublisher, Idempotency, DLQ)
- [x] API Response Standardization (Envelope Middleware)
- [x] API Versioning (/api/v1/)
- [x] **Webhook System Productization** — 2026-03-18
  - Subscription CRUD (create/read/update/delete/rotate-secret)
  - HMAC-SHA256 signed delivery with standard headers
  - SSRF protection (HTTPS-only, private IP blocking)
  - Retry with exponential backoff (6 attempts)
  - Circuit breaker per subscription endpoint
  - Admin monitoring (health, stats, dead-letter, replay, circuit reset)
  - 10 supported webhook events
  - Idempotency enforcement (subscription_id + event_id)
  - 27/27 tests passed

## Prioritized Backlog

### P0 + P0.5 — COMPLETED
All P0 and P0.5 tasks have been addressed.

### P1 — Next Sprint
1. **Router Consolidation Phase 2** — Physical merge of fragmented router files into domain modules
2. **Event-Driven Core Expansion** — Add more domain-specific workers and event types
3. **Cache Strategy** — L0/L1/L2 caching layers

### P2 — Future
1. **Product Packaging** — Core/Pro/Enterprise tier feature gating
2. **New Supplier Adapters** — Hotelbeds, Juniper
3. **Frontend Persona Separation** — Sales/Ops/Finance views
4. **Enterprise SLA Monitoring**
5. **Rate Limiting Enhancement** — per-tenant rate limits
