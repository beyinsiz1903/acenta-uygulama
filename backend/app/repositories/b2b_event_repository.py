from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.db import get_db

logger = logging.getLogger(__name__)


class B2BEventRepository:
  """Repository for b2b_events collection."""

  async def _col(self):
    db = await get_db()
    return db.b2b_events

  async def append(self, doc: Dict[str, Any]) -> str:
    col = await self._col()
    doc.setdefault("id", "evt_" + uuid4().hex[:12])
    doc.setdefault("created_at", datetime.now(timezone.utc))
    await col.insert_one(doc)
    return doc["id"]

  async def list_events(
    self,
    tenant_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    listing_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 50,
    before_id: Optional[str] = None,
  ) -> List[Dict[str, Any]]:
    col = await self._col()
    flt: Dict[str, Any] = {}

    if tenant_id:
      flt["$or"] = [
        {"provider_tenant_id": tenant_id},
        {"seller_tenant_id": tenant_id},
      ]
    if entity_id:
      flt["entity_id"] = entity_id
    if listing_id:
      flt["listing_id"] = listing_id
    if event_type:
      flt["event_type"] = event_type
    if before_id:
      ref = await col.find_one({"id": before_id}, {"created_at": 1})
      if ref:
        flt["created_at"] = {"$lt": ref["created_at"]}

    cursor = col.find(flt, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)

  async def ensure_indexes(self) -> None:
    col = await self._col()
    await col.create_index("entity_id")
    await col.create_index("listing_id")
    await col.create_index("provider_tenant_id")
    await col.create_index("seller_tenant_id")
    await col.create_index([("created_at", -1)])
    await col.create_index("event_type")


b2b_event_repo = B2BEventRepository()
