from __future__ import annotations

"""Indexes for coupons & campaigns (FAZ 5)."""

import logging
from pymongo import ASCENDING
from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)


async def ensure_coupon_indexes(db):
    """Ensure indexes for coupons and campaigns collections."""

    async def _safe_create(collection, *args, **kwargs):
        try:
            await collection.create_index(*args, **kwargs)
        except OperationFailure as e:  # pragma: no cover - defensive
            msg = str(e).lower()
            if (
                "indexoptionsconflict" in msg
                or "indexkeyspecsconflict" in msg
                or "already exists" in msg
            ):
                logger.warning(
                    "[coupon_indexes] Keeping legacy index for %s (name=%s): %s",
                    collection.name,
                    kwargs.get("name"),
                    msg,
                )
                return
            raise

    await _safe_create(
        db.coupons,
        [("organization_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="uniq_coupon_code_per_org",
    )

    await _safe_create(
        db.campaigns,
        [("organization_id", ASCENDING), ("active", ASCENDING)],
        name="idx_campaigns_org_active",
    )
