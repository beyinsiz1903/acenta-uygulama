# Changelog

## 2026-03-18 — Outbox Consumer Hardening + API Response Standard + API Versioning

### Outbox Consumer Hardening (3 improvements)
- **EventPublisher abstraction:** Created `infrastructure/event_publisher.py` with `DomainEvent` dataclass and `EventTransport` protocol. Outbox consumer now uses `get_transport()` instead of raw Redis push. Transport is swappable (Redis → Kafka) without touching any service code.
- **Idempotency hardening:** Two-layer dedup — Redis fast-path check (O(1), 7-day TTL) + MongoDB unique index on `(event_id, handler)`. Handles `DuplicateKeyError` gracefully.
- **Dead-letter visibility:** New endpoints:
  - `GET /api/admin/outbox/dead-letter` — full DLQ with breakdown by event type
  - `POST /api/admin/outbox/dead-letter/retry-all` — bulk retry with optional event_type filter
  - `GET /api/admin/outbox/stats-by-type` — event stats grouped by type and status

### API Response Standardization
- **Middleware:** `middleware/response_envelope.py` — wraps ALL JSON API responses in standard envelope
- **Success:** `{ok: true, data: {...}, meta: {trace_id, timestamp, latency_ms, api_version}}`
- **Error:** `{ok: false, error: {code, message, details}, meta: {...}}`
- **Exclusions:** Health, OpenAPI, static files, root endpoint
- **Pagination helper:** `response.py` with `paginated()` function for standardized list responses

### API Versioning (/api/v1/)
- **Middleware:** `middleware/api_versioning.py` — transparent path-rewrite (`/api/v1/x` → `/api/x`)
- **Zero router changes** — all existing endpoints instantly accessible at `/api/v1/...`
- **Deprecation headers:** `X-API-Deprecated`, `X-API-Sunset`, `X-API-Upgrade` on legacy `/api/` paths
- **CORS:** Versioning headers exposed in CORS config

### Testing: 22/22 tests passed (iteration_146.json)

## 2026-03-18 — Celery + Redis + Outbox Consumer (P0 #4)
- **Infrastructure:** Set up Redis server (supervisor-managed), Celery worker (2 concurrency, 3 queues), Celery beat (5s poll interval)
- **Outbox Consumer:** Implemented poll-and-dispatch logic
- **Event Dispatch Table:** 10 event types, 35+ handler registrations
- **First-Wave Consumers:** 5 idempotent consumer handlers
- **Admin API:** 8 endpoints under `/api/admin/outbox/`
- **Testing:** 25/26 tests passed (iteration_145.json)

## 2026-03-17 — Orphan Order Recovery
- Evidence-based migration script for 86 orphaned orders
- Admin API for quarantine management
- 38/38 API tests passed

## Previous — Tenant Isolation Hardening
- Enforced organization_id on all collections
- Middleware-level tenant boundary checks
- Booking truth model with state machine

## Previous — Router Domain Registry
- Domain-driven router organization
- Bootstrap pattern for modular router registration
