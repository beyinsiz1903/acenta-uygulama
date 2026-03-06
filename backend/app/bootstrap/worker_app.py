from __future__ import annotations

import asyncio
import contextlib
import logging
import os

from app.bootstrap.runtime_health import RuntimeHeartbeat, heartbeat_loop, install_signal_handlers
from app.bootstrap.runtime_init import load_backend_env

logger = logging.getLogger("worker_runtime")

WORKER_ENTRYPOINT = "python -m app.bootstrap.worker_app"
WORKER_RESPONSIBILITIES = [
    "Email outbox dispatch loop",
    "Integration sync outbox processing",
    "Background jobs queue consumption",
    "One-time seed/cache warm-up boot tasks",
]


def get_worker_runtime_components() -> list[dict[str, object]]:
    return [
        {
            "name": "email-worker",
            "env_flag": "ENABLE_EMAIL_WORKER",
            "enabled": _is_enabled("ENABLE_EMAIL_WORKER", default=True),
            "responsibility": "Dispatch pending email outbox items",
        },
        {
            "name": "integration-sync-worker",
            "env_flag": "ENABLE_INTEGRATION_SYNC_WORKER",
            "enabled": _is_enabled("ENABLE_INTEGRATION_SYNC_WORKER", default=True),
            "responsibility": "Process integration sync outbox jobs",
        },
        {
            "name": "job-worker",
            "env_flag": "ENABLE_JOB_WORKER",
            "enabled": _is_enabled("ENABLE_JOB_WORKER", default=True),
            "responsibility": "Consume jobs collection and execute handlers",
        },
    ]


def _worker_snapshot() -> dict[str, object]:
    components = get_worker_runtime_components()
    enabled_components = [component["name"] for component in components if component["enabled"]]
    return {
        "components": components,
        "enabled_components": enabled_components,
        "enabled_count": len(enabled_components),
    }


def _is_enabled(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


async def main() -> None:
    load_backend_env()

    from app.bootstrap.runtime_init import (
        ensure_jwt_secret,
        init_observability,
        run_worker_boot_tasks,
        shutdown_runtime_resources,
    )
    from app.db import close_mongo, connect_mongo
    from app.email_worker import email_dispatch_loop
    from app.integration_sync_worker import integration_sync_loop
    from app.services.jobs import run_job_worker_loop

    ensure_jwt_secret()
    init_observability()

    stop_event = asyncio.Event()
    install_signal_handlers(stop_event, "worker")
    heartbeat = RuntimeHeartbeat(
        "worker",
        entrypoint=WORKER_ENTRYPOINT,
        responsibilities=WORKER_RESPONSIBILITIES,
    )
    heartbeat.mark_starting(details=_worker_snapshot())

    await connect_mongo()

    tasks: list[asyncio.Task] = []
    heartbeat_task: asyncio.Task | None = None
    shutdown_task: asyncio.Task | None = None
    try:
        await run_worker_boot_tasks()

        if _is_enabled("ENABLE_EMAIL_WORKER", default=True):
            tasks.append(asyncio.create_task(email_dispatch_loop(), name="email-worker"))
        if _is_enabled("ENABLE_INTEGRATION_SYNC_WORKER", default=True):
            tasks.append(asyncio.create_task(integration_sync_loop(), name="integration-sync-worker"))
        if _is_enabled("ENABLE_JOB_WORKER", default=True):
            tasks.append(asyncio.create_task(run_job_worker_loop("job-worker-1"), name="job-worker"))

        heartbeat.mark_ready(details=_worker_snapshot())
        heartbeat_task = asyncio.create_task(
            heartbeat_loop(heartbeat, stop_event, snapshot=_worker_snapshot),
            name="worker-heartbeat",
        )

        if not tasks:
            logger.warning("No worker loops enabled; worker runtime exiting")
            stop_event.set()
            return

        shutdown_task = asyncio.create_task(stop_event.wait(), name="worker-shutdown")
        done, _pending = await asyncio.wait([shutdown_task, *tasks], return_when=asyncio.FIRST_COMPLETED)
        if shutdown_task not in done:
            failed_task = next(task for task in done if task is not shutdown_task)
            with contextlib.suppress(asyncio.CancelledError):
                exc = failed_task.exception()
                if exc is not None:
                    raise exc
            raise RuntimeError(f"Worker loop exited unexpectedly: {failed_task.get_name()}")
    finally:
        stop_event.set()
        if shutdown_task is not None:
            shutdown_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await shutdown_task
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        heartbeat.mark_stopped(details=_worker_snapshot())
        shutdown_runtime_resources()
        await close_mongo()


if __name__ == "__main__":
    asyncio.run(main())
