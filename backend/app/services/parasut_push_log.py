from __future__ import annotations

"""Parasut push logging + idempotency helpers (PZ1).

This module implements the persistence layer for Paraşüt Push V1.
It does NOT talk to Paraşüt directly; it only maintains a log that
ensures idempotent behaviour per (organization, booking, push_type).

Collections used:
- parasut_push_log

Schema (MVP):
- organization_id: str
- booking_id: str
- push_type: str (e.g. "invoice_v1")
- dedupe_key: str (e.g. f"invoice_v1:{booking_id}")
- status: "pending" | "success" | "failed"
- parasut_contact_id: Optional[str]
- parasut_invoice_id: Optional[str]
- attempt_count: int
- last_error: Optional[str]
- created_at, updated_at: datetime
"""

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from app.utils import now_utc

ParasutPushStatus = Literal["pending", "success", "failed"]


class ParasutPushLogService:
    """Small service wrapper for parasut_push_log collection.

    Responsibility:
    - Provide idempotent lookup/create semantics for a given booking + push_type.
    - Increment attempt counters and update status/error fields.
    """

    def __init__(self, db):
        self.db = db

    @staticmethod
    def _dedupe_key(push_type: str, booking_id: str) -> str:
        return f"{push_type}:{booking_id}"

    async def get_existing(
        self,
        *,
        organization_id: str,
        booking_id: str,
        push_type: str,
    ) -> Optional[dict[str, Any]]:
        """Return existing log entry, if any.

        This is a pure lookup and does not modify state.
        """

        dedupe_key = self._dedupe_key(push_type, booking_id)
        doc = await self.db.parasut_push_log.find_one(
            {
                "organization_id": organization_id,
                "dedupe_key": dedupe_key,
            }
        )
        return doc

    async def get_or_create_pending(
        self,
        *,
        organization_id: str,
        booking_id: str,
        push_type: str = "invoice_v1",
    ) -> dict[str, Any]:
        """Get or create a pending push log for the given booking.

        Idempotency contract:
        - If an entry exists (any status), it is returned as-is.
        - Otherwise a new `pending` entry is inserted and returned.
        """

        dedupe_key = self._dedupe_key(push_type, booking_id)
        existing = await self.db.parasut_push_log.find_one(
            {
                "organization_id": organization_id,
                "dedupe_key": dedupe_key,
            }
        )
        if existing:
            return existing

        now = now_utc()
        doc = {
            "organization_id": organization_id,
            "booking_id": booking_id,
            "push_type": push_type,
            "dedupe_key": dedupe_key,
            "status": "pending",
            "parasut_contact_id": None,
            "parasut_invoice_id": None,
            "attempt_count": 0,
            "last_error": None,
            "created_at": now,
            "updated_at": now,
        }
        res = await self.db.parasut_push_log.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def mark_success(
        self,
        *,
        log_id,
        parasut_contact_id: Optional[str] = None,
        parasut_invoice_id: Optional[str] = None,
    ) -> None:
        """Mark a log row as success and update Paraşüt ids.

        Does not raise if the document does not exist.
        """

        now = now_utc()
        await self.db.parasut_push_log.update_one(
            {"_id": log_id},
            {
                "$set": {
                    "status": "success",
                    "parasut_contact_id": parasut_contact_id,
                    "parasut_invoice_id": parasut_invoice_id,
                    "updated_at": now,
                },
                "$inc": {"attempt_count": 1},
            },
        )

    async def mark_failed(self, *, log_id, error: str) -> None:
        """Mark a log row as failed and store last_error.

        Does not raise if the document does not exist.
        """

        now = now_utc()
        await self.db.parasut_push_log.update_one(
            {"_id": log_id},
            {
                "$set": {
                    "status": "failed",
                    "last_error": error,
                    "updated_at": now,
                },
                "$inc": {"attempt_count": 1},
            },
        )
