"""PART 2 — Worker Deployment Strategy.

Celery worker pools, queue isolation, DLQ consumers, auto-scaling config.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("hardening.worker_strategy")


# Worker pool definitions
WORKER_POOLS = {
    "critical": {
        "queues": ["critical"],
        "concurrency": 4,
        "prefetch_multiplier": 1,
        "max_tasks_per_child": 500,
        "description": "Payment confirmations, booking state changes",
        "autoscale": {"min": 2, "max": 8},
        "priority": "highest",
    },
    "supplier": {
        "queues": ["supplier"],
        "concurrency": 8,
        "prefetch_multiplier": 2,
        "max_tasks_per_child": 200,
        "description": "External supplier API calls",
        "autoscale": {"min": 2, "max": 16},
        "priority": "high",
    },
    "notifications": {
        "queues": ["notifications", "email", "alerts"],
        "concurrency": 6,
        "prefetch_multiplier": 4,
        "max_tasks_per_child": 1000,
        "description": "Email, SMS, Slack, webhooks",
        "autoscale": {"min": 1, "max": 8},
        "priority": "medium",
    },
    "reports": {
        "queues": ["reports", "voucher"],
        "concurrency": 2,
        "prefetch_multiplier": 1,
        "max_tasks_per_child": 100,
        "description": "PDF generation, report exports",
        "autoscale": {"min": 1, "max": 4},
        "priority": "low",
    },
    "maintenance": {
        "queues": ["maintenance"],
        "concurrency": 2,
        "prefetch_multiplier": 1,
        "max_tasks_per_child": 50,
        "description": "Cache cleanup, metric aggregation",
        "autoscale": {"min": 1, "max": 2},
        "priority": "lowest",
    },
}


# DLQ consumer configuration
DLQ_CONFIG = {
    "dlq.critical": {
        "max_retry_attempts": 5,
        "retry_delay_seconds": 300,
        "alert_on_failure": True,
        "escalation_channel": "slack",
        "store_permanently": True,
    },
    "dlq.supplier": {
        "max_retry_attempts": 3,
        "retry_delay_seconds": 600,
        "alert_on_failure": True,
        "escalation_channel": "slack",
        "store_permanently": True,
    },
    "dlq.default": {
        "max_retry_attempts": 2,
        "retry_delay_seconds": 900,
        "alert_on_failure": False,
        "escalation_channel": "log",
        "store_permanently": False,
    },
}


# Auto-scaling rules
AUTOSCALE_RULES = {
    "queue_depth_threshold": {
        "critical": {"scale_up_at": 10, "scale_down_at": 2},
        "supplier": {"scale_up_at": 50, "scale_down_at": 5},
        "notifications": {"scale_up_at": 100, "scale_down_at": 10},
        "reports": {"scale_up_at": 20, "scale_down_at": 2},
    },
    "latency_threshold_ms": {
        "critical": {"scale_up_at": 5000, "scale_down_at": 1000},
        "supplier": {"scale_up_at": 15000, "scale_down_at": 3000},
    },
    "cooldown_seconds": 120,
    "evaluation_window_seconds": 60,
}


async def get_worker_strategy_status(db) -> dict:
    """Get comprehensive worker deployment status."""
    import redis as redis_lib
    import os

    redis_status = "unknown"
    queue_depths = {}
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis_lib.from_url(redis_url, socket_timeout=2)
        r.ping()
        redis_status = "healthy"
        for pool_name, pool in WORKER_POOLS.items():
            for q in pool["queues"]:
                depth = r.llen(q) if r.exists(q) else 0
                queue_depths[q] = depth
    except Exception:
        redis_status = "unhealthy"

    dlq_depths = {}
    try:
        for dlq_name in DLQ_CONFIG:
            depth = r.llen(dlq_name) if r.exists(dlq_name) else 0
            dlq_depths[dlq_name] = depth
    except Exception:
        pass

    # Get recent DLQ events from DB
    dlq_events = await db.dlq_events.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).limit(20).to_list(20)

    return {
        "redis_status": redis_status,
        "worker_pools": WORKER_POOLS,
        "queue_depths": queue_depths,
        "dlq_config": DLQ_CONFIG,
        "dlq_depths": dlq_depths,
        "dlq_recent_events": dlq_events,
        "autoscale_rules": AUTOSCALE_RULES,
        "status": "operational" if redis_status == "healthy" else "degraded",
    }


async def process_dlq_message(db, queue_name: str, message: dict) -> dict:
    """Process a dead-letter queue message with retry logic."""
    config = DLQ_CONFIG.get(queue_name, DLQ_CONFIG["dlq.default"])
    event = {
        "queue": queue_name,
        "message": message,
        "attempt": message.get("retry_count", 0) + 1,
        "max_attempts": config["max_retry_attempts"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "retrying",
    }

    if event["attempt"] > config["max_retry_attempts"]:
        event["status"] = "permanently_failed"
        if config["store_permanently"]:
            await db.dlq_permanent_failures.insert_one({**event})

    await db.dlq_events.insert_one({**event})
    return event
