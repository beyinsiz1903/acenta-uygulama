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
    # For booking-level events we rely on higher-level idempotency (request_id,
    # amend_id, etc.), so we do not enforce a global per-(source,event) unique
    # constraint here. This allows multiple BOOKING_AMENDED postings for the
    # same booking (multi-amend v1.5).
    await _safe_create(
        db.ledger_postings,
        [("organization_id", ASCENDING), ("source.type", ASCENDING), ("source.id", ASCENDING), ("event", ASCENDING), ("meta.amend_id", ASCENDING)],
        unique=True,
        name="uniq_posting_per_source_event",
        partialFilterExpression={"meta.amend_id": {"$exists": True}},
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

    # ========================================================================
    # 7) booking_events (lifecycle log)
    # ========================================================================
    await _safe_create(
        db.booking_events,
        [("organization_id", ASCENDING), ("booking_id", ASCENDING), ("occurred_at", DESCENDING)],
        name="booking_events_by_booking",
    )
    await _safe_create(
        db.booking_events,
        [("organization_id", ASCENDING), ("booking_id", ASCENDING), ("event", ASCENDING), ("request_id", ASCENDING)],
        unique=True,
        name="uniq_booking_event_per_request",
        partialFilterExpression={"request_id": {"$type": "string"}},
    )

    # ========================================================================
    # 8) booking_payments (booking-level payment aggregate)
    # ========================================================================
    await _safe_create(
        db.booking_payments,
        [("organization_id", ASCENDING), ("booking_id", ASCENDING)],
        unique=True,
        name="uniq_booking_payment_per_booking",
    )
    await _safe_create(
        db.booking_payments,
        [("organization_id", ASCENDING), ("stripe.payment_intent_id", ASCENDING)],
        unique=True,
        name="uniq_booking_payment_per_pi",
        partialFilterExpression={"stripe.payment_intent_id": {"$type": "string"}},
    )
    await _safe_create(
        db.booking_payments,
        [
            ("organization_id", ASCENDING),
            ("agency_id", ASCENDING),
            ("status", ASCENDING),
            ("updated_at", DESCENDING),
        ],
        name="booking_payments_by_agency_status",
    )

    # ========================================================================
    # 9) booking_payment_transactions (append-only payment ops log)
    # ========================================================================
    await _safe_create(
        db.booking_payment_transactions,
        [("organization_id", ASCENDING), ("booking_id", ASCENDING), ("occurred_at", ASCENDING)],
        name="booking_payment_tx_by_booking_time",
    )
    await _safe_create(
        db.booking_payment_transactions,
        [("payment_id", ASCENDING), ("occurred_at", ASCENDING)],
        name="booking_payment_tx_by_payment_time",
    )
    await _safe_create(
        db.booking_payment_transactions,
        [("provider", ASCENDING), ("provider_event_id", ASCENDING)],
        unique=True,
        name="uniq_booking_payment_tx_per_provider_event",
        partialFilterExpression={"provider_event_id": {"$type": "string"}},
    )
    await _safe_create(
        db.booking_payment_transactions,
        [
            ("organization_id", ASCENDING),
            ("booking_id", ASCENDING),
            ("request_id", ASCENDING),
            ("type", ASCENDING),
        ],
        unique=True,
        name="uniq_booking_payment_tx_per_request_type",
        partialFilterExpression={"request_id": {"$type": "string"}},
    )

    # ========================================================================
    # 10) click_to_pay_links
    # ========================================================================
    # Click-to-pay links: token_hash uniqueness + TTL index on expires_at
    await _safe_create(
        db.click_to_pay_links,
        [("token_hash", ASCENDING)],
        unique=True,
        name="uniq_click_to_pay_token_hash",
    )
    await _safe_create(
        db.click_to_pay_links,
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="ttl_click_to_pay_expires_at",
    )


    logger.info("✅ Finance indexes ensured successfully")
