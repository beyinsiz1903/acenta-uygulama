"""Notification Delivery Service — Multi-channel notification dispatch.

Primary: Resend (email)
Secondary: Webhook/Slack alerts

Provides provider abstraction, retry logic, and audit visibility.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("notification.delivery")


async def send_email(
    db,
    org_id: str,
    to: str | list[str],
    subject: str,
    html: str,
    *,
    from_email: str | None = None,
    reply_to: str | None = None,
) -> dict[str, Any]:
    """Send email via Resend."""
    import resend

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        return await _log_delivery(
            db, org_id, "email", "resend", to, subject,
            status="skipped", error="RESEND_API_KEY not configured",
        )

    resend.api_key = api_key
    sender = from_email or os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
    recipients = [to] if isinstance(to, str) else to

    params: dict[str, Any] = {
        "from": sender,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if reply_to:
        params["reply_to"] = reply_to

    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        email_id = result.get("id") if isinstance(result, dict) else str(result)
        return await _log_delivery(
            db, org_id, "email", "resend", recipients, subject,
            status="sent", provider_id=email_id,
        )
    except Exception as exc:
        logger.error("Resend email failed: %s", exc)
        return await _log_delivery(
            db, org_id, "email", "resend", recipients, subject,
            status="failed", error=str(exc)[:500],
        )


async def send_webhook(
    db, org_id: str, url: str, payload: dict,
    *,
    headers: dict | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    """Send webhook POST request."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers or {})
            return await _log_delivery(
                db, org_id, "webhook", "http", url, "webhook_event",
                status="sent" if resp.status_code < 400 else "failed",
                provider_id=str(resp.status_code),
                error=resp.text[:300] if resp.status_code >= 400 else None,
            )
    except Exception as exc:
        logger.error("Webhook failed to %s: %s", url, exc)
        return await _log_delivery(
            db, org_id, "webhook", "http", url, "webhook_event",
            status="failed", error=str(exc)[:300],
        )


async def send_slack_alert(
    db, org_id: str, message: str,
    *,
    webhook_url: str | None = None,
    channel: str | None = None,
) -> dict[str, Any]:
    """Send Slack alert via incoming webhook."""
    url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        return await _log_delivery(
            db, org_id, "slack", "slack_webhook", channel or "default", message[:100],
            status="skipped", error="SLACK_WEBHOOK_URL not configured",
        )

    import httpx
    payload = {"text": message}
    if channel:
        payload["channel"] = channel

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            return await _log_delivery(
                db, org_id, "slack", "slack_webhook", channel or "default", message[:100],
                status="sent" if resp.status_code == 200 else "failed",
                error=resp.text[:200] if resp.status_code != 200 else None,
            )
    except Exception as exc:
        logger.error("Slack alert failed: %s", exc)
        return await _log_delivery(
            db, org_id, "slack", "slack_webhook", channel or "default", message[:100],
            status="failed", error=str(exc)[:200],
        )


async def _log_delivery(
    db, org_id: str, channel: str, provider: str, recipient: Any,
    subject: str, *, status: str, provider_id: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Log notification delivery for audit."""
    now = datetime.now(timezone.utc).isoformat()
    log_id = str(uuid.uuid4())
    doc = {
        "delivery_id": log_id,
        "organization_id": org_id,
        "channel": channel,
        "provider": provider,
        "recipient": recipient if isinstance(recipient, str) else str(recipient),
        "subject": subject[:200],
        "status": status,
        "provider_id": provider_id,
        "error": error,
        "created_at": now,
    }
    try:
        await db.notification_deliveries.insert_one(doc)
    except Exception:
        logger.warning("Failed to log delivery: %s", log_id)

    return {
        "delivery_id": log_id,
        "channel": channel,
        "status": status,
        "provider_id": provider_id,
        "error": error,
    }


async def get_delivery_log(
    db, org_id: str, channel: str | None = None,
    status: str | None = None, limit: int = 50,
) -> list[dict]:
    """Get notification delivery log."""
    match: dict[str, Any] = {"organization_id": org_id}
    if channel:
        match["channel"] = channel
    if status:
        match["status"] = status
    cursor = db.notification_deliveries.find(match, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(limit)
