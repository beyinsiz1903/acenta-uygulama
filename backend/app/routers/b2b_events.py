from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.security.b2b_context import B2BTenantContext, get_b2b_tenant_context
from app.security.feature_flags import require_b2b_feature
from app.constants.features import FEATURE_B2B
from app.services.b2b_event_service import list_b2b_events

router = APIRouter(prefix="/api/b2b/events", tags=["b2b_events"])


def _serialize_item(item: dict) -> dict:
  out = dict(item)
  for k, v in out.items():
    if isinstance(v, datetime):
      out[k] = v.isoformat()
  return out


@router.get("")
async def get_b2b_events(
  tenant_ctx: B2BTenantContext = Depends(get_b2b_tenant_context),
  _: None = Depends(require_b2b_feature(FEATURE_B2B)),
  entity_id: Optional[str] = Query(None),
  listing_id: Optional[str] = Query(None),
  event_type: Optional[str] = Query(None),
  limit: int = Query(50, le=200),
  cursor: Optional[str] = Query(None),
) -> dict:
  """B2B: list events scoped to current tenant with optional filters."""
  items = await list_b2b_events(
    tenant_id=tenant_ctx.tenant_id,
    entity_id=entity_id,
    listing_id=listing_id,
    event_type=event_type,
    limit=limit,
    cursor=cursor,
  )
  serialized = [_serialize_item(i) for i in items]
  next_cursor = serialized[-1]["id"] if serialized else None
  return {"items": serialized, "next_cursor": next_cursor}
