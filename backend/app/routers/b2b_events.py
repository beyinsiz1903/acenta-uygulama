from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.security.b2b_context import B2BTenantContext, get_b2b_tenant_context
from app.security.feature_flags import require_b2b_feature
from app.constants.features import FEATURE_B2B
from app.services.b2b_event_service import list_b2b_events

router = APIRouter(prefix="/api/b2b/events", tags=["b2b_events"])


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
  next_cursor = items[-1]["id"] if items else None
  return {"items": items, "next_cursor": next_cursor}
