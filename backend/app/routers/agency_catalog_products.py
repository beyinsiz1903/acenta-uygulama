from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_roles
from app.db import get_db
from app.utils import now_utc, to_object_id

router = APIRouter(prefix="/api/agency/catalog/products", tags=["agency:catalog:products"])


def _sid(x: Any) -> str:
    return str(x)


def _oid_or_404(id_str: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=404, detail={"code": "CATALOG_PRODUCT_NOT_FOUND", "message": "Ürün bulunamadı."})


@router.get("")
async def list_catalog_products(
    type: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    active: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """List catalog products for current agency.

    Filters:
    - type: tour|hotel|transfer|car|activity
    - q: simple case-insensitive search on title/description
    - active: bool
    """

    org_id = _sid(user.get("organization_id"))
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail={"code": "USER_NOT_IN_AGENCY", "message": "Kullanıcı bir acentaya bağlı değil."})

    query: Dict[str, Any] = {
        "organization_id": org_id,
        "agency_id": agency_id,
    }
    if type:
        query["type"] = type
    if active is not None:
        query["active"] = active

    if q:
        rx = {"$regex": q, "$options": "i"}
        query["$or"] = [{"title": rx}, {"description": rx}]

    cursor = (
        db.agency_catalog_products
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    items: List[Dict[str, Any]] = []
    async for doc in cursor:
        d = dict(doc)
        d["id"] = _sid(d.pop("_id"))
        # remove internal ids if present
        d.pop("organization_id", None)
        d.pop("agency_id", None)
        items.append(d)

    return {"items": items}


@router.post("/")
async def create_catalog_product(
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin"])),
):
    org_id = _sid(user.get("organization_id"))
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail={"code": "USER_NOT_IN_AGENCY", "message": "Kullanıcı bir acentaya bağlı değil."})

    p_type = (body.get("type") or "").strip()
    if p_type not in {"tour", "hotel", "transfer", "car", "activity"}:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PRODUCT_TYPE", "message": "Geçersiz ürün tipi."})

    title = (body.get("title") or "").strip()
    if len(title) < 2:
        raise HTTPException(status_code=400, detail={"code": "INVALID_TITLE", "message": "Lütfen ürün için başlık girin."})

    now = now_utc()

    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "agency_id": agency_id,
        "type": p_type,
        "title": title,
        "description": (body.get("description") or "").strip(),
        "location": body.get("location") or {},
        "base_currency": (body.get("base_currency") or "TRY").upper(),
        "images": body.get("images") or [],
        "active": bool(body.get("active", True)),
        "created_at": now,
        "updated_at": now,
    }

    res = await db.agency_catalog_products.insert_one(doc)
    saved = await db.agency_catalog_products.find_one({"_id": res.inserted_id})
    assert saved is not None
    out = dict(saved)
    out["id"] = _sid(out.pop("_id"))
    out.pop("organization_id", None)
    out.pop("agency_id", None)
    return out


@router.put("/{product_id}")
async def update_catalog_product(
    product_id: str,
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin"])),
):
    org_id = _sid(user.get("organization_id"))
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail={"code": "USER_NOT_IN_AGENCY", "message": "Kullanıcı bir acentaya bağlı değil."})

    product_oid = _oid_or_404(product_id)

    existing = await db.agency_catalog_products.find_one(
        {"_id": product_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail={"code": "CATALOG_PRODUCT_NOT_FOUND", "message": "Ürün bulunamadı."})

    update: Dict[str, Any] = {}

    if "title" in body:
        title = (body.get("title") or "").strip()
        if len(title) < 2:
            raise HTTPException(status_code=400, detail={"code": "INVALID_TITLE", "message": "Lütfen ürün için başlık girin."})
        update["title"] = title

    if "description" in body:
        update["description"] = (body.get("description") or "").strip()

    if "location" in body:
        update["location"] = body.get("location") or {}

    if "base_currency" in body:
        update["base_currency"] = (body.get("base_currency") or "TRY").upper()

    if "images" in body:
        update["images"] = body.get("images") or []

    if "type" in body:
        p_type = (body.get("type") or "").strip()
        if p_type not in {"tour", "hotel", "transfer", "car", "activity"}:
            raise HTTPException(status_code=400, detail={"code": "INVALID_PRODUCT_TYPE", "message": "Geçersiz ürün tipi."})
        update["type"] = p_type

    if not update:
        existing_out = dict(existing)
        existing_out["id"] = _sid(existing_out.pop("_id"))
        existing_out.pop("organization_id", None)
        existing_out.pop("agency_id", None)
        return existing_out

    update["updated_at"] = now_utc()

    await db.agency_catalog_products.update_one(
        {"_id": product_oid, "organization_id": org_id, "agency_id": agency_id},
        {"$set": update},
    )

    doc = await db.agency_catalog_products.find_one({"_id": product_oid})
    assert doc is not None
    out = dict(doc)
    out["id"] = _sid(out.pop("_id"))
    out.pop("organization_id", None)
    out.pop("agency_id", None)
    return out


@router.post("/{product_id}/toggle-active")
async def toggle_catalog_product_active(
    product_id: str,
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin"])),
):
    org_id = _sid(user.get("organization_id"))
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail={"code": "USER_NOT_IN_AGENCY", "message": "Kullanıcı bir acentaya bağlı değil."})

    product_oid = _oid_or_404(product_id)

    existing = await db.agency_catalog_products.find_one(
        {"_id": product_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail={"code": "CATALOG_PRODUCT_NOT_FOUND", "message": "Ürün bulunamadı."})

    if "active" not in body:
        raise HTTPException(status_code=400, detail={"code": "ACTIVE_REQUIRED", "message": "active alanı zorunludur."})

    active = bool(body.get("active"))

    await db.agency_catalog_products.update_one(
        {"_id": product_oid, "organization_id": org_id, "agency_id": agency_id},
        {"$set": {"active": active, "updated_at": now_utc()}},
    )

    doc = await db.agency_catalog_products.find_one({"_id": product_oid})
    assert doc is not None
    out = dict(doc)
    out["id"] = _sid(out.pop("_id"))
    out.pop("organization_id", None)
    out.pop("agency_id", None)
    return out


@router.get("/{product_id}/variants")
async def list_product_variants(
    product_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """List variants for a catalog product."""

    org_id = _sid(user.get("organization_id"))
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail={"code": "USER_NOT_IN_AGENCY", "message": "Kullanıcı bir acentaya bağlı değil."})

    product_oid = _oid_or_404(product_id)

    # Ensure product exists and belongs to agency
    prod = await db.agency_catalog_products.find_one(
        {"_id": product_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not prod:
        raise HTTPException(status_code=404, detail={"code": "CATALOG_PRODUCT_NOT_FOUND", "message": "Ürün bulunamadı."})

    cursor = db.agency_catalog_variants.find(
        {
            "organization_id": org_id,
            "agency_id": agency_id,
            "product_id": product_oid,
        }
    ).sort("created_at", -1)

    items: List[Dict[str, Any]] = []
    async for doc in cursor:
        d = dict(doc)
        d["id"] = _sid(d.pop("_id"))
        d["product_id"] = _sid(d["product_id"])
        d.pop("organization_id", None)
        d.pop("agency_id", None)
        items.append(d)

    return {"items": items}
