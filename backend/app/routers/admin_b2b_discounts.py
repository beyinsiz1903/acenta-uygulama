from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, conint, confloat, field_validator

from app.db import get_db
from app.errors import AppError
from app.auth import require_roles
from app.utils import now_utc


router = APIRouter(prefix="/api/admin/b2b/discount-groups", tags=["admin_b2b_discounts"])

AdminDep = Depends(require_roles(["admin", "super_admin"]))


class DiscountRuleIn(BaseModel):
    type: str = Field("percent", pattern="^(percent|amount)$")
    value: confloat(ge=0, le=100)  # percent 0-100; amount treated separately if added later
    applies_to: str = Field("markup_only", pattern="^markup_only$")


class DiscountScope(BaseModel):
    agency_id: Optional[str] = None
    product_id: Optional[str] = None
    product_type: Optional[str] = None


class DiscountValidity(BaseModel):
    from_: Optional[str] = Field(default=None, alias="from")
    to: Optional[str] = None

    @field_validator("from_", "to")
    @classmethod
    def _validate_iso(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Simple ISO date validation (YYYY-MM-DD)
        try:
            datetime.fromisoformat(v)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Invalid date format: {v}") from exc
        return v


class DiscountGroupCreate(BaseModel):
    name: str
    priority: conint(ge=0, le=1000) = 0
    scope: DiscountScope = Field(default_factory=DiscountScope)
    validity: Optional[DiscountValidity] = None
    rules: List[DiscountRuleIn] = Field(default_factory=list)
    notes: Optional[str] = None


class DiscountGroupUpdate(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(active|inactive)$")
    name: Optional[str] = None
    priority: Optional[conint(ge=0, le=1000)] = None
    scope: Optional[DiscountScope] = None
    validity: Optional[DiscountValidity] = None
    notes: Optional[str] = None


async def _serialize_group(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc_out = {
        "id": str(doc.get("_id")),
        "organization_id": doc.get("organization_id"),
        "status": doc.get("status"),
        "name": doc.get("name"),
        "priority": doc.get("priority"),
        "scope": doc.get("scope") or {},
        "validity": doc.get("validity") or {},
        "rules": doc.get("rules") or [],
        "notes": doc.get("notes"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "created_by_email": doc.get("created_by_email"),
    }
    return doc_out


@router.get("/")
async def list_discount_groups(user=AdminDep, db=Depends(get_db)) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "missing_org", "User missing organization_id")

    cur = db.b2b_discount_groups.find({"organization_id": org_id}).sort(
        [("priority", -1), ("updated_at", -1)]
    )
    items_raw = await cur.to_list(500)
    items = [await _serialize_group(doc) for doc in items_raw]
    return {"ok": True, "items": items, "total": len(items)}


@router.post("/")
async def create_discount_group(payload: DiscountGroupCreate, user=AdminDep, db=Depends(get_db)) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "missing_org", "User missing organization_id")

    now = now_utc()

    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "status": "active",
        "name": payload.name.strip(),
        "priority": int(payload.priority or 0),
        "scope": payload.scope.model_dump(),
        "validity": payload.validity.model_dump(by_alias=True) if payload.validity else {},
        "rules": [r.model_dump() for r in payload.rules],
        "notes": payload.notes or None,
        "created_at": now,
        "updated_at": now,
        "created_by_email": user.get("email"),
    }

    res = await db.b2b_discount_groups.insert_one(doc)
    created = await db.b2b_discount_groups.find_one({"_id": res.inserted_id})
    return {"ok": True, "item": await _serialize_group(created)}


@router.put("/{group_id}")
async def update_discount_group(group_id: str, payload: DiscountGroupUpdate, user=AdminDep, db=Depends(get_db)) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "missing_org", "User missing organization_id")

    from bson import ObjectId

    try:
        oid = ObjectId(group_id)
    except Exception:
        raise AppError(404, "not_found", "Discount group not found", {"group_id": group_id})

    existing = await db.b2b_discount_groups.find_one({"_id": oid, "organization_id": org_id})
    if not existing:
        raise AppError(404, "not_found", "Discount group not found", {"group_id": group_id})

    data = payload.model_dump(exclude_unset=True, by_alias=True)

    # Whitelist-only updates (guardrail)
    update_fields: Dict[str, Any] = {}
    for key in ["status", "name", "priority", "scope", "validity", "notes"]:
        if key in data and data[key] is not None:
            update_fields[key] = data[key]

    if not update_fields:
        return {"ok": True, "item": await _serialize_group(existing)}

    update_fields["updated_at"] = now_utc()

    await db.b2b_discount_groups.update_one(
        {"_id": oid, "organization_id": org_id},
        {"$set": update_fields},
    )

    updated = await db.b2b_discount_groups.find_one({"_id": oid})
    return {"ok": True, "item": await _serialize_group(updated)}


@router.post("/{group_id}/rules")
async def add_discount_rule(group_id: str, payload: DiscountRuleIn, user=AdminDep, db=Depends(get_db)) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "missing_org", "User missing organization_id")

    from bson import ObjectId

    try:
        oid = ObjectId(group_id)
    except Exception:
        raise AppError(404, "not_found", "Discount group not found", {"group_id": group_id})

    existing = await db.b2b_discount_groups.find_one({"_id": oid, "organization_id": org_id})
    if not existing:
        raise AppError(404, "not_found", "Discount group not found", {"group_id": group_id})

    rule_doc = payload.model_dump()

    await db.b2b_discount_groups.update_one(
        {"_id": oid, "organization_id": org_id},
        {"$push": {"rules": rule_doc}, "$set": {"updated_at": now_utc()}},
    )

    updated = await db.b2b_discount_groups.find_one({"_id": oid})
    return {"ok": True, "item": await _serialize_group(updated)}


@router.delete("/{group_id}/rules/{rule_index}")
async def delete_discount_rule(group_id: str, rule_index: int, user=AdminDep, db=Depends(get_db)) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "missing_org", "User missing organization_id")

    from bson import ObjectId

    try:
        oid = ObjectId(group_id)
    except Exception:
        raise AppError(404, "not_found", "Discount group not found", {"group_id": group_id})

    existing = await db.b2b_discount_groups.find_one({"_id": oid, "organization_id": org_id})
    if not existing:
        raise AppError(404, "not_found", "Discount group not found", {"group_id": group_id})

    rules = existing.get("rules") or []
    if rule_index < 0 or rule_index >= len(rules):
        raise AppError(400, "invalid_rule_index", "Rule index out of range", {"rule_index": rule_index})

    # Remove rule by index (no arbitrary field updates)
    rules.pop(rule_index)

    await db.b2b_discount_groups.update_one(
        {"_id": oid, "organization_id": org_id},
        {"$set": {"rules": rules, "updated_at": now_utc()}},
    )

    updated = await db.b2b_discount_groups.find_one({"_id": oid})
    return {"ok": True, "item": await _serialize_group(updated)}
