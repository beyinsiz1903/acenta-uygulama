"""First-wave Outbox Consumers — Idempotent side-effect handlers.

Architecture rule (CTO-mandated):
  - These consumers NEVER change booking state.
  - They only produce side effects: notifications, emails, projections, webhooks.

Idempotency:
  - Each consumer checks outbox_consumer_results for the (event_id, handler) pair.
  - If already processed, it returns immediately (no-op).
  - This ensures at-least-once delivery is safe.

Consumers:
  1. send_booking_notification  — In-app notification record
  2. send_booking_email         — Email dispatch (via email service)
  3. update_billing_projection  — Revenue/billing aggregation
  4. update_reporting_projection — Funnel/KPI aggregation
  5. dispatch_webhook           — External webhook delivery
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.infrastructure.celery_app import celery_app

logger = logging.getLogger("tasks.outbox_consumers")


# ── Idempotency helper ───────────────────────────────────────

def _run_async(coro):
    """Run an async coroutine from sync Celery task context.

    Uses a per-thread persistent event loop to avoid 'Event loop is closed' errors
    with Motor's cached connections.
    """
    import asyncio
    import threading

    # Use a thread-local persistent loop
    _local = getattr(_run_async, '_local', None)
    if _local is None:
        _local = threading.local()
        _run_async._local = _local

    loop = getattr(_local, 'loop', None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _local.loop = loop

    return loop.run_until_complete(coro)


async def _is_already_processed(db, event_id: str, handler: str) -> bool:
    """Check idempotency — two-layer: Redis fast-path + MongoDB unique constraint.

    Layer 1 (Redis): O(1) check via SET key — covers 99% of duplicate attempts
    Layer 2 (MongoDB): unique index on (event_id, handler) — catches race conditions
    """
    # Layer 1: Redis fast-path
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if r:
            key = f"idempotent:{event_id}:{handler}"
            if await r.exists(key):
                return True
    except Exception:
        pass  # Fall through to DB check

    # Layer 2: MongoDB (authoritative source)
    existing = await db.outbox_consumer_results.find_one({
        "event_id": event_id,
        "handler": handler,
    })
    return existing is not None


async def _mark_processed(
    db, event_id: str, handler: str, result: dict
) -> None:
    """Record that this handler has processed this event.

    Uses MongoDB upsert with unique index as the authoritative lock.
    Also sets a Redis key for fast-path dedup on subsequent attempts.
    TTL: 7 days (events older than this won't be replayed).
    """
    from pymongo.errors import DuplicateKeyError

    try:
        await db.outbox_consumer_results.insert_one({
            "event_id": event_id,
            "handler": handler,
            "result": result,
            "processed_at": datetime.now(timezone.utc),
        })
    except DuplicateKeyError:
        logger.warning("Duplicate processing attempt: event=%s handler=%s", event_id, handler)
        return

    # Set Redis fast-path key (TTL 7 days)
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if r:
            key = f"idempotent:{event_id}:{handler}"
            await r.set(key, "1", ex=7 * 24 * 3600)
    except Exception:
        pass  # Non-critical — DB is the authority


# ── 1. Notification Consumer ─────────────────────────────────

@celery_app.task(
    name="app.tasks.outbox_consumers.send_booking_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
    queue="notification_queue",
)
def send_booking_notification(
    self,
    event_id: str,
    event_type: str,
    payload: dict,
    organization_id: str,
    aggregate_id: str,
    aggregate_type: str,
):
    """Create an in-app notification record for the booking event.

    Writes to `notifications` collection — consumed by frontend notification center.
    """
    handler = "send_booking_notification"
    logger.info("[%s] Processing %s for %s", handler, event_type, aggregate_id)

    try:
        result = _run_async(
            _async_send_booking_notification(
                event_id, event_type, payload, organization_id, aggregate_id
            )
        )
        return result
    except Exception as exc:
        logger.error("[%s] Failed for event %s: %s", handler, event_id, exc)
        raise self.retry(exc=exc)


async def _async_send_booking_notification(
    event_id: str, event_type: str, payload: dict,
    organization_id: str, aggregate_id: str,
) -> dict:
    from app.db import get_db
    db = await get_db()

    if await _is_already_processed(db, event_id, "send_booking_notification"):
        return {"status": "skipped", "reason": "idempotent_duplicate"}

    data = payload.get("data", {})
    actor = payload.get("actor", {})

    # Map event type to notification message
    messages = {
        "booking.confirmed": "Rezervasyon onaylandi",
        "booking.cancelled": "Rezervasyon iptal edildi",
        "booking.completed": "Rezervasyon tamamlandi",
        "booking.quoted": "Teklif hazirlandi",
        "booking.amended": "Rezervasyon guncellendi",
        "booking.refunded": "Iade islemi tamamlandi",
        "booking.ticketed": "Bilet hazirlandi",
        "booking.vouchered": "Voucher hazirlandi",
        "payment.completed": "Odeme alindi",
        "payment.failed": "Odeme basarisiz",
    }
    message = messages.get(event_type, f"Booking event: {event_type}")

    notification = {
        "organization_id": organization_id,
        "booking_id": aggregate_id,
        "event_type": event_type,
        "message": message,
        "actor": actor,
        "status_from": data.get("from_status", ""),
        "status_to": data.get("status", ""),
        "read": False,
        "created_at": datetime.now(timezone.utc),
        "source": "outbox_consumer",
    }

    await db.booking_notifications.insert_one(notification)
    await _mark_processed(db, event_id, "send_booking_notification", {"status": "created"})

    logger.info("[notification] Created notification for %s: %s", aggregate_id, event_type)
    return {"status": "created", "event_type": event_type, "booking_id": aggregate_id}


# ── 2. Email Consumer ────────────────────────────────────────

@celery_app.task(
    name="app.tasks.outbox_consumers.send_booking_email",
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    retry_backoff=True,
    queue="notification_queue",
)
def send_booking_email(
    self,
    event_id: str,
    event_type: str,
    payload: dict,
    organization_id: str,
    aggregate_id: str,
    aggregate_type: str,
):
    """Send transactional email for booking event.

    Uses email_outbox collection for email service to pick up and send.
    """
    handler = "send_booking_email"
    logger.info("[%s] Processing %s for %s", handler, event_type, aggregate_id)

    try:
        result = _run_async(
            _async_send_booking_email(
                event_id, event_type, payload, organization_id, aggregate_id
            )
        )
        return result
    except Exception as exc:
        logger.error("[%s] Failed for event %s: %s", handler, event_id, exc)
        raise self.retry(exc=exc)


async def _async_send_booking_email(
    event_id: str, event_type: str, payload: dict,
    organization_id: str, aggregate_id: str,
) -> dict:
    from app.db import get_db
    db = await get_db()

    if await _is_already_processed(db, event_id, "send_booking_email"):
        return {"status": "skipped", "reason": "idempotent_duplicate"}

    data = payload.get("data", {})
    actor = payload.get("actor", {})

    # Map event type to email template
    templates = {
        "booking.confirmed": "booking_confirmed",
        "booking.cancelled": "booking_cancelled",
        "booking.completed": "booking_completed",
        "booking.refunded": "booking_refunded",
    }
    template = templates.get(event_type)
    if not template:
        await _mark_processed(db, event_id, "send_booking_email", {"status": "no_template"})
        return {"status": "no_template", "event_type": event_type}

    # Write to email_outbox for the email service to pick up
    email_record = {
        "organization_id": organization_id,
        "booking_id": aggregate_id,
        "event_type": event_type,
        "template": template,
        "context": {
            "booking_id": aggregate_id,
            "status": data.get("status", ""),
            "from_status": data.get("from_status", ""),
            "actor_email": actor.get("email", ""),
        },
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
        "source": "outbox_consumer",
    }

    await db.email_outbox.insert_one(email_record)
    await _mark_processed(db, event_id, "send_booking_email", {"status": "queued", "template": template})

    logger.info("[email] Queued email for %s: template=%s", aggregate_id, template)
    return {"status": "queued", "template": template, "booking_id": aggregate_id}


# ── 3. Billing Projection Consumer ───────────────────────────

@celery_app.task(
    name="app.tasks.outbox_consumers.update_billing_projection",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    queue="reports",
)
def update_billing_projection(
    self,
    event_id: str,
    event_type: str,
    payload: dict,
    organization_id: str,
    aggregate_id: str,
    aggregate_type: str,
):
    """Update billing/revenue projection based on booking events."""
    handler = "update_billing_projection"
    logger.info("[%s] Processing %s for %s", handler, event_type, aggregate_id)

    try:
        result = _run_async(
            _async_update_billing_projection(
                event_id, event_type, payload, organization_id, aggregate_id
            )
        )
        return result
    except Exception as exc:
        logger.error("[%s] Failed for event %s: %s", handler, event_id, exc)
        raise self.retry(exc=exc)


async def _async_update_billing_projection(
    event_id: str, event_type: str, payload: dict,
    organization_id: str, aggregate_id: str,
) -> dict:
    from app.db import get_db
    db = await get_db()

    if await _is_already_processed(db, event_id, "update_billing_projection"):
        return {"status": "skipped", "reason": "idempotent_duplicate"}

    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")

    # Determine projection delta
    delta_map = {
        "booking.confirmed": {"confirmed_count": 1},
        "booking.cancelled": {"cancelled_count": 1, "confirmed_count": -1},
        "booking.completed": {"completed_count": 1},
        "booking.amended": {"amended_count": 1},
        "booking.refunded": {"refunded_count": 1},
        "payment.completed": {"payments_received": 1},
    }
    deltas = delta_map.get(event_type, {})

    if deltas:
        inc_fields = {f"projections.{k}": v for k, v in deltas.items()}
        await db.billing_projections.update_one(
            {"organization_id": organization_id, "month": month_key},
            {
                "$inc": inc_fields,
                "$set": {"updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    await _mark_processed(db, event_id, "update_billing_projection", {
        "status": "updated", "deltas": deltas, "month": month_key,
    })

    logger.info("[billing] Updated projection for org %s, month %s", organization_id, month_key)
    return {"status": "updated", "deltas": deltas}


# ── 4. Reporting Projection Consumer ─────────────────────────

@celery_app.task(
    name="app.tasks.outbox_consumers.update_reporting_projection",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    queue="reports",
)
def update_reporting_projection(
    self,
    event_id: str,
    event_type: str,
    payload: dict,
    organization_id: str,
    aggregate_id: str,
    aggregate_type: str,
):
    """Update reporting/funnel projections based on booking events."""
    handler = "update_reporting_projection"
    logger.info("[%s] Processing %s for %s", handler, event_type, aggregate_id)

    try:
        result = _run_async(
            _async_update_reporting_projection(
                event_id, event_type, payload, organization_id, aggregate_id
            )
        )
        return result
    except Exception as exc:
        logger.error("[%s] Failed for event %s: %s", handler, event_id, exc)
        raise self.retry(exc=exc)


async def _async_update_reporting_projection(
    event_id: str, event_type: str, payload: dict,
    organization_id: str, aggregate_id: str,
) -> dict:
    from app.db import get_db
    db = await get_db()

    if await _is_already_processed(db, event_id, "update_reporting_projection"):
        return {"status": "skipped", "reason": "idempotent_duplicate"}

    now = datetime.now(timezone.utc)
    date_key = now.strftime("%Y-%m-%d")

    # Increment daily event counter
    await db.reporting_daily_events.update_one(
        {
            "organization_id": organization_id,
            "date": date_key,
        },
        {
            "$inc": {
                f"events.{event_type}": 1,
                "events.total": 1,
            },
            "$set": {"updated_at": now},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    # Update funnel stage counts
    funnel_stage_map = {
        "booking.quoted": "quoted",
        "booking.confirmed": "confirmed",
        "booking.completed": "completed",
        "booking.cancelled": "cancelled",
    }
    stage = funnel_stage_map.get(event_type)
    if stage:
        await db.reporting_funnel.update_one(
            {"organization_id": organization_id, "month": now.strftime("%Y-%m")},
            {
                "$inc": {f"stages.{stage}": 1},
                "$set": {"updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    await _mark_processed(db, event_id, "update_reporting_projection", {
        "status": "updated", "date": date_key, "stage": stage,
    })

    logger.info("[reporting] Updated daily events for org %s, date %s", organization_id, date_key)
    return {"status": "updated", "date": date_key}


# ── 5. Webhook Dispatcher Consumer ───────────────────────────
# Delegates to the productized webhook system (app.tasks.webhook_tasks)

@celery_app.task(
    name="app.tasks.outbox_consumers.dispatch_webhook",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
    queue="notification_queue",
)
def dispatch_webhook(
    self,
    event_id: str,
    event_type: str,
    payload: dict,
    organization_id: str,
    aggregate_id: str,
    aggregate_type: str,
):
    """Dispatch event to productized webhook system.

    This consumer acts as a bridge — it delegates to the new webhook_tasks
    which handle subscription lookup, HMAC signing, retry, idempotency,
    and circuit breakers.
    """
    handler = "dispatch_webhook"
    logger.info("[%s] Delegating %s to webhook system for %s", handler, event_type, aggregate_id)

    try:
        result = _run_async(
            _async_dispatch_webhook(
                event_id, event_type, payload, organization_id, aggregate_id, aggregate_type
            )
        )
        return result
    except Exception as exc:
        logger.error("[%s] Failed for event %s: %s", handler, event_id, exc)
        raise self.retry(exc=exc)


async def _async_dispatch_webhook(
    event_id: str, event_type: str, payload: dict,
    organization_id: str, aggregate_id: str, aggregate_type: str,
) -> dict:
    from app.db import get_db
    db = await get_db()

    if await _is_already_processed(db, event_id, "dispatch_webhook"):
        return {"status": "skipped", "reason": "idempotent_duplicate"}

    # Delegate to productized webhook task
    from app.tasks.webhook_tasks import dispatch_webhook_event
    dispatch_webhook_event.apply_async(
        kwargs={
            "event_id": event_id,
            "event_type": event_type,
            "payload": payload,
            "organization_id": organization_id,
            "aggregate_id": aggregate_id,
            "aggregate_type": aggregate_type,
        },
        queue="webhook_queue",
    )

    await _mark_processed(db, event_id, "dispatch_webhook", {
        "status": "delegated_to_webhook_system",
    })

    logger.info("[webhook] Delegated %s to webhook system for event %s", event_type, event_id)
    return {"status": "delegated", "event_type": event_type}
