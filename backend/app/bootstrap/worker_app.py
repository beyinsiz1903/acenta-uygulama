from __future__ import annotations

import asyncio
import contextlib
import logging
import os

from app.bootstrap.runtime_init import load_backend_env

logger = logging.getLogger("worker_runtime")


def _is_enabled(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


async def main() -> None:
    load_backend_env()

    from app.bootstrap.runtime_init import init_observability, run_worker_boot_tasks, shutdown_runtime_resources
    from app.db import close_mongo, connect_mongo
    from app.email_worker import email_dispatch_loop
    from app.integration_sync_worker import integration_sync_loop
    from app.services.jobs import run_job_worker_loop

    init_observability()
    await connect_mongo()

    tasks: list[asyncio.Task] = []
    try:
        await run_worker_boot_tasks()

        if _is_enabled("ENABLE_EMAIL_WORKER", default=True):
            tasks.append(asyncio.create_task(email_dispatch_loop(), name="email-worker"))
        if _is_enabled("ENABLE_INTEGRATION_SYNC_WORKER", default=True):
            tasks.append(asyncio.create_task(integration_sync_loop(), name="integration-sync-worker"))
        if _is_enabled("ENABLE_JOB_WORKER", default=True):
            tasks.append(asyncio.create_task(run_job_worker_loop("job-worker-1"), name="job-worker"))

        if not tasks:
            logger.warning("No worker loops enabled; worker runtime exiting")
            return

        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        shutdown_runtime_resources()
        await close_mongo()


if __name__ == "__main__":
    asyncio.run(main())
