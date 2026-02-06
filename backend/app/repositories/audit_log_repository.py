from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.db import get_db

logger = logging.getLogger(__name__)


class AuditLogRepository:
  """Repository for audit_logs collection."""

  async def _col(self):
    db = await get_db()
    return db.audit_logs

  async def append(self, doc: Dict[str, Any]) -> str:
    col = await self._col()
    doc.setdefault("id", "audit_" + uuid4().hex[:12])
    doc.setdefault("created_at", datetime.now(timezone.utc))
    await col.insert_one(doc)
    return doc["id"]

  async def list_logs(
    self,
    tenant_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 50,
    before_id: Optional[str] = None,
  ) -> List[Dict[str, Any]]:
    col = await self._col()
    flt: Dict[str, Any] = {}
    if tenant_id:
      flt["tenant_id"] = tenant_id
    if action:
      flt["action"] = action
    if before_id:
      ref = await col.find_one({"id": before_id}, {"created_at": 1})
      if ref:
        flt["created_at"] = {"$lt": ref["created_at"]}

    cursor = col.find(flt, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)

  async def ensure_indexes(self) -> None:
    col = await self._col()
    await col.create_index("tenant_id")
    await col.create_index("action")
    await col.create_index([("created_at", -1)])


audit_log_repo = AuditLogRepository()
