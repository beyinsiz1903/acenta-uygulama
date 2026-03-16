"""Configuration Version History Router.

Endpoints:
  GET /api/config-versions/{entity_type}/{entity_id} - Version history
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.services.config_versioning_service import get_version_history

router = APIRouter(prefix="/api/config-versions", tags=["Config Versions"])


@router.get("/{entity_type}/{entity_id}")
async def version_history(
    entity_type: str,
    entity_id: str,
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
):
    org_id = user["organization_id"]
    versions = await get_version_history(entity_type, entity_id, org_id, limit=limit)
    return {"versions": versions, "entity_type": entity_type, "entity_id": entity_id}
