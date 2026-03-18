"""Webhook Delivery Tasks — Celery tasks for async webhook HTTP dispatch.

Architecture:
  - dispatch_webhook_event: Entry point from outbox consumer
  - execute_webhook_delivery: Performs actual HTTP POST to target URL
  - process_webhook_retries: Periodic task to pick up retries

Guarantees:
  - Idempotency: subscription_id + event_id unique constraint
  - At-least-once: retry with exponential backoff (6 attempts)
  - Circuit breaker: per-subscription automatic pause on repeated failures
  - HMAC-SHA256: signed payload for tamper detection
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from app.infrastructure.celery_app import celery_app

logger = logging.getLogger("tasks.webhook")


def _run_async(coro):
    """Run async coroutine from sync Celery context."""
    import asyncio
    import threading

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


# ── Main Dispatch Task ───────────────────────────────────────

@celery_app.task(
    name="app.tasks.webhook_tasks.dispatch_webhook_event",
    bind=True,
    max_retries=0,
    queue="webhook_queue",
)
def dispatch_webhook_event(
    self,
    event_id: str,
    event_type: str,
    payload: dict,
    organization_id: str,
    aggregate_id: str,
    aggregate_type: str,
):
    """Fan-out webhook event to all matching subscriptions.

    Called by outbox consumer for each event. Looks up active subscriptions
    and creates delivery records for each.
    """
    logger.info("[webhook] Dispatching %s for org %s", event_type, organization_id)

    try:
        result = _run_async(
            _async_dispatch_webhook_event(
                event_id, event_type, payload, organization_id, aggregate_id, aggregate_type
            )
        )
        return result
    except Exception as exc:
        logger.error("[webhook] Dispatch failed for event %s: %s", event_id, exc)
        return {"status": "error", "error": str(exc)}


async def _async_dispatch_webhook_event(
    event_id: str,
    event_type: str,
    payload: dict,
    organization_id: str,
    aggregate_id: str,
    aggregate_type: str,
) -> dict:
    from app.db import get_db
    from app.services.webhook_service import (
        create_delivery,
        is_circuit_open,
        ALLOWED_EVENTS,
    )

    db = await get_db()

    # Only dispatch for allowed webhook events
    if event_type not in ALLOWED_EVENTS:
        return {"status": "skipped", "reason": f"event_type {event_type} not in webhook scope"}

    # Find active subscriptions for this org + event type
    cursor = db.webhook_subscriptions.find({
        "organization_id": organization_id,
        "subscribed_events": event_type,
        "is_active": True,
    }, {"_id": 0})

    subscriptions = await cursor.to_list(50)

    deliveries_created = 0
    deliveries_skipped = 0

    for sub in subscriptions:
        sub_id = sub["subscription_id"]

        # Check circuit breaker
        if await is_circuit_open(db, sub_id):
            logger.warning("[webhook] Circuit open for subscription %s, skipping", sub_id)
            deliveries_skipped += 1
            continue

        # Create delivery record (idempotent — will fail on duplicate)
        delivery, err = await create_delivery(
            db, sub_id, organization_id, event_id, event_type
        )
        if err:
            logger.debug("[webhook] Delivery creation skipped: %s", err)
            deliveries_skipped += 1
            continue

        deliveries_created += 1

        # Enqueue immediate delivery execution
        execute_webhook_delivery.apply_async(
            kwargs={
                "delivery_id": delivery["delivery_id"],
                "subscription_id": sub_id,
                "event_id": event_id,
                "event_type": event_type,
                "payload": payload,
                "aggregate_id": aggregate_id,
                "aggregate_type": aggregate_type,
                "organization_id": organization_id,
                "attempt_number": 1,
            },
            queue="webhook_queue",
        )

    return {
        "status": "dispatched",
        "event_type": event_type,
        "subscriptions_found": len(subscriptions),
        "deliveries_created": deliveries_created,
        "deliveries_skipped": deliveries_skipped,
    }


# ── Delivery Execution Task ──────────────────────────────────

@celery_app.task(
    name="app.tasks.webhook_tasks.execute_webhook_delivery",
    bind=True,
    max_retries=0,
    queue="webhook_queue",
)
def execute_webhook_delivery(
    self,
    delivery_id: str,
    subscription_id: str,
    event_id: str,
    event_type: str,
    payload: dict,
    aggregate_id: str,
    aggregate_type: str,
    organization_id: str,
    attempt_number: int,
):
    """Execute a single webhook HTTP delivery attempt."""
    logger.info(
        "[webhook] Executing delivery %s attempt #%d",
        delivery_id, attempt_number,
    )

    try:
        result = _run_async(
            _async_execute_delivery(
                delivery_id, subscription_id, event_id, event_type,
                payload, aggregate_id, aggregate_type, organization_id,
                attempt_number,
            )
        )
        return result
    except Exception as exc:
        logger.error("[webhook] Delivery execution error %s: %s", delivery_id, exc)
        return {"status": "error", "error": str(exc)}


async def _async_execute_delivery(
    delivery_id: str,
    subscription_id: str,
    event_id: str,
    event_type: str,
    payload: dict,
    aggregate_id: str,
    aggregate_type: str,
    organization_id: str,
    attempt_number: int,
) -> dict:
    import httpx
    from app.db import get_db
    from app.services.webhook_service import (
        compute_signature,
        record_delivery_attempt,
        should_retry,
        update_circuit_state,
        MAX_RETRY_ATTEMPTS,
        RETRY_DELAYS,
        WEBHOOK_TIMEOUT_SECONDS,
    )

    db = await get_db()

    # Load subscription (need secret + target_url)
    sub = await db.webhook_subscriptions.find_one(
        {"subscription_id": subscription_id, "is_active": True},
        {"_id": 0, "target_url": 1, "secret": 1},
    )
    if not sub:
        await record_delivery_attempt(
            db, delivery_id, attempt_number, "failed",
            error="Subscription not found or inactive",
        )
        return {"status": "failed", "reason": "subscription_not_found"}

    target_url = sub["target_url"]
    secret = sub["secret"]

    # Build webhook payload
    now = datetime.now(timezone.utc)
    timestamp = int(now.timestamp())

    webhook_body = {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": now.isoformat(),
        "organization_id": organization_id,
        "entity_id": aggregate_id,
        "version": "v1",
        "data": payload.get("data", payload),
    }

    body_json = json.dumps(webhook_body, ensure_ascii=False, default=str)
    signature = compute_signature(secret, timestamp, body_json)

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Syroce-Webhooks/1.0",
        "X-Webhook-Event": event_type,
        "X-Webhook-Delivery-Id": delivery_id,
        "X-Webhook-Timestamp": str(timestamp),
        "X-Webhook-Signature": signature,
    }

    # Execute HTTP POST
    start_time = time.monotonic()
    response_code = None
    response_time_ms = None
    error_msg = None

    try:
        async with httpx.AsyncClient(
            timeout=WEBHOOK_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:
            response = await client.post(target_url, content=body_json, headers=headers)
            response_code = response.status_code
            response_time_ms = round((time.monotonic() - start_time) * 1000, 2)

            if response_code < 400:
                # Success
                await record_delivery_attempt(
                    db, delivery_id, attempt_number, "success",
                    response_status_code=response_code,
                    response_time_ms=response_time_ms,
                )
                await update_circuit_state(db, subscription_id, success=True)
                logger.info(
                    "[webhook] Delivery %s success: %d in %.1fms",
                    delivery_id, response_code, response_time_ms,
                )
                return {"status": "success", "http_status": response_code}
            else:
                error_msg = f"HTTP {response_code}"

    except httpx.TimeoutException:
        response_time_ms = round((time.monotonic() - start_time) * 1000, 2)
        error_msg = f"Timeout after {WEBHOOK_TIMEOUT_SECONDS}s"
    except httpx.ConnectError as e:
        response_time_ms = round((time.monotonic() - start_time) * 1000, 2)
        error_msg = f"Connection error: {e}"
    except Exception as e:
        response_time_ms = round((time.monotonic() - start_time) * 1000, 2)
        error_msg = f"Unexpected error: {e}"

    # Failed — decide retry
    await update_circuit_state(db, subscription_id, success=False)

    if attempt_number < MAX_RETRY_ATTEMPTS and should_retry(response_code, error_msg):
        # Schedule retry
        await record_delivery_attempt(
            db, delivery_id, attempt_number, "retrying",
            response_status_code=response_code,
            response_time_ms=response_time_ms,
            error=error_msg,
        )

        next_attempt = attempt_number + 1
        delay = RETRY_DELAYS[min(next_attempt - 1, len(RETRY_DELAYS) - 1)]

        execute_webhook_delivery.apply_async(
            kwargs={
                "delivery_id": delivery_id,
                "subscription_id": subscription_id,
                "event_id": event_id,
                "event_type": event_type,
                "payload": payload,
                "aggregate_id": aggregate_id,
                "aggregate_type": aggregate_type,
                "organization_id": organization_id,
                "attempt_number": next_attempt,
            },
            queue="webhook_queue",
            countdown=delay,
        )

        logger.info(
            "[webhook] Delivery %s retry #%d scheduled in %ds: %s",
            delivery_id, next_attempt, delay, error_msg,
        )
        return {"status": "retrying", "next_attempt": next_attempt, "delay_s": delay}
    else:
        # Max retries exhausted or non-retryable → dead
        final_status = "failed"
        await record_delivery_attempt(
            db, delivery_id, attempt_number, final_status,
            response_status_code=response_code,
            response_time_ms=response_time_ms,
            error=error_msg,
        )
        logger.warning(
            "[webhook] Delivery %s FAILED permanently after %d attempts: %s",
            delivery_id, attempt_number, error_msg,
        )
        return {"status": "failed", "reason": error_msg}


# ── Manual Replay Task ───────────────────────────────────────

@celery_app.task(
    name="app.tasks.webhook_tasks.replay_webhook_delivery",
    bind=True,
    max_retries=0,
    queue="webhook_queue",
)
def replay_webhook_delivery(self, delivery_id: str):
    """Manually replay a failed webhook delivery."""
    logger.info("[webhook] Manual replay for delivery %s", delivery_id)
    try:
        result = _run_async(_async_replay_delivery(delivery_id))
        return result
    except Exception as exc:
        logger.error("[webhook] Replay error %s: %s", delivery_id, exc)
        return {"status": "error", "error": str(exc)}


async def _async_replay_delivery(delivery_id: str) -> dict:
    from app.db import get_db
    db = await get_db()

    delivery = await db.webhook_deliveries.find_one(
        {"delivery_id": delivery_id},
        {"_id": 0},
    )
    if not delivery:
        return {"status": "error", "reason": "delivery_not_found"}

    if delivery["status"] not in ("failed",):
        return {"status": "error", "reason": f"Cannot replay delivery with status '{delivery['status']}'"}

    # Reset delivery status
    await db.webhook_deliveries.update_one(
        {"delivery_id": delivery_id},
        {"$set": {
            "status": "pending",
            "next_retry_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    # We need the original event payload — look up from outbox_events or reconstruct
    # For replay, we re-trigger the execution task
    event = await db.outbox_events.find_one(
        {"event_id": delivery["event_id"]},
        {"_id": 0, "payload": 1, "aggregate_id": 1, "aggregate_type": 1},
    )

    payload = event.get("payload", {}) if event else {}
    aggregate_id = event.get("aggregate_id", "") if event else ""
    aggregate_type = event.get("aggregate_type", "booking") if event else "booking"

    execute_webhook_delivery.apply_async(
        kwargs={
            "delivery_id": delivery_id,
            "subscription_id": delivery["subscription_id"],
            "event_id": delivery["event_id"],
            "event_type": delivery["event_type"],
            "payload": payload,
            "aggregate_id": aggregate_id,
            "aggregate_type": aggregate_type,
            "organization_id": delivery["organization_id"],
            "attempt_number": delivery.get("attempt_number", 0) + 1,
        },
        queue="webhook_queue",
    )

    return {"status": "replayed", "delivery_id": delivery_id}
