from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection, with_org_filter
from app.utils import now_utc


class BookingRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._col = get_collection(db, "bookings")

    async def create_draft(self, organization_id: str, payload: Dict[str, Any]) -> str:
        now = now_utc()
        doc: Dict[str, Any] = {
            "organization_id": organization_id,
            "agency_id": payload.get("agency_id"),
            "customer_id": payload.get("customer_id"),
            "supplier_id": payload.get("supplier_id"),
            "state": "draft",
            "amount": float(payload.get("amount", 0.0)),
            "currency": payload.get("currency", "TRY"),
            "booking_ref": payload.get("booking_ref"),
            "created_at": now,
            "updated_at": now,
        }
        res = await self._col.insert_one(doc)
        return str(res.inserted_id)

    async def get_by_id(self, organization_id: str, booking_id: str) -> Optional[Dict[str, Any]]:
        from bson import ObjectId

        try:
            oid = ObjectId(booking_id)
        except Exception:
            return None

        doc = await self._col.find_one(with_org_filter({"_id": oid}, organization_id))
        return doc

    async def update_state(
        self,
        organization_id: str,
        booking_id: str,
        new_state: str,
        extra_updates: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Update booking state and return (before, after) documents.

        Returns (None, None) if booking not found.
        """

        doc = await self.get_by_id(organization_id, booking_id)
        if not doc:
            return None, None

        before = dict(doc)
        updates: Dict[str, Any] = {"state": new_state, "updated_at": now_utc()}
        if extra_updates:
            updates.update(extra_updates)

        await self._col.update_one(
            with_org_filter({"_id": doc["_id"]}, organization_id),
            {"$set": updates},
        )

        after = await self.get_by_id(organization_id, booking_id)
        return before, after

    async def list_bookings(
        self,
        organization_id: str,
        *,
        state: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        flt: Dict[str, Any] = {}
        if state:
            flt["state"] = state
        if start_date or end_date:
            date_range: Dict[str, Any] = {}
            if start_date:
                date_range["$gte"] = start_date
            if end_date:
                date_range["$lte"] = end_date
            flt["created_at"] = date_range

        cursor = self._col.find(with_org_filter(flt, organization_id)).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(limit)
        return docs
