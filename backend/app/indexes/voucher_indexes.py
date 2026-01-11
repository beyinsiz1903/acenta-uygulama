from __future__ import annotations

"""Indexes for voucher file storage (FAZ 1)."""

from pymongo import ASCENDING
from pymongo.errors import OperationFailure
import logging

logger = logging.getLogger(__name__)


async def ensure_voucher_indexes(db):
    """Ensure indexes for files_vouchers collection.

    Unique per (organization_id, booking_id, version, issue_reason).
    """

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
                    "[voucher_indexes] Keeping legacy index for %s (name=%s): %s",
                    collection.name,
                    kwargs.get("name"),
                    msg,
                )
                return
            raise

    await _safe_create(
        db.files_vouchers,
        [
            ("organization_id", ASCENDING),
            ("booking_id", ASCENDING),
            ("version", ASCENDING),
            ("issue_reason", ASCENDING),
        ],
        unique=True,
        name="uniq_voucher_file_per_booking_version_reason",
    )
