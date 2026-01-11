from __future__ import annotations

"""Indexes for inbox threads and messages (FAZ 4 Inbox/Bildirim Merkezi)."""

import logging
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)


async def ensure_inbox_indexes(db):
    """Ensure indexes for inbox_threads and inbox_messages collections."""

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
                    "[inbox_indexes] Keeping legacy index for %s (name=%s): %s",
                    collection.name,
                    kwargs.get("name"),
                    msg,
                )
                return
            raise

    # Threads: by org + booking, and by status/last_message_at for listing
    await _safe_create(
        db.inbox_threads,
        [("organization_id", ASCENDING), ("booking_id", ASCENDING)],
        name="idx_inbox_threads_org_booking",
    )

    await _safe_create(
        db.inbox_threads,
        [
            ("organization_id", ASCENDING),
            ("status", ASCENDING),
            ("last_message_at", DESCENDING),
        ],
        name="idx_inbox_threads_org_status_lastmsg",
    )

    # Messages: by thread + created_at, and org+thread
    await _safe_create(
        db.inbox_messages,
        [("thread_id", ASCENDING), ("created_at", ASCENDING)],
        name="idx_inbox_messages_thread_created",
    )

    await _safe_create(
        db.inbox_messages,
        [("organization_id", ASCENDING), ("thread_id", ASCENDING)],
        name="idx_inbox_messages_org_thread",
    )
