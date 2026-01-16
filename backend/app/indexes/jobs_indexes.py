from __future__ import annotations

from datetime import datetime, timedelta

from pymongo import ASCENDING


async def ensure_jobs_indexes(db):
    """Ensure indexes for generic jobs collection.

    Collection: jobs
    - (organization_id, status, next_run_at) for schedulers
    - (status, next_run_at) for global ops
    - Optional TTL for succeeded jobs (best-effort)
    """

    async def _safe_create(collection, keys, **kwargs):
        try:
            await collection.create_index(keys, **kwargs)
        except Exception:
            # Index creation failures must not crash app in preview/dev
            return

    await _safe_create(
        db.jobs,
        [("organization_id", ASCENDING), ("status", ASCENDING), ("next_run_at", ASCENDING)],
        name="jobs_by_org_status_next_run",
    )

    await _safe_create(
        db.jobs,
        [("status", ASCENDING), ("next_run_at", ASCENDING)],
        name="jobs_by_status_next_run",
    )

    # Best-effort TTL for succeeded jobs: keep recent history only.
    # We cannot rely on datetime.utcnow here, so we use updated_at field.
    try:
        await db.jobs.create_index(
            [("updated_at", ASCENDING)],
            name="ttl_jobs_succeeded",
            expireAfterSeconds=int(timedelta(days=30).total_seconds()),
            partialFilterExpression={"status": "succeeded"},
        )
    except Exception:
        # Non-fatal in dev/preview
        pass
