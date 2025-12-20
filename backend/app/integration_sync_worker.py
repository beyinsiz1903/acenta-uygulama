from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.db import get_db
from app.routers.hotel_integrations import _ensure_cm_integration, _utc_now

logger = logging.getLogger("integration_sync_worker")


async def dispatch_pending_integration_sync(db, *, limit: int = 10) -> int:
    """Process pending integration sync jobs.

    For FAZ-10.1 this is a placeholder that marks jobs as done and updates
    hotel_integrations.last_sync_at. Later we will replace the body with
    real CM API calls.
    """

    now = _utc_now()

    cursor = db.integration_sync_outbox.find(
        {"status": "pending", "next_retry_at": {"$lte": now}}, limit=limit
    )

    processed = 0
    async for job in cursor:
        processed += 1
        job_id = job.get("_id")
        org_id = job.get("organization_id")
        hotel_id = job.get("hotel_id")

        logger.info("Processing integration sync job %s for hotel %s", job_id, hotel_id)

        # Mark as running
        await db.integration_sync_outbox.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "running",
                    "started_at": now,
                    "updated_at": now,
                }
            },
        )

        try:
            # Ensure integration exists and update last_sync_at
            integ = await _ensure_cm_integration(db, org_id, str(hotel_id))

            await db.hotel_integrations.update_one(
                {
                    "organization_id": org_id,
                    "hotel_id": str(hotel_id),
                    "kind": "channel_manager",
                },
                {"$set": {"last_sync_at": now, "last_error": None, "updated_at": now}},
            )

            await db.integration_sync_outbox.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "sent",
                        "finished_at": now,
                        "updated_at": now,
                        "last_error": None,
                    }
                },
            )

            # Optionally we could write an audit log here later
        except Exception as e:  # pragma: no cover - placeholder error branch
            logger.error("Integration sync job %s failed: %s", job_id, e, exc_info=True)
            await db.integration_sync_outbox.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "failed",
                        "finished_at": _utc_now(),
                        "updated_at": _utc_now(),
                        "last_error": str(e),
                    }
                },
            )

    return processed


async def integration_sync_loop() -> None:
    db = await get_db()
    while True:
        try:
            processed = await dispatch_pending_integration_sync(db, limit=10)
            if processed:
                logger.info("Integration sync worker processed %s jobs", processed)
        except Exception as e:  # pragma: no cover
            logger.error("Integration sync worker loop error: %s", e, exc_info=True)

        await asyncio.sleep(10)
