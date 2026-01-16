from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_feature, require_roles
from app.db import get_db
from app.services.api_keys import create_api_key, list_api_keys


router = APIRouter(prefix="/api/admin/api-keys", tags=["admin_api_keys"])


AdminDep = Depends(require_roles(["super_admin", "admin"]))
FeatureDep = Depends(require_feature("partner_api"))


class ApiKeyCreateIn(BaseModel):
    name: str = Field(..., min_length=1)
    scopes: List[str] = Field(default_factory=list)


@router.get("")
async def get_api_keys(
    user=AdminDep,  # noqa: B008
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id missing")
    items = await list_api_keys(organization_id=org_id)
    return {"items": items}


@router.post("")
async def create_key(
    payload: ApiKeyCreateIn,
    user=AdminDep,  # noqa: B008
    _feature=FeatureDep,  # noqa: B008
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id missing")

    res = await create_api_key(
        organization_id=org_id,
        name=payload.name,
        scopes=payload.scopes,
    )
    return {"ok": True, "api_key": res["api_key"], "meta": {"name": res["name"], "scopes": res["scopes"]}}
