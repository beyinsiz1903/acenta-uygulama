# Changelog

## 2026-03-18 — Webhook System Productization (P0.5)

### Webhook Subscription API
- **CRUD:** Create/Read/Update/Delete/List subscriptions per organization
- **Secret Management:** HMAC signing secrets generated on create, shown once, masked on GET, rotation supported
- **Validation:** HTTPS-only URLs, SSRF protection (private IPs, metadata endpoints blocked), event type validation
- **Duplicate Policy:** Same org + URL + event set rejected
- **Rate Limit:** Max 10 active subscriptions per organization

### Webhook Delivery System
- **Async Delivery:** Celery tasks for fan-out delivery to all matching subscriptions
- **HMAC-SHA256 Signing:** `X-Webhook-Signature: sha256=HMAC(secret, timestamp.payload)`
- **Standard Headers:** X-Webhook-Event, X-Webhook-Delivery-Id, X-Webhook-Timestamp, X-Webhook-Signature
- **Retry Policy:** 6 attempts — 0s, 60s, 5m, 15m, 1h, 6h (only for 5xx, 429, network errors; 4xx = no retry)
- **Idempotency:** subscription_id + event_id unique constraint prevents double delivery
- **Circuit Breaker:** Per-subscription, auto-opens after 5 consecutive failures, auto-recovers after 30 min

### Admin Monitoring
- **Health Endpoint:** Health score based on success rate and circuit state
- **Stats:** Delivery counts by event type and status, avg response time
- **Dead-Letter View:** Failed deliveries with breakdown by event type
- **Manual Replay:** Re-trigger failed deliveries
- **Circuit Reset:** Admin can manually close open circuit breakers
- **Subscription Health:** All subscriptions with enriched delivery stats

### Supported Events (10)
booking.created, booking.quoted, booking.optioned, booking.confirmed, booking.cancelled, booking.completed, booking.refunded, invoice.created, payment.received, payment.refunded

### Infrastructure
- Added `webhook_queue` to Celery worker and queue definitions
- Added `webhook_tasks` module to Celery includes
- Added `booking.created`, `booking.optioned`, `invoice.created`, `payment.received`, `payment.refunded` to event dispatch table
- Updated outbox `dispatch_webhook` consumer to delegate to productized system
- MongoDB indexes on webhook_subscriptions and webhook_deliveries

### Testing: 27/27 tests passed (iteration_147.json)

## 2026-03-18 — Outbox Consumer Hardening + API Response Standard + API Versioning

### Outbox Consumer Hardening (3 improvements)
- **EventPublisher abstraction:** Swappable transport (Redis → Kafka)
- **Idempotency hardening:** Two-layer dedup — Redis fast-path + MongoDB unique index
- **Dead-letter visibility:** DLQ endpoints, bulk retry, stats breakdown

### API Response Standardization
- **Middleware:** Wraps ALL JSON API responses in standard envelope
- **Success:** `{ok: true, data: {...}, meta: {trace_id, timestamp, latency_ms, api_version}}`
- **Error:** `{ok: false, error: {code, message, details}, meta: {...}}`

### API Versioning (/api/v1/)
- **Middleware:** Transparent path-rewrite
- **Deprecation headers:** On legacy `/api/` paths

### Testing: 22/22 tests passed (iteration_146.json)

## 2026-03-18 — Celery + Redis + Outbox Consumer (P0 #4)
- Infrastructure: Redis server, Celery worker, Celery beat
- Outbox Consumer: Poll-and-dispatch logic
- Event Dispatch Table: 10 event types, 35+ handler registrations
- 5 idempotent consumer handlers
- Admin API: 8 endpoints

## 2026-03-17 — Orphan Order Recovery
- Evidence-based migration script for 86 orphaned orders

## Previous — Tenant Isolation Hardening + Booking Truth Model + Router Domain Registry
