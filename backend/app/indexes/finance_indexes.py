"""
Finance indexes for Ledger OS (Phase 1)
Ensures data integrity and query performance
"""
from __future__ import annotations

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure
import logging

logger = logging.getLogger(__name__)


async def ensure_finance_indexes(db):
    """Ensure indexes for finance collections.
    
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
                    "[finance_indexes] Keeping legacy index for %s (name=%s): %s",
                    collection.name,
                    kwargs.get("name"),
                    msg,
                )
                return
            raise

    # ========================================================================
    # 1) finance_accounts
    # ========================================================================
    await _safe_create(
        db.finance_accounts,
        [("organization_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="uniq_account_code_per_org",
    )
    await _safe_create(
        db.finance_accounts,
        [("organization_id", ASCENDING), ("type", ASCENDING), ("owner_id", ASCENDING)],
        name="accounts_by_owner",
    )
    await _safe_create(
        db.finance_accounts,
        [("organization_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
        name="accounts_list",
    )

    # ========================================================================
    # 2) ledger_entries (immutable)
    # ========================================================================
    await _safe_create(
        db.ledger_entries,
        [("organization_id", ASCENDING), ("account_id", ASCENDING), ("posted_at", DESCENDING)],
        name="entries_by_account_posted",
    )
    await _safe_create(
        db.ledger_entries,
        [("organization_id", ASCENDING), ("source.type", ASCENDING), ("source.id", ASCENDING)],
        name="entries_by_source",
    )
    await _safe_create(
        db.ledger_entries,
        [("organization_id", ASCENDING), ("meta.booking_id", ASCENDING)],
        name="entries_by_booking",
        sparse=True,  # not all entries have booking_id
    )
    await _safe_create(
        db.ledger_entries,
        [("organization_id", ASCENDING), ("posted_at", DESCENDING)],
        name="entries_by_posted_at",
    )

    # ========================================================================
    # 3) ledger_postings (idempotency header)
    # ========================================================================
    await _safe_create(
        db.ledger_postings,
        [("organization_id", ASCENDING), ("source.type", ASCENDING), ("source.id", ASCENDING), ("event", ASCENDING)],
        unique=True,
        name="uniq_posting_per_source_event",
    )
    await _safe_create(
        db.ledger_postings,
        [("organization_id", ASCENDING), ("created_at", DESCENDING)],
        name="postings_by_created",
    )

    # ========================================================================
    # 4) credit_profiles
    # ========================================================================
    await _safe_create(
        db.credit_profiles,
        [("organization_id", ASCENDING), ("agency_id", ASCENDING)],
        unique=True,
        name="uniq_credit_profile_per_agency",
    )

    # ========================================================================
    # 5) account_balances (cached)
    # ========================================================================
    await _safe_create(
        db.account_balances,
        [("organization_id", ASCENDING), ("account_id", ASCENDING), ("currency", ASCENDING)],
        unique=True,
        name="uniq_balance_per_account_currency",
    )

    # ========================================================================
    # 6) payments
    # ========================================================================
    await _safe_create(
        db.payments,
        [("organization_id", ASCENDING), ("account_id", ASCENDING), ("received_at", DESCENDING)],
        name="payments_by_account_received",
    )
    await _safe_create(
        db.payments,
        [("organization_id", ASCENDING), ("created_at", DESCENDING)],
        name="payments_by_created",
    )

    logger.info("✅ Finance indexes ensured successfully")
