from __future__ import annotations

from pymongo import ASCENDING


async def ensure_api_keys_indexes(db):
    async def _safe_create(collection, *args, **kwargs):
        try:
            await collection.create_index(*args, **kwargs)
        except Exception:
            return

    await _safe_create(
        db.api_keys,
        [("organization_id", ASCENDING), ("key_hash", ASCENDING)],
        name="api_keys_by_org_hash",
        unique=True,
    )

    await _safe_create(
        db.api_keys,
        [("organization_id", ASCENDING), ("status", ASCENDING)],
        name="api_keys_by_org_status",
    )
