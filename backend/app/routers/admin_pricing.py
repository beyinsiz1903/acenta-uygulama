from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.schemas_pricing import (
    PricingContractCreateRequest,
    PricingContractResponse,
    PricingRateGridCreateRequest,
    PricingRateGridResponse,
    PricingRuleCreateRequest,
    PricingRuleResponse,
)
from app.utils import now_utc


router = APIRouter(prefix="/api/admin/pricing", tags=["admin_pricing"])


def _id(x: Any) -> str:
    return str(x) if isinstance(x, ObjectId) else str(x)


# ---- Contracts ----


@router.post("/contracts", response_model=PricingContractResponse)
async def create_contract(
    payload: PricingContractCreateRequest,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    org_id = user["organization_id"]
    now = now_utc()

    doc = {
        "organization_id": org_id,
        "code": (payload.code or "").strip().upper(),
        "status": payload.status,
        "supplier_id": payload.supplier_id,
        "agency_id": payload.agency_id,
        "channel_id": payload.channel_id,
        "markets": payload.markets,
        "product_ids": payload.product_ids,
        "valid_from": payload.valid_from,
        "valid_to": payload.valid_to,
        "default_markup_type": payload.default_markup_type,
        "default_markup_value": payload.default_markup_value,
        "created_at": now,
        "updated_at": now,
        "published_at": None,
        "published_by_email": None,
    }
    res = await db.pricing_contracts.insert_one(doc)
    doc["_id"] = res.inserted_id

    return PricingContractResponse(
        contract_id=_id(doc["_id"]),
        organization_id=org_id,
        code=doc["code"],
        status=doc["status"],
        supplier_id=doc.get("supplier_id"),
        agency_id=doc.get("agency_id"),
        channel_id=doc.get("channel_id"),
        markets=doc.get("markets") or [],
        product_ids=doc.get("product_ids") or [],
        valid_from=doc.get("valid_from"),
        valid_to=doc.get("valid_to"),
        default_markup_type=doc.get("default_markup_type"),
        default_markup_value=doc.get("default_markup_value"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        published_at=doc.get("published_at"),
        published_by_email=doc.get("published_by_email"),
    )


@router.get("/contracts", response_model=list[PricingContractResponse])
async def list_contracts(
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
):
    org_id = user["organization_id"]
    cur = db.pricing_contracts.find({"organization_id": org_id}).sort("created_at", -1)
    docs = await cur.to_list(500)
    out: list[PricingContractResponse] = []
    for d in docs:
        out.append(
            PricingContractResponse(
                contract_id=_id(d["_id"]),
                organization_id=org_id,
                code=d.get("code"),
                status=d.get("status", "draft"),
                supplier_id=d.get("supplier_id"),
                agency_id=d.get("agency_id"),
                channel_id=d.get("channel_id"),
                markets=d.get("markets") or [],
                product_ids=d.get("product_ids") or [],
                valid_from=d.get("valid_from"),
                valid_to=d.get("valid_to"),
                default_markup_type=d.get("default_markup_type"),
                default_markup_value=d.get("default_markup_value"),
                created_at=d.get("created_at", datetime.utcnow()),
                updated_at=d.get("updated_at", datetime.utcnow()),
                published_at=d.get("published_at"),
                published_by_email=d.get("published_by_email"),
            )
        )
    return out


# ---- Rate grids ----


@router.post("/rate-grids", response_model=PricingRateGridResponse)
async def create_rate_grid(
    payload: PricingRateGridCreateRequest,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    org_id = user["organization_id"]
    now = now_utc()

    try:
        cid = ObjectId(payload.contract_id)
    except Exception:
        raise AppError(404, "not_found", "Contract not found", {"contract_id": payload.contract_id})

    contract = await db.pricing_contracts.find_one({"_id": cid, "organization_id": org_id})
    if not contract:
        raise AppError(404, "not_found", "Contract not found", {"contract_id": payload.contract_id})

    doc = {
        "organization_id": org_id,
        "contract_id": cid,
        "product_id": payload.product_id,
        "rate_plan_id": payload.rate_plan_id,
        "room_type_id": payload.room_type_id,
        "currency": payload.currency.upper(),
        "status": payload.status,
        "rows": [r.model_dump() for r in payload.rows],
        "created_at": now,
        "updated_at": now,
    }

    res = await db.pricing_rate_grids.insert_one(doc)
    doc["_id"] = res.inserted_id

    return PricingRateGridResponse(
        grid_id=_id(doc["_id"]),
        organization_id=org_id,
        contract_id=payload.contract_id,
        product_id=payload.product_id,
        rate_plan_id=payload.rate_plan_id,
        room_type_id=payload.room_type_id,
        currency=doc["currency"],
        status=doc["status"],
        rows=payload.rows,
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get("/rate-grids", response_model=list[PricingRateGridResponse])
async def list_rate_grids(
    product_id: Optional[str] = Query(default=None),
    rate_plan_id: Optional[str] = Query(default=None),
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
):
    org_id = user["organization_id"]
    q: dict[str, Any] = {"organization_id": org_id}
    if product_id:
        q["product_id"] = product_id
    if rate_plan_id:
        q["rate_plan_id"] = rate_plan_id

    cur = db.pricing_rate_grids.find(q).sort("created_at", -1)
    docs = await cur.to_list(500)

    out: list[PricingRateGridResponse] = []
    for d in docs:
        out.append(
            PricingRateGridResponse(
                grid_id=_id(d["_id"]),
                organization_id=org_id,
                contract_id=str(d.get("contract_id")),
                product_id=d.get("product_id"),
                rate_plan_id=d.get("rate_plan_id"),
                room_type_id=d.get("room_type_id"),
                currency=d.get("currency"),
                status=d.get("status", "draft"),
                rows=d.get("rows") or [],
                created_at=d.get("created_at", datetime.utcnow()),
                updated_at=d.get("updated_at", datetime.utcnow()),
            )
        )
    return out


# ---- Rules ----


@router.post("/rules", response_model=PricingRuleResponse)
async def create_rule(
    payload: PricingRuleCreateRequest,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    org_id = user["organization_id"]
    now = now_utc()

    doc = {
        "organization_id": org_id,
        "code": (payload.code or "").strip().upper(),
        "status": payload.status,
        "priority": payload.priority,
        "scope": payload.scope.model_dump(),
        "action": payload.action.model_dump(),
        "created_at": now,
        "updated_at": now,
        "created_by_email": user.get("email"),
    }

    res = await db.pricing_rules.insert_one(doc)
    doc["_id"] = res.inserted_id

    return PricingRuleResponse(
        rule_id=_id(doc["_id"]),
        organization_id=org_id,
        code=doc["code"],
        status=doc["status"],
        priority=doc["priority"],
        scope=payload.scope,
        action=payload.action,
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        created_by_email=doc.get("created_by_email"),
    )


@router.get("/rules", response_model=list[PricingRuleResponse])
async def list_rules(
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
):
    org_id = user["organization_id"]
    cur = db.pricing_rules.find({"organization_id": org_id}).sort("priority", -1)
    docs = await cur.to_list(500)

    out: list[PricingRuleResponse] = []
    for d in docs:
        out.append(
            PricingRuleResponse(
                rule_id=_id(d["_id"]),
                organization_id=org_id,
                code=d.get("code"),
                status=d.get("status", "draft"),
                priority=d.get("priority", 0),
                scope=d.get("scope") or {},
                action=d.get("action") or {},
                created_at=d.get("created_at", datetime.utcnow()),
                updated_at=d.get("updated_at", datetime.utcnow()),
                created_by_email=d.get("created_by_email"),
            )
        )
    return out
