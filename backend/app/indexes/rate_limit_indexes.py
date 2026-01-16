from __future__ import annotations

from pymongo import ASCENDING


async def ensure_rate_limit_indexes(db):
    async def _safe_create(collection, *args, **kwargs):
        try:
            await collection.create_index(*args, **kwargs)
        except Exception:
            return

    await _safe_create(
        db.rate_limit_buckets,
        [
            ("organization_id", ASCENDING),
            ("key_id", ASCENDING),
            ("ip", ASCENDING),
            ("bucket_minute", ASCENDING),
        ],
        name="rate_limit_by_org_key_ip_bucket",
    )

    await _safe_create(
        db.rate_limit_buckets,
        [("created_at", ASCENDING)],
        name="ttl_rate_limit_buckets",
        expireAfterSeconds=7200,
    )
