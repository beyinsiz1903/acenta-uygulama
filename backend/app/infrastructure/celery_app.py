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

# Queue definitions
TASK_QUEUES = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("critical", default_exchange, routing_key="critical"),
    Queue("supplier", default_exchange, routing_key="supplier"),
    Queue("notifications", default_exchange, routing_key="notifications"),
    Queue("reports", default_exchange, routing_key="reports"),
    Queue("maintenance", default_exchange, routing_key="maintenance"),
    # Dead Letter Queues
    Queue("dlq.default", dlx_exchange, routing_key="dlq.default"),
    Queue("dlq.critical", dlx_exchange, routing_key="dlq.critical"),
    Queue("dlq.supplier", dlx_exchange, routing_key="dlq.supplier"),
)

# Route tasks to queues by name pattern
TASK_ROUTES = {
    "app.tasks.booking.*": {"queue": "critical"},
    "app.tasks.payment.*": {"queue": "critical"},
    "app.tasks.supplier.*": {"queue": "supplier"},
    "app.tasks.email.*": {"queue": "notifications"},
    "app.tasks.sms.*": {"queue": "notifications"},
    "app.tasks.notification.*": {"queue": "notifications"},
    "app.tasks.report.*": {"queue": "reports"},
    "app.tasks.invoice.*": {"queue": "reports"},
    "app.tasks.voucher.*": {"queue": "reports"},
    "app.tasks.maintenance.*": {"queue": "maintenance"},
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
    app.autodiscover_tasks(["app.tasks"])

    return app


celery_app = create_celery_app()
