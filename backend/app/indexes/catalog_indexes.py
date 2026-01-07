from __future__ import annotations

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure
import logging

logger = logging.getLogger(__name__)


async def ensure_catalog_indexes(db):
    """Ensure indexes for catalog collections.

    Defensive: if an index with the same name but different options already
    exists (legacy), we swallow IndexOptionsConflict and keep existing
    definition. This avoids blocking startup while still enforcing
    constraints on fresh deployments.
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
                    "[catalog_indexes] Keeping legacy index for %s (name=%s): %s",
                    collection.name,
                    kwargs.get("name"),
                    msg,
                )
                return
            raise

    # products: enforce unique code per org only for docs that have code
    await _safe_create(
        db.products,
        [("organization_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="uniq_product_code_per_org",
        partialFilterExpression={"code": {"$type": "string"}},
    )
    await _safe_create(
        db.products,
        [("organization_id", ASCENDING), ("type", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
        name="products_list",
    )
    await _safe_create(
        db.products,
        [("organization_id", ASCENDING), ("name_search", ASCENDING)],
        name="products_name_search",
    )

    # product_versions
    await _safe_create(
        db.product_versions,
        [("organization_id", ASCENDING), ("product_id", ASCENDING), ("version", DESCENDING)],
        name="pver_by_product_version",
    )
    await _safe_create(
        db.product_versions,
        [("organization_id", ASCENDING), ("product_id", ASCENDING), ("status", ASCENDING)],
        name="pver_by_product_status",
    )
    await _safe_create(
        db.product_versions,
        [("organization_id", ASCENDING), ("product_id", ASCENDING), ("published_at", DESCENDING)],
        name="pver_published_at",
    )

    # room_types
    await _safe_create(
        db.room_types,
        [("organization_id", ASCENDING), ("product_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="uniq_roomtype_code_per_product",
    )

    # rate_plans
    await _safe_create(
        db.rate_plans,
        [("organization_id", ASCENDING), ("product_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="uniq_rateplan_code_per_product",
        partialFilterExpression={"code": {"$type": "string"}, "product_id": {"$type": "string"}},
    )

    # cancellation_policies
    await _safe_create(
        db.cancellation_policies,
        [("organization_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="uniq_cancel_policy_code_per_org",
    )

    # audit_logs (extra entity-centric index)
    await _safe_create(
        db.audit_logs,
        [
            ("organization_id", ASCENDING),
            ("target.type", ASCENDING),
            ("target.id", ASCENDING),
            ("created_at", DESCENDING),
        ],
        name="audit_by_entity",
    )
