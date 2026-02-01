from __future__ import annotations

from logging import getLogger

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = getLogger(__name__)


async def ensure_marketplace_indexes(db: AsyncIOMotorDatabase) -> None:
    """Ensure indexes for marketplace collections.

    - marketplace_listings: org + tenant + status, org + status + updated_at
    - marketplace_access: unique (org, seller_tenant_id, buyer_tenant_id), buyer_tenant_id lookup
    """

    async def _safe_create(collection, *args, **kwargs):
        try:
            await collection.create_index(*args, **kwargs)
        except OperationFailure as e:
            msg = str(e).lower()
            if (
                "indexoptionsconflict" in msg
                or "indexkeyspecsconflict" in msg
                or "already exists" in msg
            ):
                logger.warning(
                    "[marketplace_indexes] Keeping legacy index for %s (name=%s): %s",
                    collection.name,
                    kwargs.get("name"),
                    msg,
                )
                return
            raise

    await _safe_create(
        db.marketplace_listings,
        [("organization_id", ASCENDING), ("tenant_id", ASCENDING), ("status", ASCENDING)],
        name="marketplace_listings_org_tenant_status",
    )
    await _safe_create(
        db.marketplace_listings,
        [("organization_id", ASCENDING), ("status", ASCENDING), ("updated_at", DESCENDING)],
        name="marketplace_listings_org_status_updated",
    )
    await _safe_create(
        db.marketplace_access,
        [
            ("organization_id", ASCENDING),
            ("seller_tenant_id", ASCENDING),
            ("buyer_tenant_id", ASCENDING),
        ],
        name="marketplace_access_org_seller_buyer",
        unique=True,
    )
    await _safe_create(
        db.marketplace_access,
        [("buyer_tenant_id", ASCENDING)],
        name="marketplace_access_buyer_tenant",
    )
