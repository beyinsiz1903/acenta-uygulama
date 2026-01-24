from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query, Request

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.services.audit import write_audit_log, audit_snapshot
from app.schemas_pricing import (
    PricingContractCreateRequest,
    PricingContractResponse,
    PricingRateGridCreateRequest,
    PricingRateGridResponse,
    PricingRuleCreateRequest,
    PricingRuleResponse,
    SimplePricingRuleCreate,
    SimplePricingRuleUpdate,
    SimplePricingRuleResponse,
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
    request: Request,
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

    # Audit: pricing_rule_create
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": user.get("id") or user.get("email"),
                "email": user.get("email"),
                "roles": user.get("roles") or [],
            },
            request=request,
            action="pricing_rule_create",
            target_type="pricing_rule",
            target_id=_id(doc["_id"]),
            before=audit_snapshot("pricing_rule", None),
            after=audit_snapshot("pricing_rule", doc),
            meta={"payload": payload.model_dump()},
        )
    except Exception:
        pass

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


@router.post("/rules/simple", response_model=SimplePricingRuleResponse)
async def create_simple_rule(
    payload: SimplePricingRuleCreate,
    request: Request,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    """Create a simple markup_percent pricing rule (P1.2 MVP).

    - action.type is fixed to "markup_percent"
    - value is validated between 0 and 100 by schema
    - validity semantics: from <= check_in < to (to is exclusive)
    """
    org_id = user["organization_id"]
    now = now_utc()

    # Normalise product_type for v1 (only hotel supported if provided)
    scope = payload.scope
    if scope.product_type and scope.product_type.lower() != "hotel":
        raise AppError(
            422,
            "unsupported_product_type",
            "Only product_type='hotel' is supported in P1.2 simple rules",
            {"product_type": scope.product_type},
        )

    # Prepare validity dict for storage (date -> ISO string)
    validity = {
        "from": payload.validity.from_.isoformat(),
        "to": payload.validity.to.isoformat(),
    }

    doc = {
        "organization_id": org_id,
        "status": "active",
        "priority": payload.priority,
        "scope": payload.scope.model_dump(exclude_none=True),
        "validity": validity,
        "action": payload.action.model_dump(),
        "notes": payload.notes,
        "created_at": now,
        "updated_at": now,
        "created_by_email": user.get("email"),
    }

    res = await db.pricing_rules.insert_one(doc)
    doc["_id"] = res.inserted_id

    # Audit: pricing_rule_create (simple)
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": user.get("id") or user.get("email"),
                "email": user.get("email"),
                "roles": user.get("roles") or [],
            },
            request=request,
            action="pricing_rule_create",
            target_type="pricing_rule",
            target_id=_id(doc["_id"]),
            before=audit_snapshot("pricing_rule", None),
            after=audit_snapshot("pricing_rule", doc),
            meta={"payload": payload.model_dump(), "mode": "simple"},
        )
    except Exception:
        pass

    return SimplePricingRuleResponse(
        rule_id=_id(doc["_id"]),
        organization_id=org_id,
        status=doc["status"],
        priority=doc["priority"],
        scope=doc["scope"],
        validity=doc["validity"],
        action=doc["action"],
        notes=doc.get("notes"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        created_by_email=doc.get("created_by_email"),
    )


@router.get("/rules/simple", response_model=list[SimplePricingRuleResponse])
async def list_simple_rules(
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
):
    """List simple markup_percent pricing rules (P1.2 MVP)."""
    org_id = user["organization_id"]
    
    # Find rules with action.type = "markup_percent" and validity field
    cur = db.pricing_rules.find({
        "organization_id": org_id,
        "action.type": "markup_percent",
        "validity": {"$exists": True}
    }).sort("priority", -1)
    
    docs = await cur.to_list(500)
    
    out: list[SimplePricingRuleResponse] = []
    for d in docs:
        out.append(
            SimplePricingRuleResponse(
                rule_id=_id(d["_id"]),
                organization_id=org_id,
                status=d.get("status", "active"),
                priority=d.get("priority", 100),
                scope=d.get("scope") or {},
                validity=d.get("validity") or {},
                action=d.get("action") or {},
                notes=d.get("notes"),
                created_at=d.get("created_at", datetime.utcnow()),
                updated_at=d.get("updated_at", datetime.utcnow()),
                created_by_email=d.get("created_by_email"),
            )
        )
    return out


@router.put("/rules/{rule_id}", response_model=SimplePricingRuleResponse)
async def update_simple_rule(
    rule_id: str,
    payload: SimplePricingRuleUpdate,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    """Update simple pricing rule fields (P1.2 MVP).

    Patch semantics: only provided fields are updated.
    """
    org_id = user["organization_id"]

    try:
        rid = ObjectId(rule_id)
    except Exception:
        raise AppError(404, "not_found", "Rule not found", {"rule_id": rule_id})

    existing = await db.pricing_rules.find_one({"_id": rid, "organization_id": org_id})
    if not existing:
        raise AppError(404, "not_found", "Rule not found", {"rule_id": rule_id})

    update: dict[str, Any] = {}

    if payload.priority is not None:
        update["priority"] = payload.priority

    if payload.scope is not None:
        scope = payload.scope
        if scope.product_type and scope.product_type.lower() != "hotel":
            raise AppError(
                422,
                "unsupported_product_type",
                "Only product_type='hotel' is supported in P1.2 simple rules",
                {"product_type": scope.product_type},
            )
        update["scope"] = scope.model_dump(exclude_none=True)

    if payload.validity is not None:
        update["validity"] = {
            "from": payload.validity.from_.isoformat(),
            "to": payload.validity.to.isoformat(),
        }

    if payload.action is not None:
        # Only markup_percent is allowed; schema already enforces this
        update["action"] = payload.action.model_dump()

    if payload.status is not None:
        if payload.status not in {"active", "inactive"}:
            raise AppError(422, "invalid_status", "Status must be 'active' or 'inactive'", {"status": payload.status})
        update["status"] = payload.status

    if payload.notes is not None:
        update["notes"] = payload.notes

    if not update:
        # Nothing to update; return current state
        existing["_id"] = rid
        return SimplePricingRuleResponse(
            rule_id=_id(existing["_id"]),
            organization_id=org_id,
            status=existing.get("status", "active"),
            priority=existing.get("priority", 0),
            scope=existing.get("scope") or {},
            validity=existing.get("validity") or {},
            action=existing.get("action") or {},
            notes=existing.get("notes"),
            created_at=existing.get("created_at", now_utc()),
            updated_at=existing.get("updated_at", now_utc()),
            created_by_email=existing.get("created_by_email"),
        )

    update["updated_at"] = now_utc()

    await db.pricing_rules.update_one({"_id": rid, "organization_id": org_id}, {"$set": update})
    doc = await db.pricing_rules.find_one({"_id": rid, "organization_id": org_id})

    return SimplePricingRuleResponse(
        rule_id=_id(doc["_id"]),
        organization_id=org_id,
        status=doc.get("status", "active"),
        priority=doc.get("priority", 0),
        scope=doc.get("scope") or {},
        validity=doc.get("validity") or {},
        action=doc.get("action") or {},
        notes=doc.get("notes"),
        created_at=doc.get("created_at", now_utc()),
        updated_at=doc.get("updated_at", now_utc()),
        created_by_email=doc.get("created_by_email"),
    )
