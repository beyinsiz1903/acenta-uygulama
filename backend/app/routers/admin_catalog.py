from __future__ import annotations

from typing import Any
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, Query, Path, Request

from app.auth import require_roles, get_current_user
from app.db import get_db
from app.errors import AppError
from app.schemas.catalog import (
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductResponse,
    ProductListResponse,
    ProductListItem,
    ProductVersionCreateRequest,
    ProductVersionListResponse,
    ProductVersionResponse,
    PublishResponse,
    RoomTypeCreateRequest,
    RoomTypeResponse,
    RatePlanCreateRequest,
    RatePlanResponse,
    CancellationPolicyCreateRequest,
    CancellationPolicyResponse,
)
from pymongo.errors import DuplicateKeyError
from app.services import catalog as svc


router = APIRouter(prefix="/api/admin/catalog", tags=["admin_catalog"])


def _id(x: Any) -> str:
    return str(x) if isinstance(x, ObjectId) else str(x)


@router.post("/products", response_model=ProductResponse)
async def create_product(
    payload: ProductCreateRequest,
    request: Request,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    actor = {
        "organization_id": user["organization_id"],
        "email": user.get("email"),
        "roles": user.get("roles") or [],
        "request": request,
    }
    doc = await svc.create_product(db, actor, payload.model_dump())
    return {
        "product_id": _id(doc["_id"]),
        "organization_id": doc["organization_id"],
        "type": doc["type"],
        "code": doc["code"],
        "name": doc["name"],
        "status": doc["status"],
        "default_currency": doc["default_currency"],
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    q: str | None = Query(default=None),
    type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
):
    items, published_map, next_cursor = await svc.list_products(
        db,
        user["organization_id"],
        q=q,
        type_=type,
        status=status,
        limit=limit,
        cursor=cursor,
    )
    out: list[ProductListItem] = []
    for it in items:
        pid = _id(it["_id"])
        out.append(
            ProductListItem(
                product_id=pid,
                type=it.get("type") or "hotel",
                code=it.get("code") or "",
                status=it.get("status") or "inactive",
                name_tr=(it.get("name") or {}).get("tr"),
                name_en=(it.get("name") or {}).get("en"),
                created_at=it.get("created_at"),
                updated_at=it.get("updated_at") or it.get("created_at"),
                published_version=published_map.get(pid),
            )
        )
    return ProductListResponse(items=out, next_cursor=next_cursor)


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str = Path(...),
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
):
    try:
        pid = ObjectId(product_id)
    except Exception:
        raise AppError(404, "not_found", "Product not found", {"product_id": product_id})
    doc = await db.products.find_one({"_id": pid, "organization_id": user["organization_id"]})
    if not doc:
        raise AppError(404, "not_found", "Product not found", {"product_id": product_id})
    return ProductResponse(
        product_id=_id(doc["_id"]),
        organization_id=doc["organization_id"],
        type=doc.get("type") or "hotel",
        code=doc.get("code") or "",
        name=doc.get("name") or {},
        status=doc.get("status") or "inactive",
        default_currency=doc.get("default_currency") or "EUR",
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at") or doc.get("created_at"),
    )


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    payload: ProductUpdateRequest,
    request: Request,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    actor = {
        "organization_id": user["organization_id"],
        "email": user.get("email"),
        "roles": user.get("roles") or [],
        "request": request,
    }
    doc = await svc.update_product(db, actor, product_id, payload.model_dump(exclude_unset=True))
    return ProductResponse(
        product_id=_id(doc["_id"]),
        organization_id=doc["organization_id"],
        type=doc["type"],
        code=doc["code"],
        name=doc["name"],
        status=doc["status"],
        default_currency=doc["default_currency"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get("/products/{product_id}/versions", response_model=ProductVersionListResponse)
async def list_versions(
    product_id: str,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
):
    items = await svc.list_product_versions(db, user["organization_id"], product_id)
    out: list[ProductVersionResponse] = []
    for it in items:
        out.append(
            ProductVersionResponse(
                version_id=_id(it["_id"]),
                product_id=_id(it["product_id"]),
                version=it["version"],
                status=it["status"],
                valid_from=it.get("valid_from"),
                valid_to=it.get("valid_to"),
                content=it.get("content") or {},
                created_at=it["created_at"],
                updated_at=it["updated_at"],
                published_at=it.get("published_at"),
                published_by_email=it.get("published_by_email"),
            )
        )
    return ProductVersionListResponse(items=out)


@router.post("/products/{product_id}/versions", response_model=ProductVersionResponse)
async def create_version(
    product_id: str,
    payload: ProductVersionCreateRequest,
    request: Request,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    actor = {
        "organization_id": user["organization_id"],
        "email": user.get("email"),
        "roles": user.get("roles") or [],
        "request": request,
    }
    doc = await svc.create_product_version(db, actor, product_id, payload.model_dump())
    return ProductVersionResponse(
        version_id=_id(doc["_id"]),
        product_id=_id(doc["product_id"]),
        version=doc["version"],
        status=doc["status"],
        valid_from=doc.get("valid_from"),
        valid_to=doc.get("valid_to"),
        content=doc.get("content") or {},
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        published_at=doc.get("published_at"),
        published_by_email=doc.get("published_by_email"),
    )


@router.post("/products/{product_id}/versions/{version_id}/publish", response_model=PublishResponse)
async def publish_version(
    product_id: str,
    version_id: str,
    request: Request,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    actor = {
        "organization_id": user["organization_id"],
        "email": user.get("email"),
        "roles": user.get("roles") or [],
        "request": request,
    }
    doc = await svc.publish_product_version(db, actor, product_id, version_id)
    return PublishResponse(
        product_id=product_id,
        published_version=doc["version"],
        version_id=_id(doc["_id"]),
        status="published",
    )


@router.post("/room-types", response_model=RoomTypeResponse)
async def create_room_type(
    payload: RoomTypeCreateRequest,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    try:
        pid = ObjectId(payload.product_id)
    except Exception:
        raise AppError(404, "not_found", "Product not found", {"product_id": payload.product_id})

    prod = await db.products.find_one({"_id": pid, "organization_id": user["organization_id"]})
    if not prod:
        raise AppError(404, "not_found", "Product not found", {"product_id": payload.product_id})

    now = datetime.utcnow()
    doc = {
        "organization_id": user["organization_id"],
        "product_id": pid,
        "code": (payload.code or "").strip().upper(),
        "name": payload.name.model_dump(),
        "max_occupancy": payload.max_occupancy,
        "attributes": payload.attributes,
        "created_at": now,
        "updated_at": now,
    }
    try:
        res = await db.room_types.insert_one(doc)
    except Exception:
        raise AppError(409, "duplicate_code", "Room type code exists", {"code": payload.code})

    return RoomTypeResponse(
        room_type_id=_id(res.inserted_id),
        product_id=payload.product_id,
        code=doc["code"],
        name=doc["name"],
        max_occupancy=doc["max_occupancy"],
        attributes=doc["attributes"],
    )


@router.get("/room-types", response_model=list[RoomTypeResponse])
async def list_room_types(
    product_id: str = Query(...),
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
):
    try:
        pid = ObjectId(product_id)
    except Exception:
        raise AppError(404, "not_found", "Product not found", {"product_id": product_id})

    cur = db.room_types.find({"organization_id": user["organization_id"], "product_id": pid}).sort("code", 1)
    items = await cur.to_list(length=500)
    return [
        RoomTypeResponse(
            room_type_id=_id(x["_id"]),
            product_id=_id(x["product_id"]),
            code=x["code"],
            name=x.get("name") or {},
            max_occupancy=x.get("max_occupancy", 1),
            attributes=x.get("attributes") or {},
        )
        for x in items
    ]


@router.post("/cancellation-policies", response_model=CancellationPolicyResponse)
async def create_cancel_policy(
    payload: CancellationPolicyCreateRequest,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    now = datetime.utcnow()
    doc = {
        "organization_id": user["organization_id"],
        "code": (payload.code or "").strip().upper(),
        "name": payload.name,
        "rules": [r.model_dump() for r in payload.rules],
        "created_at": now,
        "updated_at": now,
    }
    try:
        res = await db.cancellation_policies.insert_one(doc)
    except DuplicateKeyError:
        raise AppError(409, "duplicate_code", "Code already exists", {"code": doc["code"]})

    return CancellationPolicyResponse(
        policy_id=_id(res.inserted_id),
        code=doc["code"],
        name=doc["name"],
        rules=doc["rules"],
    )


@router.get("/cancellation-policies", response_model=list[CancellationPolicyResponse])
async def list_cancel_policies(
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
):
    cur = db.cancellation_policies.find({"organization_id": user["organization_id"]}).sort("code", 1)
    items = await cur.to_list(length=500)
    return [
        CancellationPolicyResponse(
            cancellation_policy_id=_id(x["_id"]),
            code=x["code"],
            name=x["name"],
            rules=x.get("rules") or [],
        )
        for x in items
    ]


@router.post("/rate-plans", response_model=RatePlanResponse)
async def create_rate_plan(
    payload: RatePlanCreateRequest,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin"])),
):
    try:
        pid = ObjectId(payload.product_id)
    except Exception:
        raise AppError(404, "not_found", "Product not found", {"product_id": payload.product_id})

    prod = await db.products.find_one({"_id": pid, "organization_id": user["organization_id"]})
    if not prod:
        raise AppError(404, "not_found", "Product not found", {"product_id": payload.product_id})

    cpid = None
    if payload.cancellation_policy_id:
        try:
            cpid = ObjectId(payload.cancellation_policy_id)
        except Exception:
            raise AppError(409, "invalid_reference", "Cancellation policy not found", {"policy_id": payload.cancellation_policy_id})
        ok = await db.cancellation_policies.find_one({"_id": cpid, "organization_id": user["organization_id"]})
        if not ok:
            raise AppError(409, "invalid_reference", "Cancellation policy not found", {"policy_id": payload.cancellation_policy_id})

    now = datetime.utcnow()
    doc = {
        "organization_id": user["organization_id"],
        "product_id": pid,
        "code": (payload.code or "").strip().upper(),
        "name": payload.name.model_dump(),
        "board": payload.board,
        "cancellation_policy_id": cpid,
        "payment_type": payload.payment_type,
        "min_stay": payload.min_stay,
        "max_stay": payload.max_stay,
        "created_at": now,
        "updated_at": now,
    }
    try:
        res = await db.rate_plans.insert_one(doc)
    except Exception:
        raise AppError(409, "duplicate_code", "Rate plan code exists", {"code": payload.code})

    return RatePlanResponse(
        rate_plan_id=_id(res.inserted_id),
        product_id=payload.product_id,
        code=doc["code"],
        name=doc["name"],
        board=doc["board"],
        cancellation_policy_id=_id(cpid) if cpid else None,
        payment_type=doc["payment_type"],
        min_stay=doc["min_stay"],
        max_stay=doc["max_stay"],
    )


@router.get("/rate-plans", response_model=list[RatePlanResponse])
async def list_rate_plans(
    product_id: str = Query(...),
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
):
    try:
        pid = ObjectId(product_id)
    except Exception:
        raise AppError(404, "not_found", "Product not found", {"product_id": product_id})

    cur = db.rate_plans.find({"organization_id": user["organization_id"], "product_id": pid}).sort("code", 1)
    items = await cur.to_list(length=500)
    return [
        RatePlanResponse(
            rate_plan_id=_id(x["_id"]),
            product_id=_id(x["product_id"]),
            code=x["code"],
            name=x.get("name") or {},
            board=x.get("board") or "RO",
            cancellation_policy_id=_id(x["cancellation_policy_id"]) if x.get("cancellation_policy_id") else None,
            payment_type=x.get("payment_type") or "postpay",
            min_stay=x.get("min_stay", 1),
            max_stay=x.get("max_stay", 30),
        )
        for x in items
    ]
