from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db import get_db

logger = logging.getLogger(__name__)


class UsageLedgerRepository:
  """Repository for usage_ledger collection.

  Schema:
  {
    tenant_id: str,
    metric: str,
    quantity: int,
    timestamp: datetime,
    billing_period: str (YYYY-MM),
    billed: bool,
    source: str,
    source_event_id: str,
  }
  Unique index: (tenant_id, metric, source_event_id)
  """

  async def _col(self):
    db = await get_db()
    return db.usage_ledger

  async def insert_event(
    self,
    *,
    tenant_id: str,
    organization_id: Optional[str],
    metric: str,
    quantity: int,
    source: str,
    source_event_id: str,
    billing_period: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None,
  ) -> Optional[str]:
    """Insert a usage event. Returns event id, or None if duplicate."""
    col = await self._col()
    now = timestamp or datetime.now(timezone.utc)
    if not billing_period:
      billing_period = now.strftime("%Y-%m")

    doc = {
      "tenant_id": tenant_id,
      "metric": metric,
      "quantity": quantity,
      "timestamp": now,
      "billing_period": billing_period,
      "billed": False,
      "pushed_at": None,
      "stripe_usage_record_id": None,
      "push_attempts": 0,
      "last_push_error": None,
      "source": source,
      "source_event_id": source_event_id,
    }
    if organization_id:
      doc["organization_id"] = organization_id
    if metadata:
      doc["metadata"] = metadata

    from pymongo.errors import DuplicateKeyError
    try:
      res = await col.insert_one(doc)
      return str(res.inserted_id)
    except DuplicateKeyError:
      return None

  async def append(
    self,
    tenant_id: str,
    metric: str,
    quantity: int,
    source: str,
    source_event_id: str,
    billing_period: Optional[str] = None,
  ) -> bool:
    """Backward-compatible append helper. Returns True if inserted, False if duplicate."""
    inserted_id = await self.insert_event(
      tenant_id=tenant_id,
      organization_id=None,
      metric=metric,
      quantity=quantity,
      source=source,
      source_event_id=source_event_id,
      billing_period=billing_period,
    )
    return inserted_id is not None

  async def delete_event(self, event_id: str) -> None:
    col = await self._col()
    from bson import ObjectId

    try:
      oid = ObjectId(event_id)
    except Exception:
      return
    await col.delete_one({"_id": oid})

  async def get_period_totals(
    self,
    tenant_id: str,
    billing_period: str,
    organization_id: Optional[str] = None,
  ) -> Dict[str, int]:
    """Aggregate usage totals by metric for a billing period."""
    col = await self._col()
    match: Dict[str, Any] = {"tenant_id": tenant_id, "billing_period": billing_period}
    if organization_id:
      match["organization_id"] = organization_id
    pipeline = [
      {"$match": match},
      {"$group": {"_id": "$metric", "total": {"$sum": "$quantity"}}},
    ]
    cursor = col.aggregate(pipeline)
    results = await cursor.to_list(length=100)
    return {r["_id"]: r["total"] for r in results}

  async def get_unbilled(self, billing_period: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
    """Get unbilled usage entries for push."""
    col = await self._col()
    flt: Dict[str, Any] = {"billed": False}
    if billing_period:
      flt["billing_period"] = billing_period
    cursor = col.find(flt, {"_id": 1, "tenant_id": 1, "metric": 1, "quantity": 1, "timestamp": 1, "source_event_id": 1, "push_attempts": 1}).sort("timestamp", 1).limit(limit)
    return await cursor.to_list(length=limit)

  async def mark_pushed(self, doc_id, stripe_usage_record_id: str) -> None:
    """Mark a usage entry as pushed to Stripe."""
    col = await self._col()
    await col.update_one(
      {"_id": doc_id},
      {"$set": {"billed": True, "pushed_at": datetime.now(timezone.utc), "stripe_usage_record_id": stripe_usage_record_id}},
    )

  async def mark_push_error(self, doc_id, error: str) -> None:
    """Record push error for a usage entry."""
    col = await self._col()
    await col.update_one(
      {"_id": doc_id},
      {"$set": {"last_push_error": error}, "$inc": {"push_attempts": 1}},
    )

  async def ensure_indexes(self) -> None:
    col = await self._col()
    await col.create_index(
      [("tenant_id", 1), ("metric", 1), ("source_event_id", 1)],
      unique=True,
      name="usage_idempotency",
    )
    await col.create_index(
      [("tenant_id", 1), ("billing_period", 1), ("metric", 1), ("timestamp", -1)],
      name="usage_period_lookup",
    )
    await col.create_index(
      [("tenant_id", 1), ("metric", 1), ("timestamp", -1)],
      name="usage_metric_time_lookup",
    )


usage_ledger_repo = UsageLedgerRepository()
