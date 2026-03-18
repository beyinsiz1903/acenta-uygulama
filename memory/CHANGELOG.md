# Changelog

## 2026-03-18 — Celery + Redis + Outbox Consumer (P0 #4)
- **Infrastructure:** Set up Redis server (supervisor-managed), Celery worker (2 concurrency, 3 queues), Celery beat (5s poll interval)
- **Outbox Consumer:** Implemented poll-and-dispatch logic that reads `outbox_events`, fans out to registered handlers via dispatch table, handles retries and dead-lettering
- **Event Dispatch Table:** 10 event types (booking.confirmed/cancelled/quoted/completed/amended/refunded, payment.completed/failed, booking.ticketed/vouchered) with 35+ handler registrations
- **First-Wave Consumers:** 5 idempotent consumer handlers:
  - `send_booking_notification` → `booking_notifications` collection
  - `send_booking_email` → `email_outbox` collection
  - `update_billing_projection` → `billing_projections` collection
  - `update_reporting_projection` → `reporting_daily_events` + `reporting_funnel`
  - `dispatch_webhook` → `webhook_deliveries` collection
- **Admin API:** 8 endpoints under `/api/admin/outbox/` (health, stats, pending, failed, dispatch-table, trigger, retry, consumer-log)
- **Key Fix:** Celery's `send_task` doesn't work from async FastAPI context (kombu connection pool issue) — solved by pushing tasks directly to Redis via `redis.asyncio` with proper base64-encoded kombu message format
- **Testing:** 25/26 tests passed (1 skipped — no dead letter data to test)

## 2026-03-17 — Orphan Order Recovery
- Evidence-based migration script for 86 orphaned orders
- 8 high-confidence migrated, 78 quarantined for manual review
- Admin API for quarantine management (approve/reject/re-analyze/rollback)
- 12 unit tests, 38/38 API tests passed

## Previous — Tenant Isolation Hardening
- Enforced organization_id on all collections
- Middleware-level tenant boundary checks
- Booking truth model with state machine

## Previous — Router Domain Registry
- Domain-driven router organization
- Bootstrap pattern for modular router registration
