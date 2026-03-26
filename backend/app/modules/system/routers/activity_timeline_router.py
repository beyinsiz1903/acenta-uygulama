"""Activity Timeline Router — Centralized Audit Trail API.

Endpoints:
  GET /api/activity-timeline           - List events with filters
  GET /api/activity-timeline/stats     - Aggregate stats
  GET /api/activity-timeline/entity/{entity_type}/{entity_id} - Entity history
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.services.activity_timeline_service import (
    get_timeline,
    get_entity_timeline,
    get_timeline_stats,
)

router = APIRouter(prefix="/api/activity-timeline", tags=["Activity Timeline"])


@router.get("")
async def list_timeline(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    org_id = user["organization_id"]
    return await get_timeline(
        org_id, skip=skip, limit=limit,
        entity_type=entity_type, entity_id=entity_id,
        actor=actor, action=action,
    )


@router.get("/stats")
async def timeline_stats(user=Depends(get_current_user)):
    org_id = user["organization_id"]
    return await get_timeline_stats(org_id)


@router.get("/entity/{entity_type}/{entity_id}")
async def entity_history(
    entity_type: str,
    entity_id: str,
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
):
    org_id = user["organization_id"]
    events = await get_entity_timeline(org_id, entity_type, entity_id, limit=limit)
    return {"events": events, "entity_type": entity_type, "entity_id": entity_id}
