from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.decimal128 import Decimal128
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.db import get_db
from app.utils import serialize_doc, now_utc

router = APIRouter(prefix="/pricing/rules", tags=["pricing_rules"])


RULE_TYPES = {"markup_pct", "markup_fixed", "commission_pct", "commission_fixed"}


class PricingRuleCreate(BaseModel):
    tenant_id: Optional[str] = None
    agency_id: Optional[str] = None
    supplier: Optional[str] = None
    rule_type: str
    value: str
    priority: int = Field(0, ge=-1000, le=1000)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    stackable: bool = True


class PricingRuleUpdate(BaseModel):
    tenant_id: Optional[str] = None
    agency_id: Optional[str] = None
    supplier: Optional[str] = None
    rule_type: Optional[str] = None
    value: Optional[str] = None
    priority: Optional[int] = Field(None, ge=-1000, le=1000)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    stackable: Optional[bool] = None


def _parse_decimal(value_str: str) -> Decimal:
    try:
        dec = Decimal(value_str)
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="INVALID_DECIMAL_VALUE")
    return dec


def _validate_value(rule_type: str, dec: Decimal) -> Decimal:
    """Validate and normalize decimal based on rule type."""

    if rule_type in {"markup_pct", "commission_pct"}:
        if dec < Decimal("0") or dec > Decimal("1000"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="INVALID_PERCENT_VALUE")
        # Allow some precision but quantize to 2 decimals for storage
        return dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif rule_type in {"markup_fixed", "commission_fixed"}:
        if dec < Decimal("0"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="INVALID_FIXED_VALUE")
        return dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="INVALID_RULE_TYPE")


def _validate_window(valid_from: Optional[datetime], valid_to: Optional[datetime]) -> None:
    if valid_from and valid_to and valid_to < valid_from:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="INVALID_VALIDITY_WINDOW")


def _enforce_tenant_scope(request: Request, body_tenant_id: Optional[str], query_tenant_id: Optional[str]) -> None:
    """Enforce cross-tenant constraints for rules.

    If a tenant context exists, any explicit tenant_id (body or query) must
    match it; otherwise 403 CROSS_TENANT_FORBIDDEN.
    """

    ctx_tenant_id = getattr(request.state, "tenant_id", None)
    if not ctx_tenant_id:
        return

    for t_id in (body_tenant_id, query_tenant_id):
        if t_id is not None and t_id != ctx_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CROSS_TENANT_FORBIDDEN",
            )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_pricing_rule(
    payload: PricingRuleCreate,
    request: Request,
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    db = await get_db()
    org_id = user["organization_id"]

    # Determine tenant_id default from context if not provided
    ctx_tenant_id = getattr(request.state, "tenant_id", None)
    body_tenant_id = payload.tenant_id

    _enforce_tenant_scope(request, body_tenant_id, None)

    tenant_id = body_tenant_id if body_tenant_id is not None else ctx_tenant_id

    rule_type = payload.rule_type
    if rule_type not in RULE_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="INVALID_RULE_TYPE")

    dec = _parse_decimal(payload.value)
    dec = _validate_value(rule_type, dec)

    _validate_window(payload.valid_from, payload.valid_to)

    now = now_utc()
    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "agency_id": payload.agency_id,
        "supplier": payload.supplier,
        "rule_type": rule_type,
        "value": Decimal128(str(dec)),
        "priority": payload.priority,
        "valid_from": payload.valid_from,
        "valid_to": payload.valid_to,
        "stackable": payload.stackable,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.pricing_rules.insert_one(doc)
    created = await db.pricing_rules.find_one({"_id": res.inserted_id})
    return serialize_doc(created)


@router.get("")
async def list_pricing_rules(
    request: Request,
    tenant_id: Optional[str] = Query(None),
    supplier: Optional[str] = Query(None),
    rule_type: Optional[str] = Query(None),
    active_only: bool = Query(False),
    user=Depends(get_current_user),
) -> List[Dict[str, Any]]:
    db = await get_db()
    org_id = user["organization_id"]

    _enforce_tenant_scope(request, None, tenant_id)

    filter_: Dict[str, Any] = {"organization_id": org_id}
    if tenant_id is not None:
        filter_["tenant_id"] = tenant_id
    if supplier is not None:
        filter_["supplier"] = supplier
    if rule_type is not None:
        filter_["rule_type"] = rule_type

    now = now_utc().replace(tzinfo=None)
    if active_only:
        filter_["$and"] = [
            {"$or": [{"valid_from": None}, {"valid_from": {"$lte": now}}]},
            {"$or": [{"valid_to": None}, {"valid_to": {"$gte": now}}]},
        ]

    cursor = db.pricing_rules.find(filter_).sort([
        ("priority", -1),
        ("created_at", 1),
    ])
    docs = await cursor.to_list(length=1000)
    return [serialize_doc(d) for d in docs]


async def _get_org_scoped_rule(db, org_id: str, rule_id: str) -> Dict[str, Any]:
    try:
        oid = ObjectId(rule_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RULE_NOT_FOUND")

    doc = await db.pricing_rules.find_one({"_id": oid, "organization_id": org_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RULE_NOT_FOUND")
    return doc


@router.get("/{rule_id}")
async def get_pricing_rule(rule_id: str, user=Depends(get_current_user)) -> Dict[str, Any]:
    db = await get_db()
    org_id = user["organization_id"]
    doc = await _get_org_scoped_rule(db, org_id, rule_id)
    return serialize_doc(doc)


@router.patch("/{rule_id}")
async def update_pricing_rule(
    rule_id: str,
    payload: PricingRuleUpdate,
    request: Request,
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    db = await get_db()
    org_id = user["organization_id"]

    existing = await _get_org_scoped_rule(db, org_id, rule_id)

    body_tenant_id = payload.tenant_id
    _enforce_tenant_scope(request, body_tenant_id, None)

    update_fields: Dict[str, Any] = {}

    rule_type = payload.rule_type or existing.get("rule_type")
    if rule_type not in RULE_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="INVALID_RULE_TYPE")

    value_str = payload.value if payload.value is not None else str(existing.get("value"))
    dec = _parse_decimal(value_str)
    dec = _validate_value(rule_type, dec)

    valid_from = payload.valid_from if payload.valid_from is not None else existing.get("valid_from")
    valid_to = payload.valid_to if payload.valid_to is not None else existing.get("valid_to")
    _validate_window(valid_from, valid_to)

    if payload.tenant_id is not None:
        update_fields["tenant_id"] = payload.tenant_id
    if payload.agency_id is not None:
        update_fields["agency_id"] = payload.agency_id
    if payload.supplier is not None:
        update_fields["supplier"] = payload.supplier

    update_fields["rule_type"] = rule_type
    update_fields["value"] = Decimal128(str(dec))

    if payload.priority is not None:
        update_fields["priority"] = payload.priority
    if payload.valid_from is not None or payload.valid_to is not None:
        update_fields["valid_from"] = valid_from
        update_fields["valid_to"] = valid_to
    if payload.stackable is not None:
        update_fields["stackable"] = payload.stackable

    update_fields["updated_at"] = now_utc()

    await db.pricing_rules.update_one({"_id": existing["_id"]}, {"$set": update_fields})
    doc = await _get_org_scoped_rule(db, org_id, rule_id)
    return serialize_doc(doc)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pricing_rule(rule_id: str, user=Depends(get_current_user)) -> None:
    db = await get_db()
    org_id = user["organization_id"]

    existing = await _get_org_scoped_rule(db, org_id, rule_id)
    await db.pricing_rules.delete_one({"_id": existing["_id"]})
    return None
