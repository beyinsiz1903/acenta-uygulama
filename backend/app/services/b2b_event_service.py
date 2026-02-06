from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.repositories.b2b_event_repository import b2b_event_repo

logger = logging.getLogger(__name__)


async def append_b2b_event(
  event_type: str,
  entity_type: str,
  entity_id: str,
  listing_id: Optional[str] = None,
  provider_tenant_id: Optional[str] = None,
  seller_tenant_id: Optional[str] = None,
  actor_user_id: Optional[str] = None,
  payload: Optional[Dict[str, Any]] = None,
) -> None:
  """Best-effort B2B event append. Never raises."""
  try:
    doc = {
      "event_type": event_type,
      "entity_type": entity_type,
      "entity_id": entity_id,
      "listing_id": listing_id,
      "provider_tenant_id": provider_tenant_id,
      "seller_tenant_id": seller_tenant_id,
      "actor_user_id": actor_user_id,
      "payload": payload or {},
    }
    await b2b_event_repo.append(doc)
  except Exception:
    logger.warning("b2b_event write failed", exc_info=True)


async def list_b2b_events(
  tenant_id: Optional[str] = None,
  entity_id: Optional[str] = None,
  listing_id: Optional[str] = None,
  event_type: Optional[str] = None,
  limit: int = 50,
  cursor: Optional[str] = None,
) -> List[Dict[str, Any]]:
  return await b2b_event_repo.list_events(
    tenant_id=tenant_id,
    entity_id=entity_id,
    listing_id=listing_id,
    event_type=event_type,
    limit=limit,
    before_id=cursor,
  )
