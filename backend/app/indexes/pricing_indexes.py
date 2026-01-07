from __future__ import annotations

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure
import logging

logger = logging.getLogger(__name__)


async def ensure_pricing_indexes(db):
    """Ensure indexes for pricing v2 collections.

    Defensive: same pattern as catalog indexes - swallow IndexOptionsConflict /
    already-exists, but log it.
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
                    "[pricing_indexes] Keeping legacy index for %s (name=%s): %s",
                    collection.name,
                    kwargs.get("name"),
                    msg,
                )
                return
            raise

    # Contracts: org + status + agency/channel for fast selection
    await _safe_create(
        db.pricing_contracts,
        [("organization_id", ASCENDING), ("status", ASCENDING), ("agency_id", ASCENDING), ("channel_id", ASCENDING)],
        name="pricing_contracts_org_status_agency_channel",
    )
    await _safe_create(
        db.pricing_contracts,
        [("organization_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
        name="pricing_contracts_org_status_created",
    )

    # Rate grids: org + contract + product + rate_plan
    await _safe_create(
        db.pricing_rate_grids,
        [
            ("organization_id", ASCENDING),
            ("contract_id", ASCENDING),
            ("product_id", ASCENDING),
            ("rate_plan_id", ASCENDING),
        ],
        name="pricing_grids_lookup",
    )

    # Rules: org + status + priority
    await _safe_create(
        db.pricing_rules,
        [("organization_id", ASCENDING), ("status", ASCENDING), ("priority", DESCENDING)],
        name="pricing_rules_org_status_priority",
    )

    # Traces: org + quote + created_at
    await _safe_create(
        db.pricing_traces,
        [("organization_id", ASCENDING), ("quote_id", ASCENDING), ("created_at", DESCENDING)],
        name="pricing_traces_org_quote_created",
    )
