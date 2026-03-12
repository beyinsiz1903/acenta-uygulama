"""PART 6 — Real-Time Alerting Engine.

Alert rules:
  - Supplier health degradation (score drops below threshold)
  - Booking failure spike
  - Payment errors
  - Circuit breaker trips
  - Failover chain exhaustion

Alert channels:
  - In-app (stored in DB)
  - Slack webhook (configurable)
  - Email (configurable)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("suppliers.ops.alerting")


class AlertSeverity:
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertType:
    HEALTH_DEGRADED = "supplier_health_degraded"
    BOOKING_FAILURE_SPIKE = "booking_failure_spike"
    PAYMENT_ERROR = "payment_error"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    FAILOVER_EXHAUSTED = "failover_exhausted"
    STUCK_BOOKING = "stuck_booking"
    CONFIRMATION_FAILURE = "confirmation_failure"


async def create_alert(
    db,
    organization_id: str,
    *,
    alert_type: str,
    severity: str = AlertSeverity.WARNING,
    title: str,
    description: str = "",
    supplier_code: Optional[str] = None,
    booking_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create an alert and dispatch to configured channels."""

    now = datetime.now(timezone.utc)
    alert_id = str(uuid.uuid4())

    alert = {
        "alert_id": alert_id,
        "organization_id": organization_id,
        "alert_type": alert_type,
        "severity": severity,
        "title": title,
        "description": description,
        "supplier_code": supplier_code,
        "booking_id": booking_id,
        "metadata": metadata or {},
        "status": "active",
        "acknowledged": False,
        "acknowledged_by": None,
        "acknowledged_at": None,
        "resolved": False,
        "resolved_at": None,
        "created_at": now,
    }

    await db.ops_alerts.insert_one({"_id": alert_id, **alert})

    # Dispatch to channels
    await _dispatch_alert(db, organization_id, alert)

    logger.info("Alert created: [%s] %s — %s", severity, alert_type, title)
    alert.pop("_id", None)
    return alert


async def _dispatch_alert(
    db,
    organization_id: str,
    alert: Dict[str, Any],
):
    """Dispatch alert to configured channels (Slack, email)."""

    # Get org alert config
    config = await db.ops_alert_config.find_one(
        {"organization_id": organization_id}, {"_id": 0}
    )
    if not config:
        return

    # Slack webhook
    slack_url = config.get("slack_webhook_url")
    if slack_url:
        try:
            await _send_slack_alert(slack_url, alert)
        except Exception as e:
            logger.warning("Slack alert dispatch failed: %s", e)

    # Email recipients
    email_recipients = config.get("email_recipients", [])
    if email_recipients:
        try:
            await _queue_email_alert(db, email_recipients, alert)
        except Exception as e:
            logger.warning("Email alert dispatch failed: %s", e)


async def _send_slack_alert(webhook_url: str, alert: Dict[str, Any]):
    """Send alert to Slack via webhook."""
    import httpx

    severity_emoji = {
        "info": "info_circle",
        "warning": "warning",
        "critical": "red_circle",
        "emergency": "rotating_light",
    }
    emoji = severity_emoji.get(alert["severity"], "bell")

    payload = {
        "text": f":{emoji}: *[{alert['severity'].upper()}]* {alert['title']}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f":{emoji}: *[{alert['severity'].upper()}]* {alert['title']}\n"
                        f"Type: `{alert['alert_type']}`\n"
                        f"{alert.get('description', '')}"
                    ),
                },
            }
        ],
    }

    if alert.get("supplier_code"):
        payload["blocks"].append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Supplier: `{alert['supplier_code']}`"}
            ],
        })

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(webhook_url, json=payload)
        resp.raise_for_status()


async def _queue_email_alert(
    db,
    recipients: List[str],
    alert: Dict[str, Any],
):
    """Queue email alert for async sending."""
    now = datetime.now(timezone.utc)
    await db.ops_email_queue.insert_one({
        "type": "alert",
        "recipients": recipients,
        "subject": f"[{alert['severity'].upper()}] {alert['title']}",
        "body": alert.get("description", ""),
        "alert_id": alert["alert_id"],
        "status": "queued",
        "created_at": now,
    })


async def list_alerts(
    db,
    organization_id: str,
    *,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List alerts with optional filters."""

    query: Dict[str, Any] = {"organization_id": organization_id}
    if status:
        query["status"] = status
    if severity:
        query["severity"] = severity
    if alert_type:
        query["alert_type"] = alert_type

    cursor = db.ops_alerts.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def acknowledge_alert(
    db,
    organization_id: str,
    alert_id: str,
    *,
    acknowledged_by: str,
) -> Dict[str, Any]:
    """Acknowledge an alert."""

    now = datetime.now(timezone.utc)
    result = await db.ops_alerts.find_one_and_update(
        {"_id": alert_id, "organization_id": organization_id},
        {
            "$set": {
                "acknowledged": True,
                "acknowledged_by": acknowledged_by,
                "acknowledged_at": now,
                "status": "acknowledged",
            }
        },
        return_document=True,
    )
    if not result:
        return {"error": "alert_not_found"}
    result.pop("_id", None)
    return result


async def resolve_alert(
    db,
    organization_id: str,
    alert_id: str,
) -> Dict[str, Any]:
    """Resolve an alert."""

    now = datetime.now(timezone.utc)
    result = await db.ops_alerts.find_one_and_update(
        {"_id": alert_id, "organization_id": organization_id},
        {
            "$set": {
                "resolved": True,
                "resolved_at": now,
                "status": "resolved",
            }
        },
        return_document=True,
    )
    if not result:
        return {"error": "alert_not_found"}
    result.pop("_id", None)
    return result


async def configure_alert_channels(
    db,
    organization_id: str,
    *,
    slack_webhook_url: Optional[str] = None,
    email_recipients: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Configure alert dispatch channels for an organization."""

    now = datetime.now(timezone.utc)
    update: Dict[str, Any] = {"organization_id": organization_id, "updated_at": now}
    if slack_webhook_url is not None:
        update["slack_webhook_url"] = slack_webhook_url
    if email_recipients is not None:
        update["email_recipients"] = email_recipients

    await db.ops_alert_config.update_one(
        {"organization_id": organization_id},
        {"$set": update},
        upsert=True,
    )

    return {"status": "ok", "organization_id": organization_id}


async def evaluate_alert_rules(
    db,
    organization_id: str,
) -> List[Dict[str, Any]]:
    """Evaluate all alert rules and fire alerts if thresholds are breached.

    Called periodically by scheduler or on-demand.
    """

    now = datetime.now(timezone.utc)
    fired_alerts = []

    # Rule 1: Check for stuck bookings
    from app.suppliers.operations.incidents import detect_stuck_bookings
    stuck = await detect_stuck_bookings(db, organization_id)
    for s in stuck[:5]:  # max 5 alerts
        if s["severity"] == "critical":
            alert = await create_alert(
                db, organization_id,
                alert_type=AlertType.STUCK_BOOKING,
                severity=AlertSeverity.CRITICAL,
                title=f"Stuck booking: {s['booking_id']}",
                description=f"Booking stuck in {s['supplier_state']} for {s['stuck_minutes']}min",
                booking_id=s["booking_id"],
                supplier_code=s.get("supplier_code"),
            )
            fired_alerts.append(alert)

    # Rule 2: Check supplier health
    health_cursor = db.supplier_ecosystem_health.find(
        {"organization_id": organization_id, "state": {"$in": ["critical", "disabled"]}},
        {"_id": 0},
    )
    async for h in health_cursor:
        alert = await create_alert(
            db, organization_id,
            alert_type=AlertType.HEALTH_DEGRADED,
            severity=AlertSeverity.CRITICAL if h["state"] == "disabled" else AlertSeverity.WARNING,
            title=f"Supplier {h['supplier_code']} health: {h['state']}",
            description=f"Health score: {h.get('score', 'N/A')}",
            supplier_code=h["supplier_code"],
        )
        fired_alerts.append(alert)

    # Rule 3: Recent booking failure spike
    window_start = now - timedelta(minutes=15)
    fail_count = await db.booking_orchestration_runs.count_documents({
        "organization_id": organization_id,
        "status": "failed",
        "created_at": {"$gte": window_start},
    })
    if fail_count >= 3:
        alert = await create_alert(
            db, organization_id,
            alert_type=AlertType.BOOKING_FAILURE_SPIKE,
            severity=AlertSeverity.CRITICAL,
            title=f"Booking failure spike: {fail_count} failures in 15min",
            metadata={"failure_count": fail_count, "window_minutes": 15},
        )
        fired_alerts.append(alert)

    return fired_alerts
