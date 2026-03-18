"""Celery application factory.

Queue design:
  - default:       General tasks, catch-all
  - critical:      Payment confirmations, booking state changes
  - supplier:      External API calls (AviationStack, Paximum)
  - notifications: Email, SMS, push notifications
  - reports:       Report generation, PDF exports, invoices
  - maintenance:   DB cleanup, cache warmup, analytics aggregation

Retry policies:
  - Exponential backoff with jitter
  - Max retries per task type
  - Dead letter queue for permanently failed tasks

Configuration:
  REDIS_URL           = redis://localhost:6379/0
  CELERY_BROKER_URL   = redis://localhost:6379/1
  CELERY_RESULT_URL   = redis://localhost:6379/2
"""
from __future__ import annotations

import os
import logging

from celery import Celery
from kombu import Exchange, Queue

logger = logging.getLogger("infrastructure.celery")


def _broker_url() -> str:
    return os.environ.get("CELERY_BROKER_URL", os.environ.get("REDIS_URL", "redis://localhost:6379/1"))


def _result_url() -> str:
    return os.environ.get("CELERY_RESULT_URL", os.environ.get("REDIS_URL", "redis://localhost:6379/2"))


# Exchange definitions
default_exchange = Exchange("default", type="direct")
dlx_exchange = Exchange("dlx", type="direct")  # Dead Letter Exchange

# Queue definitions — Production worker pools
TASK_QUEUES = (
    # Legacy queues (backward compat)
    Queue("default", default_exchange, routing_key="default"),
    Queue("critical", default_exchange, routing_key="critical"),
    Queue("supplier", default_exchange, routing_key="supplier"),
    Queue("notifications", default_exchange, routing_key="notifications"),
    Queue("reports", default_exchange, routing_key="reports"),
    Queue("maintenance", default_exchange, routing_key="maintenance"),
    Queue("email", default_exchange, routing_key="email"),
    Queue("alerts", default_exchange, routing_key="alerts"),
    Queue("incidents", default_exchange, routing_key="incidents"),
    # Production worker pool queues
    Queue("booking_queue", default_exchange, routing_key="booking_queue"),
    Queue("voucher_queue", default_exchange, routing_key="voucher_queue"),
    Queue("notification_queue", default_exchange, routing_key="notification_queue"),
    Queue("incident_queue", default_exchange, routing_key="incident_queue"),
    Queue("cleanup_queue", default_exchange, routing_key="cleanup_queue"),
    Queue("webhook_queue", default_exchange, routing_key="webhook_queue"),
    # Dead Letter Queues
    Queue("dlq.default", dlx_exchange, routing_key="dlq.default"),
    Queue("dlq.critical", dlx_exchange, routing_key="dlq.critical"),
    Queue("dlq.supplier", dlx_exchange, routing_key="dlq.supplier"),
    Queue("dlq.booking", dlx_exchange, routing_key="dlq.booking"),
    Queue("dlq.voucher", dlx_exchange, routing_key="dlq.voucher"),
    Queue("dlq.notification", dlx_exchange, routing_key="dlq.notification"),
    Queue("dlq.incident", dlx_exchange, routing_key="dlq.incident"),
    Queue("dlq.cleanup", dlx_exchange, routing_key="dlq.cleanup"),
    Queue("dlq.webhook", dlx_exchange, routing_key="dlq.webhook"),
)

# Route tasks to queues by name pattern
TASK_ROUTES = {
    # Outbox consumer (runs on default queue)
    "app.tasks.outbox_consumer.*": {"queue": "default"},
    # Outbox consumer handlers (routed to their specific queues)
    "app.tasks.outbox_consumers.send_booking_notification": {"queue": "notification_queue"},
    "app.tasks.outbox_consumers.send_booking_email": {"queue": "notification_queue"},
    "app.tasks.outbox_consumers.update_billing_projection": {"queue": "reports"},
    "app.tasks.outbox_consumers.update_reporting_projection": {"queue": "reports"},
    "app.tasks.outbox_consumers.dispatch_webhook": {"queue": "notification_queue"},
    # Webhook system tasks
    "app.tasks.webhook_tasks.dispatch_webhook_event": {"queue": "webhook_queue"},
    "app.tasks.webhook_tasks.execute_webhook_delivery": {"queue": "webhook_queue"},
    "app.tasks.webhook_tasks.replay_webhook_delivery": {"queue": "webhook_queue"},
    # Production pool routes
    "app.tasks.booking.*": {"queue": "booking_queue"},
    "app.tasks.payment.*": {"queue": "booking_queue"},
    "tasks.generate_voucher": {"queue": "voucher_queue"},
    "tasks.send_voucher_email": {"queue": "voucher_queue"},
    "app.tasks.supplier.*": {"queue": "supplier"},
    "app.tasks.email.*": {"queue": "notification_queue"},
    "app.tasks.sms.*": {"queue": "notification_queue"},
    "app.tasks.notification.*": {"queue": "notification_queue"},
    "tasks.send_email": {"queue": "notification_queue"},
    "tasks.send_slack_alert": {"queue": "notification_queue"},
    "tasks.send_webhook": {"queue": "notification_queue"},
    "app.tasks.report.*": {"queue": "voucher_queue"},
    "app.tasks.invoice.*": {"queue": "voucher_queue"},
    "app.tasks.voucher.*": {"queue": "voucher_queue"},
    "tasks.escalate_incident": {"queue": "incident_queue"},
    "app.tasks.maintenance.*": {"queue": "cleanup_queue"},
    "tasks.cleanup_expired_holds": {"queue": "cleanup_queue"},
    "tasks.cleanup_stale_orchestration_runs": {"queue": "cleanup_queue"},
    "tasks.refresh_supplier_status_cache": {"queue": "cleanup_queue"},
    "tasks.cleanup_old_metrics": {"queue": "cleanup_queue"},
}


def create_celery_app() -> Celery:
    app = Celery("syroce")

    app.conf.update(
        broker_url=_broker_url(),
        result_backend=_result_url(),
        task_queues=TASK_QUEUES,
        task_routes=TASK_ROUTES,
        task_default_queue="default",
        task_default_exchange="default",
        task_default_routing_key="default",

        # Serialization
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],

        # Timezone
        timezone="UTC",
        enable_utc=True,

        # Retry defaults
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=4,

        # Result expiry
        result_expires=3600,

        # Rate limiting
        worker_max_tasks_per_child=1000,

        # Visibility timeout for Redis broker
        broker_transport_options={
            "visibility_timeout": 3600,
            "queue_order_strategy": "priority",
        },

        # Beat schedule for periodic tasks
        beat_schedule={
            "outbox-consumer-poll": {
                "task": "app.tasks.outbox_consumer.poll_and_dispatch",
                "schedule": 5.0,  # every 5 seconds — primary outbox consumer
            },
            "cleanup-expired-cache": {
                "task": "app.tasks.maintenance.cleanup_expired_cache",
                "schedule": 300.0,  # every 5 minutes
            },
            "aggregate-usage-metrics": {
                "task": "app.tasks.maintenance.aggregate_usage_metrics",
                "schedule": 3600.0,  # every hour
            },
            "health-check-suppliers": {
                "task": "app.tasks.maintenance.health_check_suppliers",
                "schedule": 600.0,  # every 10 minutes
            },
        },
    )

    # Auto-discover tasks
    app.autodiscover_tasks(["app.tasks", "app.infrastructure"])

    # Explicitly register task modules (autodiscover expects `tasks.py` naming)
    app.conf.include = [
        "app.tasks.booking_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.maintenance_tasks",
        "app.tasks.report_tasks",
        "app.tasks.supplier_tasks",
        "app.tasks.outbox_consumers",
        "app.tasks.webhook_tasks",
        "app.infrastructure.outbox_consumer",
    ]

    return app


celery_app = create_celery_app()
