"""Celery Worker Pool Configuration & Management.

PART 1 — Worker Pool Design
PART 2 — Worker Deployment
PART 3 — DLQ Consumers

Queues:
  booking_queue     — Critical booking operations (confirm, cancel, modify)
  voucher_queue     — PDF voucher generation & delivery
  notification_queue — Email, SMS, push, Slack, webhooks
  incident_queue    — Incident escalation, alert routing
  cleanup_queue     — Cache cleanup, stale data removal, metric aggregation

Each pool has isolated concurrency, prefetch, and autoscale settings.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("infrastructure.worker_pools")


# ============================================================================
# PART 1 — WORKER POOL DESIGN
# ============================================================================

WORKER_POOLS = {
    "booking": {
        "name": "booking-pool",
        "queues": ["booking_queue", "critical"],
        "concurrency": 4,
        "prefetch_multiplier": 1,
        "max_tasks_per_child": 500,
        "autoscale_min": 2,
        "autoscale_max": 8,
        "priority": "P0",
        "description": "Booking confirmations, cancellations, state transitions. Zero tolerance for dropped jobs.",
        "soft_time_limit": 120,
        "time_limit": 180,
    },
    "voucher": {
        "name": "voucher-pool",
        "queues": ["voucher_queue", "reports"],
        "concurrency": 2,
        "prefetch_multiplier": 1,
        "max_tasks_per_child": 100,
        "autoscale_min": 1,
        "autoscale_max": 4,
        "priority": "P1",
        "description": "PDF voucher generation (WeasyPrint). Memory-intensive, low concurrency.",
        "soft_time_limit": 180,
        "time_limit": 300,
    },
    "notification": {
        "name": "notification-pool",
        "queues": ["notification_queue", "notifications", "email", "alerts"],
        "concurrency": 6,
        "prefetch_multiplier": 4,
        "max_tasks_per_child": 1000,
        "autoscale_min": 1,
        "autoscale_max": 8,
        "priority": "P1",
        "description": "Email (Resend), SMS, Slack alerts, webhook delivery. High throughput.",
        "soft_time_limit": 30,
        "time_limit": 60,
    },
    "incident": {
        "name": "incident-pool",
        "queues": ["incident_queue", "incidents"],
        "concurrency": 2,
        "prefetch_multiplier": 1,
        "max_tasks_per_child": 200,
        "autoscale_min": 1,
        "autoscale_max": 4,
        "priority": "P0",
        "description": "Incident escalation, supplier outage handling, circuit breaker events.",
        "soft_time_limit": 60,
        "time_limit": 120,
    },
    "cleanup": {
        "name": "cleanup-pool",
        "queues": ["cleanup_queue", "maintenance"],
        "concurrency": 2,
        "prefetch_multiplier": 1,
        "max_tasks_per_child": 50,
        "autoscale_min": 1,
        "autoscale_max": 2,
        "priority": "P2",
        "description": "Cache cleanup, expired hold removal, stale run cleanup, metric aggregation.",
        "soft_time_limit": 300,
        "time_limit": 600,
    },
}


# Queue isolation matrix — which pool owns which queue
QUEUE_ISOLATION = {}
for pool_name, pool in WORKER_POOLS.items():
    for q in pool["queues"]:
        QUEUE_ISOLATION[q] = pool_name


# ============================================================================
# PART 2 — WORKER DEPLOYMENT & HEALTH CHECKS
# ============================================================================

def get_celery_worker_command(pool_name: str) -> str:
    """Generate the celery worker command for a specific pool."""
    pool = WORKER_POOLS.get(pool_name)
    if not pool:
        raise ValueError(f"Unknown pool: {pool_name}")

    queues = ",".join(pool["queues"])
    return (
        f"celery -A app.infrastructure.celery_app:celery_app worker "
        f"--hostname={pool['name']}@%h "
        f"--queues={queues} "
        f"--concurrency={pool['concurrency']} "
        f"--prefetch-multiplier={pool['prefetch_multiplier']} "
        f"--max-tasks-per-child={pool['max_tasks_per_child']} "
        f"--autoscale={pool['autoscale_max']},{pool['autoscale_min']} "
        f"--soft-time-limit={pool['soft_time_limit']} "
        f"--time-limit={pool['time_limit']} "
        f"--without-gossip --without-mingle "
        f"-l info"
    )


async def check_worker_health() -> dict:
    """Check health of all Celery workers via Redis broker inspection."""
    import redis.asyncio as aioredis

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "unknown",
        "pools": {},
        "total_workers": 0,
        "total_active_tasks": 0,
    }

    try:
        # Use broker URL (DB 1) for kombu/worker checks, not the cache URL (DB 0)
        base_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        broker_url = os.environ.get("CELERY_BROKER_URL", base_url.rsplit("/", 1)[0] + "/1")
        r = aioredis.from_url(broker_url, decode_responses=True, socket_connect_timeout=2)
        await r.ping()

        # Check kombu bindings (queue registrations) — stored as SET members under exchange names
        kombu_keys = []
        kombu_members = []
        async for key in r.scan_iter("_kombu.binding.*"):
            kombu_keys.append(key)
            try:
                members = await r.smembers(key)
                kombu_members.extend(members)
            except Exception:
                pass

        # Check for Celery worker heartbeats
        heartbeat_keys = []
        async for key in r.scan_iter("celery-worker-heartbeat-*"):
            heartbeat_keys.append(key)

        # Check task results on result backend (DB 2)
        result_url = os.environ.get("CELERY_RESULT_URL", base_url.rsplit("/", 1)[0] + "/2")
        r_results = aioredis.from_url(result_url, decode_responses=True, socket_connect_timeout=2)
        task_meta_count = 0
        try:
            async for _ in r_results.scan_iter("celery-task-meta-*"):
                task_meta_count += 1
            await r_results.aclose()
        except Exception:
            pass

        # Check queue depths per pool
        for pool_name, pool in WORKER_POOLS.items():
            pool_status = {
                "name": pool["name"],
                "queues": {},
                "total_depth": 0,
                "status": "unknown",
            }
            for q in pool["queues"]:
                try:
                    depth = await r.llen(q)
                    pool_status["queues"][q] = {"depth": depth}
                    pool_status["total_depth"] += depth
                except Exception:
                    pool_status["queues"][q] = {"depth": 0}

            pool_status["status"] = "active" if any(
                q in member for member in kombu_members for q in pool["queues"]
            ) else "idle"
            result["pools"][pool_name] = pool_status

        # Try celery inspect via subprocess
        workers_found = await _inspect_celery_workers()

        active_pools = sum(1 for p in result["pools"].values() if p["status"] == "active")
        total_pools = len(result["pools"])

        result.update({
            "status": "healthy" if workers_found else ("registered" if kombu_members else "no_workers"),
            "total_workers": len(workers_found) if workers_found else (1 if kombu_members else 0),
            "worker_details": workers_found or [],
            "kombu_bindings": len(kombu_keys),
            "kombu_registered_queues": list(set(kombu_members)),
            "task_results_count": task_meta_count,
            "active_pools": active_pools,
            "total_pools": total_pools,
        })

        await r.aclose()
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


async def _inspect_celery_workers() -> list:
    """Inspect running Celery workers via subprocess."""
    import subprocess

    loop = asyncio.get_event_loop()

    def _run():
        try:
            env = dict(os.environ)
            env["PYTHONPATH"] = "/app/backend"
            env["PATH"] = "/root/.venv/bin:" + env.get("PATH", "/usr/bin")
            proc = subprocess.run(
                ["/root/.venv/bin/celery",
                 "-A", "app.infrastructure.celery_app:celery_app",
                 "inspect", "ping", "--timeout=5", "--json"],
                capture_output=True, text=True, timeout=10,
                cwd="/app/backend", env=env,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                try:
                    data = json.loads(proc.stdout.strip())
                    workers = []
                    for name, response in data.items():
                        workers.append({
                            "name": name,
                            "alive": response.get("ok") == "pong" if isinstance(response, dict) else False,
                        })
                    return workers
                except (json.JSONDecodeError, AttributeError):
                    pass
            return []
        except Exception:
            return []

    return await loop.run_in_executor(None, _run)


# ============================================================================
# PART 3 — DLQ CONSUMERS
# ============================================================================

DLQ_QUEUES = {
    "dlq.booking": {
        "source_queue": "booking_queue",
        "max_retries": 5,
        "retry_delay_seconds": 300,
        "escalate_on_failure": True,
        "escalation_channel": "slack+email",
        "persist_permanently": True,
    },
    "dlq.voucher": {
        "source_queue": "voucher_queue",
        "max_retries": 3,
        "retry_delay_seconds": 600,
        "escalate_on_failure": True,
        "escalation_channel": "slack",
        "persist_permanently": True,
    },
    "dlq.notification": {
        "source_queue": "notification_queue",
        "max_retries": 3,
        "retry_delay_seconds": 300,
        "escalate_on_failure": False,
        "escalation_channel": "log",
        "persist_permanently": False,
    },
    "dlq.incident": {
        "source_queue": "incident_queue",
        "max_retries": 5,
        "retry_delay_seconds": 120,
        "escalate_on_failure": True,
        "escalation_channel": "pagerduty",
        "persist_permanently": True,
    },
    "dlq.cleanup": {
        "source_queue": "cleanup_queue",
        "max_retries": 2,
        "retry_delay_seconds": 900,
        "escalate_on_failure": False,
        "escalation_channel": "log",
        "persist_permanently": False,
    },
    # Legacy DLQs
    "dlq.default": {
        "source_queue": "default",
        "max_retries": 2,
        "retry_delay_seconds": 900,
        "escalate_on_failure": False,
        "escalation_channel": "log",
        "persist_permanently": False,
    },
    "dlq.critical": {
        "source_queue": "critical",
        "max_retries": 5,
        "retry_delay_seconds": 300,
        "escalate_on_failure": True,
        "escalation_channel": "slack+email",
        "persist_permanently": True,
    },
    "dlq.supplier": {
        "source_queue": "supplier",
        "max_retries": 3,
        "retry_delay_seconds": 600,
        "escalate_on_failure": True,
        "escalation_channel": "slack",
        "persist_permanently": True,
    },
}


def _broker_url() -> str:
    """Get the Celery broker URL (Redis DB 1)."""
    base = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return os.environ.get("CELERY_BROKER_URL", base.rsplit("/", 1)[0] + "/1")


async def inspect_dlq(db) -> dict:
    """Inspect all DLQ queues: depth, recent failures, retry status."""
    import redis.asyncio as aioredis

    dlq_status = {}
    total_failed = 0

    try:
        r = aioredis.from_url(_broker_url(), decode_responses=True, socket_connect_timeout=2)

        for dlq_name, config in DLQ_QUEUES.items():
            depth = await r.llen(dlq_name)
            total_failed += depth
            dlq_status[dlq_name] = {
                "depth": depth,
                "source_queue": config["source_queue"],
                "max_retries": config["max_retries"],
                "escalate_on_failure": config["escalate_on_failure"],
            }

        await r.aclose()
    except Exception as e:
        return {"status": "error", "error": str(e)}

    # Get recent DLQ events from MongoDB
    recent_events = []
    try:
        cursor = db.dlq_events.find({}, {"_id": 0}).sort("timestamp", -1).limit(20)
        recent_events = await cursor.to_list(20)
    except Exception:
        pass

    # Get permanent failures count
    permanent_failures = 0
    try:
        permanent_failures = await db.dlq_permanent_failures.count_documents({})
    except Exception:
        pass

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "healthy" if total_failed == 0 else "has_failures",
        "queues": dlq_status,
        "total_dead_letters": total_failed,
        "permanent_failures": permanent_failures,
        "recent_events": recent_events[:10],
    }


async def process_dlq_message(db, dlq_name: str, message: dict) -> dict:
    """Process a single DLQ message: retry if safe, escalate if exhausted."""
    config = DLQ_QUEUES.get(dlq_name, DLQ_QUEUES.get("dlq.default"))
    retry_count = message.get("retry_count", 0) + 1

    event = {
        "dlq_name": dlq_name,
        "task_name": message.get("task_name", "unknown"),
        "retry_count": retry_count,
        "max_retries": config["max_retries"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "original_error": message.get("error", "unknown"),
    }

    if retry_count <= config["max_retries"]:
        # Safe to retry — push back to source queue
        event["action"] = "retry"
        event["status"] = "retrying"
        event["next_retry_in_seconds"] = config["retry_delay_seconds"]
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(_broker_url(), decode_responses=True, socket_connect_timeout=2)
            message["retry_count"] = retry_count
            await r.rpush(config["source_queue"], json.dumps(message))
            await r.aclose()
            event["requeued"] = True
        except Exception as e:
            event["requeued"] = False
            event["requeue_error"] = str(e)
    else:
        # Exhausted retries — escalate
        event["action"] = "escalate"
        event["status"] = "permanently_failed"
        if config["persist_permanently"]:
            await db.dlq_permanent_failures.insert_one({
                **event, "original_message": message,
            })
        if config["escalate_on_failure"]:
            event["escalation_channel"] = config["escalation_channel"]
            event["escalation_triggered"] = True

    await db.dlq_events.insert_one({**event})
    return {k: v for k, v in event.items() if k != "_id"}


async def retry_all_safe_dlq(db) -> dict:
    """Batch-retry all DLQ messages that haven't exceeded max retries."""
    import redis.asyncio as aioredis

    url = _broker_url()
    results = {"retried": 0, "escalated": 0, "errors": 0}

    try:
        r = aioredis.from_url(url, decode_responses=True, socket_connect_timeout=2)

        for dlq_name, config in DLQ_QUEUES.items():
            depth = await r.llen(dlq_name)
            for _ in range(depth):
                raw = await r.lpop(dlq_name)
                if not raw:
                    break
                try:
                    msg = json.loads(raw)
                    result = await process_dlq_message(db, dlq_name, msg)
                    if result["action"] == "retry":
                        results["retried"] += 1
                    else:
                        results["escalated"] += 1
                except Exception:
                    results["errors"] += 1

        await r.aclose()
    except Exception as e:
        results["error"] = str(e)

    results["timestamp"] = datetime.now(timezone.utc).isoformat()
    return results
