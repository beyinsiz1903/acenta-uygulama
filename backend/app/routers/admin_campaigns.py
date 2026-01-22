from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc


router = APIRouter(prefix="/api/admin/campaigns", tags=["admin_campaigns"])


AdminDep = Depends(require_roles(["super_admin", "admin"]))


class CampaignBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    active: bool = True
    channels: List[str] = Field(default_factory=lambda: ["B2C"], description="B2B/B2C/BOTH flags")
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    coupon_codes: List[str] = Field(default_factory=list, description="Related coupon codes (upper-case)")


class CampaignCreateIn(CampaignBase):
    pass


class CampaignUpdateIn(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    active: Optional[bool] = None
    channels: Optional[List[str]] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    coupon_codes: Optional[List[str]] = None


class CampaignOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    active: bool
    channels: List[str]
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    coupon_codes: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


@router.get("", response_model=List[CampaignOut], dependencies=[AdminDep])
async def list_campaigns(
    active: Optional[bool] = Query(default=None),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
) -> List[CampaignOut]:
    org_id = user["organization_id"]
    query: Dict[str, Any] = {"organization_id": org_id}
    if active is not None:
        query["active"] = active

    cursor = db.campaigns.find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=500)
    return [CampaignOut(**serialize_doc(d)) for d in docs]


@router.post("", response_model=CampaignOut, dependencies=[AdminDep])
async def create_campaign(
    payload: CampaignCreateIn,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
) -> CampaignOut:
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()

    if payload.valid_from and payload.valid_to and payload.valid_to <= payload.valid_from:
        raise HTTPException(status_code=400, detail="valid_to must be after valid_from")

    slug = payload.slug.strip()
    name = payload.name.strip()
    if not slug or not name:
        raise HTTPException(status_code=400, detail="name and slug are required")

    codes = [c.strip().upper() for c in (payload.coupon_codes or []) if c.strip()]

    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "name": name,
        "slug": slug,
        "description": payload.description or "",
        "active": payload.active,
        "channels": payload.channels or ["B2C"],
        "valid_from": payload.valid_from,
        "valid_to": payload.valid_to,
        "coupon_codes": codes,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.campaigns.insert_one(doc)
    doc["_id"] = res.inserted_id
    return CampaignOut(**serialize_doc(doc))


@router.patch("/{campaign_id}", response_model=CampaignOut, dependencies=[AdminDep])
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdateIn,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
) -> CampaignOut:
    org_id = user["organization_id"]

    try:
        oid = ObjectId(campaign_id)
    except Exception:
        raise HTTPException(status_code=404, detail="CAMPAIGN_NOT_FOUND")

    data = payload.model_dump(exclude_unset=True)

    if data.get("valid_from") and data.get("valid_to") and data["valid_to"] <= data["valid_from"]:
        raise HTTPException(status_code=400, detail="valid_to must be after valid_from")

    update: Dict[str, Any] = {}
    for field in [
        "name",
        "slug",
        "description",
        "active",
        "channels",
        "valid_from",
        "valid_to",
    ]:
        if field in data:
            update[field] = data[field]

    if "coupon_codes" in data:
        codes = [c.strip().upper() for c in (data["coupon_codes"] or []) if c.strip()]
        update["coupon_codes"] = codes

    if not update:
        doc = await db.campaigns.find_one({"_id": oid, "organization_id": org_id})
        if not doc:
            raise HTTPException(status_code=404, detail="CAMPAIGN_NOT_FOUND")
        return CampaignOut(**serialize_doc(doc))

    update["updated_at"] = datetime.now(timezone.utc).isoformat()

    res = await db.campaigns.update_one({"_id": oid, "organization_id": org_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="CAMPAIGN_NOT_FOUND")

    doc = await db.campaigns.find_one({"_id": oid, "organization_id": org_id})
    if not doc:
        raise HTTPException(status_code=404, detail="CAMPAIGN_NOT_FOUND")

    return CampaignOut(**serialize_doc(doc))
