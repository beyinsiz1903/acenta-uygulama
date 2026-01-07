"""
Phase 2A.2: Supplier Accruals Indexes
Ensures data integrity and query performance for accrual tracking
"""
from __future__ import annotations

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure
import logging

logger = logging.getLogger(__name__)


async def ensure_phase2a_indexes(db):
    """
    Ensure indexes for Phase 2A collections (supplier_accruals)
    
    Defensive: if an index with the same name but different options already
    exists, we swallow IndexOptionsConflict and keep existing definition.
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
                    "[phase2a_indexes] Keeping legacy index for %s (name=%s): %s",
                    collection.name,
                    kwargs.get("name"),
                    msg,
                )
                return
            raise

    # ========================================================================
    # supplier_accruals (Phase 2A.2)
    # ========================================================================
    
    # Booking başına 1 accrual (unique constraint)
    await _safe_create(
        db.supplier_accruals,
        [("organization_id", ASCENDING), ("booking_id", ASCENDING)],
        unique=True,
        name="uniq_accrual_per_booking",
    )
    
    # Supplier list / dashboard filters
    await _safe_create(
        db.supplier_accruals,
        [("organization_id", ASCENDING), ("supplier_id", ASCENDING), ("status", ASCENDING), ("accrued_at", DESCENDING)],
        name="accruals_by_supplier_status",
    )
    
    # Settlement join/lookup
    await _safe_create(
        db.supplier_accruals,
        [("organization_id", ASCENDING), ("settlement_id", ASCENDING)],
        name="accruals_by_settlement",
    )
    
    # Ops debug (recent accruals)
    await _safe_create(
        db.supplier_accruals,
        [("organization_id", ASCENDING), ("accrued_at", DESCENDING)],
        name="accruals_recent",
    )

    logger.info("✅ Phase 2A indexes ensured successfully")
