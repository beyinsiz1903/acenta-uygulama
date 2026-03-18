"""Event Dispatch Table — Maps outbox event types to consumer handlers.

Architecture rule (CTO-mandated):
  Command path → state change (sync)
  Event path  → side effect (async)

Consumers NEVER own booking state. They only produce side effects:
  - Send email
  - Send notification
  - Update billing projection
  - Update reporting projection
  - Dispatch webhooks

Each dispatch entry defines:
  - handler: Celery task name
  - queue: target queue
  - idempotent: whether the handler is safe to re-run
  - retry_policy: max retries + backoff config
  - description: what it does
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DispatchEntry:
    handler: str
    queue: str
    idempotent: bool = True
    max_retries: int = 3
    retry_delay: int = 60
    description: str = ""
    enabled: bool = True


# ── Event Dispatch Table ─────────────────────────────────────
# Key: event_type  →  Value: list of DispatchEntry
# One event can fan out to multiple consumers.

DISPATCH_TABLE: dict[str, list[DispatchEntry]] = {
    # ── Booking Events ───────────────────────────────────────
    "booking.confirmed": [
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_notification",
            queue="notification_queue",
            description="Send booking confirmation notification to guest + agency",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_email",
            queue="notification_queue",
            description="Send confirmation email with booking details",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.update_billing_projection",
            queue="reports",
            description="Update billing projection for confirmed booking revenue",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.update_reporting_projection",
            queue="reports",
            description="Update reporting aggregates for confirmed booking",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.dispatch_webhook",
            queue="notification_queue",
            description="Dispatch booking.confirmed webhook to registered endpoints",
        ),
    ],
    "booking.cancelled": [
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_notification",
            queue="notification_queue",
            description="Send cancellation notification",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_email",
            queue="notification_queue",
            description="Send cancellation email",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.update_billing_projection",
            queue="reports",
            description="Reverse billing projection for cancelled booking",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.update_reporting_projection",
            queue="reports",
            description="Update reporting aggregates for cancellation",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.dispatch_webhook",
            queue="notification_queue",
            description="Dispatch booking.cancelled webhook",
        ),
    ],
    "booking.quoted": [
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_notification",
            queue="notification_queue",
            description="Send quote-ready notification",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.update_reporting_projection",
            queue="reports",
            description="Update funnel metrics for new quote",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.dispatch_webhook",
            queue="notification_queue",
            description="Dispatch booking.quoted webhook",
        ),
    ],
    "booking.completed": [
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_notification",
            queue="notification_queue",
            description="Send completion/thank-you notification",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_email",
            queue="notification_queue",
            description="Send completion email with review request",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.update_billing_projection",
            queue="reports",
            description="Finalize billing projection for completed stay",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.update_reporting_projection",
            queue="reports",
            description="Update reporting with completion data",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.dispatch_webhook",
            queue="notification_queue",
            description="Dispatch booking.completed webhook",
        ),
    ],
    "booking.amended": [
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_notification",
            queue="notification_queue",
            description="Send amendment notification",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.update_billing_projection",
            queue="reports",
            description="Recalculate billing projection after amendment",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.update_reporting_projection",
            queue="reports",
            description="Update reporting for amendment",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.dispatch_webhook",
            queue="notification_queue",
            description="Dispatch booking.amended webhook",
        ),
    ],
    "booking.refunded": [
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_notification",
            queue="notification_queue",
            description="Send refund notification",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_email",
            queue="notification_queue",
            description="Send refund confirmation email",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.update_billing_projection",
            queue="reports",
            description="Reverse billing for refund",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.dispatch_webhook",
            queue="notification_queue",
            description="Dispatch booking.refunded webhook",
        ),
    ],
    # ── Payment Events ───────────────────────────────────────
    "payment.completed": [
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_notification",
            queue="notification_queue",
            description="Send payment confirmation notification",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.update_billing_projection",
            queue="reports",
            description="Update billing with payment received",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.dispatch_webhook",
            queue="notification_queue",
            description="Dispatch payment.completed webhook",
        ),
    ],
    "payment.failed": [
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_notification",
            queue="notification_queue",
            description="Send payment failure alert",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.dispatch_webhook",
            queue="notification_queue",
            description="Dispatch payment.failed webhook",
        ),
    ],
    # ── Fulfillment Events ───────────────────────────────────
    "booking.ticketed": [
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_notification",
            queue="notification_queue",
            description="Send ticket-ready notification",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.dispatch_webhook",
            queue="notification_queue",
            description="Dispatch booking.ticketed webhook",
        ),
    ],
    "booking.vouchered": [
        DispatchEntry(
            handler="app.tasks.outbox_consumers.send_booking_notification",
            queue="notification_queue",
            description="Send voucher-ready notification",
        ),
        DispatchEntry(
            handler="app.tasks.outbox_consumers.dispatch_webhook",
            queue="notification_queue",
            description="Dispatch booking.vouchered webhook",
        ),
    ],
}


def get_handlers_for_event(event_type: str) -> list[DispatchEntry]:
    """Return all enabled handlers for a given event type."""
    entries = DISPATCH_TABLE.get(event_type, [])
    return [e for e in entries if e.enabled]


def get_all_event_types() -> list[str]:
    """Return all registered event types."""
    return sorted(DISPATCH_TABLE.keys())


def get_dispatch_summary() -> dict:
    """Return a summary of the dispatch table for admin/health views."""
    summary = {}
    for event_type, entries in DISPATCH_TABLE.items():
        summary[event_type] = {
            "total_handlers": len(entries),
            "enabled_handlers": len([e for e in entries if e.enabled]),
            "handlers": [
                {
                    "handler": e.handler,
                    "queue": e.queue,
                    "idempotent": e.idempotent,
                    "enabled": e.enabled,
                    "description": e.description,
                }
                for e in entries
            ],
        }
    return summary
