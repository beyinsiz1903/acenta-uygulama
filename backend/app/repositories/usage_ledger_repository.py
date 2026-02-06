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

  async def append(
    self,
    tenant_id: str,
    metric: str,
    quantity: int,
    source: str,
    source_event_id: str,
    billing_period: Optional[str] = None,
  ) -> bool:
    """Append usage entry. Returns True if inserted, False if duplicate."""
    col = await self._col()
    now = datetime.now(timezone.utc)
    if not billing_period:
      billing_period = now.strftime("%Y-%m")

    doc = {
      "tenant_id": tenant_id,
      "metric": metric,
      "quantity": quantity,
      "timestamp": now,
      "billing_period": billing_period,
      "billed": False,
      "source": source,
      "source_event_id": source_event_id,
    }

    from pymongo.errors import DuplicateKeyError
    try:
      await col.insert_one(doc)
      return True
    except DuplicateKeyError:
      return False

  async def get_period_totals(
    self,
    tenant_id: str,
    billing_period: str,
  ) -> Dict[str, int]:
    """Aggregate usage totals by metric for a billing period."""
    col = await self._col()
    pipeline = [
      {"$match": {"tenant_id": tenant_id, "billing_period": billing_period}},
      {"$group": {"_id": "$metric", "total": {"$sum": "$quantity"}}},
    ]
    cursor = col.aggregate(pipeline)
    results = await cursor.to_list(length=100)
    return {r["_id"]: r["total"] for r in results}

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


usage_ledger_repo = UsageLedgerRepository()
