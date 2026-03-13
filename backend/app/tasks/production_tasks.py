"""Real Celery Task Bodies — Production-grade async task execution.

Queues:
- default: general tasks
- voucher: voucher generation
- email: email delivery
- alerts: Slack/webhook alerts
- maintenance: cleanup, cache refresh
- incidents: incident escalation

Each task defines: queue, retries, timeout, idempotency, DLQ behavior.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from app.bootstrap.worker_app import celery_app

logger = logging.getLogger("celery.tasks.production")

# Helper to run async code in sync celery tasks
def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _get_db():
    """Get async MongoDB connection for Celery tasks."""
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "syroce")
    client = AsyncIOMotorClient(mongo_url)
    return client[db_name]


# ============================================================================
# VOUCHER GENERATION — Queue: voucher
# ============================================================================

@celery_app.task(
    name="tasks.generate_voucher",
    bind=True,
    queue="voucher",
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=120,
    time_limit=180,
    acks_late=True,
)
def generate_voucher_task(self, org_id: str, booking_id: str, locale: str = "tr", brand: dict = None, actor: str = "system"):
    """Generate PDF voucher for a booking."""
    logger.info("Generating voucher for booking=%s org=%s", booking_id, org_id)
    try:
        async def _gen():
            db = await _get_db()
            from app.services.voucher_service import generate_voucher
            return await generate_voucher(db, org_id, booking_id, brand=brand, locale=locale, actor=actor)
        result = _run_async(_gen())
        if result.get("error"):
            raise Exception(result["error"])
        logger.info("Voucher generated: %s", result.get("voucher_id"))
        return result
    except Exception as exc:
        logger.error("Voucher generation failed for booking=%s: %s", booking_id, exc)
        raise self.retry(exc=exc)


# ============================================================================
# EMAIL DELIVERY — Queue: email
# ============================================================================

@celery_app.task(
    name="tasks.send_email",
    bind=True,
    queue="email",
    max_retries=5,
    default_retry_delay=60,
    soft_time_limit=30,
    time_limit=60,
    acks_late=True,
)
def send_email_task(self, org_id: str, to: str, subject: str, html: str, from_email: str = None, reply_to: str = None):
    """Send email via Resend."""
    logger.info("Sending email to=%s subject=%s org=%s", to, subject[:50], org_id)
    try:
        async def _send():
            db = await _get_db()
            from app.services.delivery_service import send_email
            return await send_email(db, org_id, to, subject, html, from_email=from_email, reply_to=reply_to)
        result = _run_async(_send())
        if result.get("status") == "failed":
            raise Exception(result.get("error", "Email send failed"))
        logger.info("Email sent: delivery_id=%s", result.get("delivery_id"))
        return result
    except Exception as exc:
        logger.error("Email send failed to=%s: %s", to, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="tasks.send_voucher_email",
    bind=True,
    queue="email",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=60,
    time_limit=120,
    acks_late=True,
)
def send_voucher_email_task(self, org_id: str, booking_id: str, to: str, locale: str = "tr"):
    """Generate voucher and send it via email."""
    logger.info("Sending voucher email for booking=%s to=%s", booking_id, to)
    try:
        async def _work():
            db = await _get_db()
            from app.services.voucher_service import generate_voucher
            voucher = await generate_voucher(db, org_id, booking_id, locale=locale, actor="email_task")
            if voucher.get("error"):
                raise Exception(voucher["error"])
            from app.services.delivery_service import send_email
            html = f"""<h2>Booking Voucher</h2>
            <p>Your voucher for booking <strong>{booking_id}</strong> has been generated.</p>
            <p>Voucher ID: {voucher.get('voucher_id', 'N/A')}</p>
            <p>Please contact us if you have any questions.</p>"""
            return await send_email(db, org_id, to, f"Booking Voucher - {booking_id}", html)
        result = _run_async(_work())
        return result
    except Exception as exc:
        logger.error("Voucher email failed booking=%s: %s", booking_id, exc)
        raise self.retry(exc=exc)


# ============================================================================
# SLACK / WEBHOOK ALERTS — Queue: alerts
# ============================================================================

@celery_app.task(
    name="tasks.send_slack_alert",
    bind=True,
    queue="alerts",
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=15,
    time_limit=30,
    acks_late=True,
)
def send_slack_alert_task(self, org_id: str, message: str, webhook_url: str = None, channel: str = None):
    """Send Slack alert."""
    logger.info("Sending Slack alert for org=%s", org_id)
    try:
        async def _send():
            db = await _get_db()
            from app.services.delivery_service import send_slack_alert
            return await send_slack_alert(db, org_id, message, webhook_url=webhook_url, channel=channel)
        result = _run_async(_send())
        return result
    except Exception as exc:
        logger.error("Slack alert failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="tasks.send_webhook",
    bind=True,
    queue="alerts",
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=15,
    time_limit=30,
    acks_late=True,
)
def send_webhook_task(self, org_id: str, url: str, payload: dict, headers: dict = None):
    """Send webhook alert."""
    logger.info("Sending webhook to=%s org=%s", url, org_id)
    try:
        async def _send():
            db = await _get_db()
            from app.services.delivery_service import send_webhook
            return await send_webhook(db, org_id, url, payload, headers=headers)
        result = _run_async(_send())
        return result
    except Exception as exc:
        logger.error("Webhook failed to=%s: %s", url, exc)
        raise self.retry(exc=exc)


# ============================================================================
# INCIDENT ESCALATION — Queue: incidents
# ============================================================================

@celery_app.task(
    name="tasks.escalate_incident",
    bind=True,
    queue="incidents",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=30,
    time_limit=60,
    acks_late=True,
)
def escalate_incident_task(self, org_id: str, incident_id: str, severity: str, supplier_code: str, details: dict = None):
    """Escalate incident: log + notify."""
    logger.info("Escalating incident=%s severity=%s supplier=%s", incident_id, severity, supplier_code)
    try:
        async def _work():
            db = await _get_db()
            from app.services.delivery_service import send_slack_alert, send_email
            msg = f"[INCIDENT] {severity.upper()} — Supplier: {supplier_code}\nIncident ID: {incident_id}\nDetails: {str(details)[:300]}"
            await send_slack_alert(db, org_id, msg)
            ops_email = os.environ.get("OPS_ALERT_EMAIL")
            if ops_email:
                html = f"<h3>Supplier Incident Alert</h3><p><strong>Severity:</strong> {severity}</p><p><strong>Supplier:</strong> {supplier_code}</p><p><strong>Incident:</strong> {incident_id}</p><pre>{str(details)[:500]}</pre>"
                await send_email(db, org_id, ops_email, f"[{severity.upper()}] Supplier Incident - {supplier_code}", html)
            return {"escalated": True, "incident_id": incident_id}
        result = _run_async(_work())
        return result
    except Exception as exc:
        logger.error("Incident escalation failed: %s", exc)
        raise self.retry(exc=exc)


# ============================================================================
# CLEANUP JOBS — Queue: maintenance
# ============================================================================

@celery_app.task(
    name="tasks.cleanup_expired_holds",
    queue="maintenance",
    soft_time_limit=300,
    time_limit=600,
)
def cleanup_expired_holds_task():
    """Clean up expired booking holds."""
    logger.info("Running expired hold cleanup")
    try:
        async def _work():
            from datetime import timedelta
            db = await _get_db()
            cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
            result = await db.bookings.update_many(
                {"supplier_state": "hold_created", "hold_expires_at": {"$lt": cutoff}},
                {"$set": {"supplier_state": "hold_expired", "updated_at": datetime.now(timezone.utc)}},
            )
            logger.info("Cleaned up %d expired holds", result.modified_count)
            return {"cleaned": result.modified_count}
        return _run_async(_work())
    except Exception as exc:
        logger.error("Hold cleanup failed: %s", exc)
        return {"error": str(exc)}


@celery_app.task(
    name="tasks.cleanup_stale_orchestration_runs",
    queue="maintenance",
    soft_time_limit=300,
    time_limit=600,
)
def cleanup_stale_orchestration_runs_task():
    """Clean up stale orchestration runs older than 24h that are still 'started'."""
    logger.info("Cleaning up stale orchestration runs")
    try:
        async def _work():
            from datetime import timedelta
            db = await _get_db()
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            result = await db.booking_orchestration_runs.update_many(
                {"status": "started", "created_at": {"$lt": cutoff}},
                {"$set": {"status": "timed_out", "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            logger.info("Cleaned up %d stale runs", result.modified_count)
            return {"cleaned": result.modified_count}
        return _run_async(_work())
    except Exception as exc:
        logger.error("Stale run cleanup failed: %s", exc)
        return {"error": str(exc)}


@celery_app.task(
    name="tasks.refresh_supplier_status_cache",
    queue="maintenance",
    soft_time_limit=60,
    time_limit=120,
)
def refresh_supplier_status_cache_task():
    """Refresh in-memory supplier status cache."""
    logger.info("Refreshing supplier status cache")
    try:
        async def _work():
            db = await _get_db()
            statuses = await db.rel_supplier_status.find({}, {"_id": 0}).to_list(500)
            from app.domain.reliability.pipeline import _supplier_status_cache
            import time
            _supplier_status_cache.clear()
            for s in statuses:
                _supplier_status_cache[s["supplier_code"]] = s
            from app.domain.reliability import pipeline
            pipeline._cache_ts = time.monotonic()
            logger.info("Refreshed %d supplier statuses", len(statuses))
            return {"refreshed": len(statuses)}
        return _run_async(_work())
    except Exception as exc:
        logger.error("Cache refresh failed: %s", exc)
        return {"error": str(exc)}


# ============================================================================
# STALE CACHE REFRESH — Queue: maintenance
# ============================================================================

@celery_app.task(
    name="tasks.cleanup_old_metrics",
    queue="maintenance",
    soft_time_limit=300,
    time_limit=600,
)
def cleanup_old_metrics_task(days: int = 30):
    """Clean up old reliability metrics older than N days."""
    logger.info("Cleaning up metrics older than %d days", days)
    try:
        async def _work():
            from datetime import timedelta
            db = await _get_db()
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            result = await db.rel_metrics.delete_many({"timestamp": {"$lt": cutoff}})
            events_result = await db.rel_resilience_events.delete_many({"timestamp": {"$lt": cutoff}})
            logger.info("Deleted %d old metrics, %d old events", result.deleted_count, events_result.deleted_count)
            return {"metrics_deleted": result.deleted_count, "events_deleted": events_result.deleted_count}
        return _run_async(_work())
    except Exception as exc:
        logger.error("Metrics cleanup failed: %s", exc)
        return {"error": str(exc)}
