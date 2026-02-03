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

    from app.indexes.partner_graph_indexes import ensure_partner_graph_indexes

    await ensure_partner_graph_indexes(db)

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
        [
            ("organization_id", ASCENDING),
            ("supplier_id", ASCENDING),
            ("status", ASCENDING),
            ("accrued_at", DESCENDING),
        ],
        name="accruals_by_supplier_status",
    )

    # refund_cases: queue + uniqueness per booking
    await _safe_create(
        db.refund_cases,
        [("organization_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
        name="refund_cases_queue",
    )

    await _safe_create(
        db.refund_cases,
        [("organization_id", ASCENDING), ("booking_id", ASCENDING), ("created_at", DESCENDING)],
        name="refund_cases_by_booking",
    )

    await _safe_create(
        db.refund_cases,
        [("organization_id", ASCENDING), ("booking_id", ASCENDING)],
        unique=True,
        partialFilterExpression={
            "status": {"$in": ["open", "pending_approval"]},
            "type": "refund",
        },
        name="uniq_open_refund_case_per_booking",
    )

    # booking_financials (Phase 2B.4)
    await _safe_create(
        db.booking_financials,
        [("organization_id", ASCENDING), ("booking_id", ASCENDING)],
        unique=True,
        name="uniq_booking_financials_per_booking",
    )

    await _safe_create(
        db.booking_financials,
        [("organization_id", ASCENDING), ("updated_at", DESCENDING)],
        name="booking_financials_recent",
    )

    await _safe_create(
        db.booking_financials,
        [("organization_id", ASCENDING), ("refunds_applied.refund_case_id", ASCENDING)],
        name="booking_financials_by_refund_case",
    )
    
    # Settlement join/lookup
    await _safe_create(
        db.supplier_accruals,
        [("organization_id", ASCENDING), ("settlement_id", ASCENDING)],
        name="accruals_by_settlement",
    )

    # ========================================================================
    # fx_rates & fx_rate_snapshots (Phase 2C)
    # ========================================================================

    # fx_rates: lookup by (org, base, quote, as_of desc)
    await _safe_create(
        db.fx_rates,
        [("organization_id", ASCENDING), ("base", ASCENDING), ("quote", ASCENDING), ("as_of", DESCENDING)],
        name="fx_rates_by_pair_asof",
    )

    # Optional uniqueness on exact (org, base, quote, as_of)
    await _safe_create(
        db.fx_rates,
        [("organization_id", ASCENDING), ("base", ASCENDING), ("quote", ASCENDING), ("as_of", ASCENDING)],
        unique=True,
        name="uniq_fx_rate_by_pair_asof",
    )

    # fx_rate_snapshots: 1 snapshot per booking+pair
    await _safe_create(
        db.fx_rate_snapshots,
        [
            ("organization_id", ASCENDING),
            ("context.type", ASCENDING),
            ("context.id", ASCENDING),
            ("base", ASCENDING),
            ("quote", ASCENDING),
        ],
        unique=True,
        name="uniq_fx_snapshot_booking_pair",
    )
    
    # Ops debug (recent accruals)
    await _safe_create(
        db.supplier_accruals,
        [("organization_id", ASCENDING), ("accrued_at", DESCENDING)],
        name="accruals_recent",
    )

    # ========================================================================
    # settlement_runs (Phase 2A.4)
    # ========================================================================

    # List/filter by supplier/currency/status
    await _safe_create(
        db.settlement_runs,
        [
            ("organization_id", ASCENDING),
            ("supplier_id", ASCENDING),
            ("currency", ASCENDING),
            ("status", ASCENDING),
        ],
        name="settlements_by_supplier_currency_status",
    )

    # Recent settlements per org
    await _safe_create(
        db.settlement_runs,
        [("organization_id", ASCENDING), ("created_at", DESCENDING)],
        name="settlements_recent",
    )

    # Optional: prevent multiple OPEN (draft/approved) runs per (supplier, currency)
    await _safe_create(
        db.settlement_runs,
        [
            ("organization_id", ASCENDING),
            ("supplier_id", ASCENDING),
            ("currency", ASCENDING),
        ],
        unique=True,
        partialFilterExpression={"status": {"$in": ["draft", "approved"]}},
        name="uniq_open_run_per_supplier_currency",
    )
    

    # booking_amendments: per-booking+request idempotency
    await _safe_create(
        db.booking_amendments,
        [
            ("organization_id", ASCENDING),
            ("booking_id", ASCENDING),
            ("request_id", ASCENDING),
        ],
        unique=True,
        name="uniq_booking_amend_request_per_booking",
    )

    logger.info("✅ Phase 2A indexes ensured successfully")
