from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import require_roles
from app.db import get_db
from app.utils import now_utc, serialize_doc


router = APIRouter(prefix="/api/admin/coupons", tags=["admin_coupons"])


class CouponBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    discount_type: str = Field("PERCENT", regex="^(PERCENT|AMOUNT)$")
    value: float = Field(..., gt=0)
    scope: str = Field("B2B", regex="^(B2B|B2C|BOTH)$")
    min_total: float = Field(0, ge=0)
    usage_limit: Optional[int] = Field(None, ge=1)
    per_customer_limit: Optional[int] = Field(None, ge=1)
    valid_from: datetime
    valid_to: datetime
    active: bool = True


class CouponCreateIn(CouponBase):
    pass


class CouponUpdateIn(BaseModel):
    discount_type: Optional[str] = Field(None, regex="^(PERCENT|AMOUNT)$")
    value: Optional[float] = Field(None, gt=0)
    scope: Optional[str] = Field(None, regex="^(B2B|B2C|BOTH)$")
    min_total: Optional[float] = Field(None, ge=0)
    usage_limit: Optional[int] = Field(None, ge=1)
    per_customer_limit: Optional[int] = Field(None, ge=1)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    active: Optional[bool] = None


class CouponOut(BaseModel):
    id: str
    code: str
    discount_type: str
    value: float
    scope: str
    min_total: float
    usage_limit: Optional[int]
    usage_count: int
    per_customer_limit: Optional[int]
    valid_from: datetime
    valid_to: datetime
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


def _oid_or_404(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=404, detail="COUPON_NOT_FOUND")


@router.get("", response_model=list[CouponOut])
async def list_coupons(
    active: Optional[bool] = Query(default=None),
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    org_id = user["organization_id"]
    query: dict[str, Any] = {"organization_id": org_id}
    if active is not None:
        query["active"] = active

    cur = db.coupons.find(query).sort("created_at", -1)
    docs = await cur.to_list(500)
    # serialize_doc will convert _id -> id and datetime -> iso
    return [CouponOut(**serialize_doc(d)) for d in docs]


@router.post("", response_model=CouponOut)
async def create_coupon(
    payload: CouponCreateIn,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    org_id = user["organization_id"]
    now = now_utc()

    if payload.valid_to <= payload.valid_from:
        raise HTTPException(status_code=400, detail="valid_to must be after valid_from")

    code = payload.code.strip().upper()

    doc: dict[str, Any] = {
        "organization_id": org_id,
        "code": code,
        "discount_type": payload.discount_type,
        "value": float(payload.value),
        "scope": payload.scope,
        "min_total": float(payload.min_total or 0),
        "usage_limit": payload.usage_limit,
        "usage_count": 0,
        "per_customer_limit": payload.per_customer_limit,
        "valid_from": payload.valid_from,
        "valid_to": payload.valid_to,
        "active": payload.active,
        "created_at": now,
        "updated_at": now,
        # Usage per customer map will be incremented lazily when bookings are created
        "usage_per_customer": {},
    }

    try:
        res = await db.coupons.insert_one(doc)
        doc["_id"] = res.inserted_id
    except Exception as exc:  # pragma: no cover - defensive, relies on unique index
        # Most likely duplicate code per organization
        raise HTTPException(status_code=409, detail="COUPON_CODE_ALREADY_EXISTS") from exc

    return CouponOut(**serialize_doc(doc))


@router.patch("/{coupon_id}", response_model=CouponOut)
async def update_coupon(
    coupon_id: str,
    payload: CouponUpdateIn,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    org_id = user["organization_id"]
    oid = _oid_or_404(coupon_id)

    update: dict[str, Any] = {}

    data = payload.model_dump(exclude_unset=True)
    if data.get("valid_from") and data.get("valid_to") and data["valid_to"] <= data["valid_from"]:
        raise HTTPException(status_code=400, detail="valid_to must be after valid_from")

    for field in [
        "discount_type",
        "value",
        "scope",
        "min_total",
        "usage_limit",
        "per_customer_limit",
        "valid_from",
        "valid_to",
        "active",
    ]:
        if field in data:
            update[field] = data[field]

    if not update:
        doc = await db.coupons.find_one({"_id": oid, "organization_id": org_id})
        if not doc:
            raise HTTPException(status_code=404, detail="COUPON_NOT_FOUND")
        return CouponOut(**serialize_doc(doc))

    update["updated_at"] = now_utc()

    res = await db.coupons.update_one({"_id": oid, "organization_id": org_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="COUPON_NOT_FOUND")

    doc = await db.coupons.find_one({"_id": oid, "organization_id": org_id})
    if not doc:
        raise HTTPException(status_code=404, detail="COUPON_NOT_FOUND")

    return CouponOut(**serialize_doc(doc))
