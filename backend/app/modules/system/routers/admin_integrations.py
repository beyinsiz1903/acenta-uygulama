from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_feature, require_roles
from app.db import get_db
from app.services.integration_hub import (
    enqueue_sync_jobs_for_provider,
    list_credentials,
    list_mappings,
    list_providers,
    upsert_credentials,
    upsert_mapping,
    upsert_provider,
)


router = APIRouter(prefix="/api/admin/integrations", tags=["admin_integrations"])


AdminDep = Depends(require_roles(["super_admin"]))
FeatureDep = Depends(require_feature("integration_hub"))


class ProviderIn(BaseModel):
    key: str = Field(..., min_length=3)
    name: str
    category: str = Field(..., description="hotel|tour|other")
    capabilities: List[str] = Field(default_factory=list)


class CredentialsIn(BaseModel):
    provider_key: str
    name: Optional[str] = None
    status: str = Field(default="active")
    config: Dict[str, Any] = Field(default_factory=dict)


class MappingIn(BaseModel):
    provider_key: str
    mapping_type: str = Field(..., description="hotel|room_type|rate_plan|location")
    internal_id: str
    external_id: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class SyncRequest(BaseModel):
    provider_key: str
    scope: str = Field(default="both", description="availability|rates|both")


@router.get("/providers")
async def get_providers(
    _user=AdminDep,  # noqa: B008
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> Dict[str, Any]:
    items = await list_providers(db)
    return {"items": items}


@router.post("/providers")
async def create_or_update_provider(
    payload: ProviderIn,
    _user=AdminDep,  # noqa: B008
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> Dict[str, Any]:
    doc = await upsert_provider(db, payload.model_dump())
    return {"ok": True, "provider": doc}


@router.get("/credentials")
async def get_credentials(
    user=AdminDep,  # noqa: B008
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id missing")
    items = await list_credentials(db, org_id)
    return {"items": items}


@router.post("/credentials")
async def create_or_update_credentials(
    payload: CredentialsIn,
    user=AdminDep,  # noqa: B008
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id missing")
    doc = await upsert_credentials(db, org_id, payload.model_dump())
    return {"ok": True, "credentials": doc}


@router.get("/mappings")
async def get_mappings(
    provider_key: Optional[str] = None,
    user=AdminDep,  # noqa: B008
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id missing")
    items = await list_mappings(db, org_id, provider_key)
    return {"items": items}


@router.post("/mappings")
async def create_or_update_mapping(
    payload: MappingIn,
    user=AdminDep,  # noqa: B008
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id missing")
    doc = await upsert_mapping(db, org_id, payload.model_dump())
    return {"ok": True, "mapping": doc}


@router.post("/sync")
async def trigger_sync(
    payload: SyncRequest,
    user=AdminDep,  # noqa: B008
    _feature=FeatureDep,  # noqa: B008
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id missing")

    count = await enqueue_sync_jobs_for_provider(
        organization_id=org_id,
        provider_key=payload.provider_key,
        scope=payload.scope,
    )
    return {"ok": True, "enqueued": count}


@router.get("/health")
async def get_integration_health(
    user=AdminDep,  # noqa: B008
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id missing")

    # Simple aggregation over jobs collection
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "type": {"$in": ["integration.sync_availability", "integration.sync_rates"]},
            }
        },
        {
            "$group": {
                "_id": {"type": "$type", "status": "$status"},
                "count": {"$sum": 1},
            }
        },
    ]
    rows = await db.jobs.aggregate(pipeline).to_list(length=1000)

    summary: Dict[str, Dict[str, int]] = {}
    for row in rows:
        group = row.get("_id") or {}
        job_type = group.get("type") or "unknown"
        status = group.get("status") or "unknown"
        key = job_type
        if key not in summary:
            summary[key] = {"succeeded": 0, "failed": 0, "dead": 0}
        if status in summary[key]:
            summary[key][status] += int(row.get("count") or 0)

    return {"items": summary}
