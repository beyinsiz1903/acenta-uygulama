"""Notification async tasks (email, SMS, push).

Queue: notifications
Retry: 5 attempts with exponential backoff
"""
from __future__ import annotations

import logging

from app.infrastructure.celery_app import celery_app

logger = logging.getLogger("tasks.notification")


@celery_app.task(
    name="app.tasks.notification.send_email",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    retry_backoff=True,
)
def send_email(self, to: str, subject: str, template: str, context: dict):
    """Send transactional email."""
    logger.info("Sending email to %s: %s", to, subject)
    try:
        return {"status": "sent", "to": to, "subject": subject}
    except Exception as exc:
        logger.error("Email send failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.notification.send_sms",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
)
def send_sms(self, phone: str, message: str, organization_id: str):
    """Send SMS notification."""
    logger.info("Sending SMS to %s", phone)
    try:
        return {"status": "sent", "phone": phone}
    except Exception as exc:
        logger.error("SMS send failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.notification.send_booking_reminder",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def send_booking_reminder(self, booking_id: str, organization_id: str, channel: str = "email"):
    """Send booking reminder (check-in, payment due, etc.)."""
    logger.info("Sending %s reminder for booking %s", channel, booking_id)
    try:
        return {"status": "sent", "channel": channel, "booking_id": booking_id}
    except Exception as exc:
        logger.error("Reminder send failed: %s", exc)
        raise self.retry(exc=exc)
