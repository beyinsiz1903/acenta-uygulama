from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.repositories.audit_log_repository import audit_log_repo

logger = logging.getLogger(__name__)


async def append_audit_log(
  scope: str,
  tenant_id: str,
  actor_user_id: str,
  actor_email: str,
  action: str,
  before: Any = None,
  after: Any = None,
  metadata: Optional[Dict[str, Any]] = None,
) -> None:
  """Best-effort audit log append. Never raises."""
  try:
    doc = {
      "scope": scope,
      "tenant_id": tenant_id,
      "actor_user_id": actor_user_id,
      "actor_email": actor_email,
      "action": action,
      "before": before,
      "after": after,
      "metadata": metadata or {},
    }
    await audit_log_repo.append(doc)
  except Exception:
    logger.warning("audit_log write failed", exc_info=True)


async def list_audit_logs(
  tenant_id: Optional[str] = None,
  action: Optional[str] = None,
  limit: int = 50,
  cursor: Optional[str] = None,
) -> List[Dict[str, Any]]:
  return await audit_log_repo.list_logs(
    tenant_id=tenant_id,
    action=action,
    limit=limit,
    before_id=cursor,
  )
