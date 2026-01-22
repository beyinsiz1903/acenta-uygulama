from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc


async def _load_agency_min(db, org_id: str, agency_id: str) -> Optional[Dict[str, Any]]:
    """Load minimal agency info for linking/summary.

    Accepts string or ObjectId-compatible id and scopes by organization.
    Returns a dict with _id and name or None when not found.
    """

    if not agency_id:
        return None

    # First try direct string _id
    doc = await db.agencies.find_one({"_id": agency_id, "organization_id": org_id}, {"name": 1})
    if doc:
        return doc

    try:
        oid = ObjectId(agency_id)
    except Exception:
        return None

    return await db.agencies.find_one({"_id": oid, "organization_id": org_id}, {"name": 1})


router = APIRouter(prefix="/api/admin/partners", tags=["admin_partners"])


AdminDep = Depends(require_roles(["super_admin", "admin", "ops"]))


class PartnerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    contact_email: Optional[str] = Field(None, max_length=200)
    status: str = Field("pending", pattern="^(pending|approved|blocked)$")
    api_key_name: Optional[str] = Field(None, max_length=200)
    default_markup_percent: float = Field(0.0, ge=-100.0, le=500.0)
    linked_agency_id: Optional[str] = Field(
        None,
        max_length=64,
        description="Optional agency id from agencies collection linked to this partner",
    )
    notes: Optional[str] = Field(None, max_length=2000)


class PartnerCreateIn(PartnerBase):
    pass


class PartnerUpdateIn(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_email: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None, pattern="^(pending|approved|blocked)$")
    api_key_name: Optional[str] = Field(None, max_length=200)
    default_markup_percent: Optional[float] = Field(None, ge=-100.0, le=500.0)
    linked_agency_id: Optional[str] = Field(
        None,
        max_length=64,
        description="Optional agency id from agencies collection linked to this partner",
    )
    notes: Optional[str] = Field(None, max_length=2000)


class PartnerOut(BaseModel):
    id: str
    name: str
    contact_email: Optional[str] = None
    status: str
    api_key_name: Optional[str] = None
    default_markup_percent: float
    linked_agency_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        orm_mode = True


@router.get("", response_model=List[PartnerOut], dependencies=[AdminDep])
async def list_partners(
    status: Optional[str] = Query(None, pattern="^(pending|approved|blocked)$"),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
) -> List[PartnerOut]:
    org_id = user["organization_id"]
    q: Dict[str, Any] = {"organization_id": org_id}
    if status:
        q["status"] = status

    cursor = db.partner_profiles.find(q).sort("created_at", -1)
    docs = await cursor.to_list(length=500)
    items: List[PartnerOut] = []
    for d in docs:
        data = serialize_doc(d)
        data["id"] = data.pop("_id")
        items.append(PartnerOut(**data))
    return items


@router.post("", response_model=PartnerOut, dependencies=[AdminDep])
async def create_partner(
    payload: PartnerCreateIn,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
) -> PartnerOut:
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()

    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "name": payload.name.strip(),
        "contact_email": (payload.contact_email or "").strip() or None,
        "status": payload.status,
        "api_key_name": (payload.api_key_name or "").strip() or None,
        "default_markup_percent": float(payload.default_markup_percent or 0.0),
        "linked_agency_id": (payload.linked_agency_id or "").strip() or None,
        "notes": (payload.notes or "").strip() or None,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.partner_profiles.insert_one(doc)
    doc["_id"] = res.inserted_id
    data = serialize_doc(doc)
    data["id"] = data.pop("_id")
    return PartnerOut(**data)


@router.patch("/{partner_id}", response_model=PartnerOut, dependencies=[AdminDep])
async def update_partner(
    partner_id: str,
    payload: PartnerUpdateIn,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
) -> PartnerOut:
    org_id = user["organization_id"]

    try:
        oid = ObjectId(partner_id)
    except Exception:
        # Support string ids as well (in case of future changes)
        oid = partner_id

    data = payload.model_dump(exclude_unset=True)
    update: Dict[str, Any] = {}

    for field in ["name", "contact_email", "status", "api_key_name", "default_markup_percent", "linked_agency_id", "notes"]:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip()
            update[field] = value

    if not update:
        doc = await db.partner_profiles.find_one({"_id": oid, "organization_id": org_id})
        if not doc:
            raise HTTPException(status_code=404, detail="PARTNER_NOT_FOUND")
        data = serialize_doc(doc)
        data["id"] = data.pop("_id")
        return PartnerOut(**data)

    update["updated_at"] = datetime.now(timezone.utc).isoformat()

    res = await db.partner_profiles.update_one({"_id": oid, "organization_id": org_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="PARTNER_NOT_FOUND")

    doc = await db.partner_profiles.find_one({"_id": oid, "organization_id": org_id})
    if not doc:
        raise HTTPException(status_code=404, detail="PARTNER_NOT_FOUND")

    data = serialize_doc(doc)
    data["id"] = data.pop("_id")
    return PartnerOut(**data)
