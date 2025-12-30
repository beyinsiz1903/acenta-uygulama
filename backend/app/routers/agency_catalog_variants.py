from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_roles
from app.db import get_db
from app.utils import now_utc, to_object_id

router = APIRouter(prefix="/api/agency/catalog/variants", tags=["agency:catalog:variants"])


def _sid(x: Any) -> str:
    return str(x)


def _oid_or_404(id_str: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=404, detail={"code": "CATALOG_VARIANT_NOT_FOUND", "message": "Variant bulunamadı."})


@router.post("")
async def create_catalog_variant(
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin"])),
):
    org_id = _sid(user.get("organization_id"))
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail={"code": "USER_NOT_IN_AGENCY", "message": "Kullanıcı bir acentaya bağlı değil."})

    product_id = (body.get("product_id") or "").strip()
    if not product_id:
        raise HTTPException(status_code=400, detail={"code": "PRODUCT_ID_REQUIRED", "message": "product_id zorunludur."})

    try:
        product_oid = to_object_id(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PRODUCT_ID", "message": "Geçersiz ürün ID."})

    # Ensure product exists and belongs to agency
    prod = await db.agency_catalog_products.find_one(
        {"_id": product_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not prod:
        raise HTTPException(status_code=404, detail={"code": "CATALOG_PRODUCT_NOT_FOUND", "message": "Ürün bulunamadı."})

    name = (body.get("name") or "").strip()
    if len(name) < 1:
        raise HTTPException(status_code=400, detail={"code": "INVALID_NAME", "message": "Lütfen variant için isim girin."})

    try:
        price = float(body.get("price", 0.0) or 0.0)
    except Exception:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PRICE", "message": "Geçersiz fiyat."})

    currency = (body.get("currency") or "TRY").upper()
    rules = body.get("rules") or {}
    min_pax = int(rules.get("min_pax", 1) or 1)
    max_pax = int(rules.get("max_pax", 99) or 99)
    if min_pax < 1:
        min_pax = 1
    if max_pax < min_pax:
        max_pax = min_pax

    now = now_utc()
    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "agency_id": agency_id,
        "product_id": product_oid,
        "name": name,
        "price": price,
        "currency": currency,
        "rules": {"min_pax": min_pax, "max_pax": max_pax},
        "active": bool(body.get("active", True)),
        "created_at": now,
        "updated_at": now,
    }

    res = await db.agency_catalog_variants.insert_one(doc)
    saved = await db.agency_catalog_variants.find_one({"_id": res.inserted_id})
    assert saved is not None
    out = dict(saved)
    out["id"] = _sid(out.pop("_id"))
    out["product_id"] = _sid(out["product_id"])
    out.pop("organization_id", None)
    out.pop("agency_id", None)
    return out


@router.put("/{variant_id}")
async def update_catalog_variant(
    variant_id: str,
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin"])),
):
    org_id = _sid(user.get("organization_id"))
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail={"code": "USER_NOT_IN_AGENCY", "message": "Kullanıcı bir acentaya bağlı değil."})

    variant_oid = _oid_or_404(variant_id)

    existing = await db.agency_catalog_variants.find_one(
        {"_id": variant_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail={"code": "CATALOG_VARIANT_NOT_FOUND", "message": "Variant bulunamadı."})

    update: Dict[str, Any] = {}

    if "name" in body:
        name = (body.get("name") or "").strip()
        if len(name) < 1:
            raise HTTPException(status_code=400, detail={"code": "INVALID_NAME", "message": "Lütfen variant için isim girin."})
        update["name"] = name

    if "price" in body:
        try:
            price = float(body.get("price") or 0.0)
        except Exception:
            raise HTTPException(status_code=400, detail={"code": "INVALID_PRICE", "message": "Geçersiz fiyat."})
        update["price"] = price

    if "currency" in body:
        update["currency"] = (body.get("currency") or "TRY").upper()

    if "rules" in body:
        rules = body.get("rules") or {}
        min_pax = int(rules.get("min_pax", 1) or 1)
        max_pax = int(rules.get("max_pax", 99) or 99)
        if min_pax < 1:
            min_pax = 1
        if max_pax < min_pax:
            max_pax = min_pax
        update["rules"] = {"min_pax": min_pax, "max_pax": max_pax}

    if "capacity" in body:
        cap = body.get("capacity") or {}
        mode = (cap.get("mode") or "pax").lower()
        if mode not in {"pax", "bookings"}:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_CAPACITY", "message": "Geçersiz capacity.mode (pax/bookings olmalı)."},
            )
        max_per_day = cap.get("max_per_day")
        if max_per_day is not None:
            try:
                max_per_day_int = int(max_per_day)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "INVALID_CAPACITY", "message": "capacity.max_per_day sayısal olmalı."},
                )
            if max_per_day_int < 1:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "INVALID_CAPACITY", "message": "capacity.max_per_day en az 1 olmalı."},
                )
            max_per_day = max_per_day_int
        overbook = bool(cap.get("overbook", False))
        update["capacity"] = {"mode": mode, "max_per_day": max_per_day, "overbook": overbook}

    if not update:
        out = dict(existing)
        out["id"] = _sid(out.pop("_id"))
        out["product_id"] = _sid(out["product_id"])
        out.pop("organization_id", None)
        out.pop("agency_id", None)
        return out

    update["updated_at"] = now_utc()

    await db.agency_catalog_variants.update_one(
        {"_id": variant_oid, "organization_id": org_id, "agency_id": agency_id},
        {"$set": update},
    )

    doc = await db.agency_catalog_variants.find_one({"_id": variant_oid})
    assert doc is not None
    out = dict(doc)
    out["id"] = _sid(out.pop("_id"))
    out["product_id"] = _sid(out["product_id"])
    out.pop("organization_id", None)
    out.pop("agency_id", None)
    return out


@router.post("/{variant_id}/toggle-active")
async def toggle_catalog_variant_active(
    variant_id: str,
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin"])),
):
    org_id = _sid(user.get("organization_id"))
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail={"code": "USER_NOT_IN_AGENCY", "message": "Kullanıcı bir acentaya bağlı değil."})

    variant_oid = _oid_or_404(variant_id)

    existing = await db.agency_catalog_variants.find_one(
        {"_id": variant_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail={"code": "CATALOG_VARIANT_NOT_FOUND", "message": "Variant bulunamadı."})

    if "active" not in body:
        raise HTTPException(status_code=400, detail={"code": "ACTIVE_REQUIRED", "message": "active alanı zorunludur."})

    active = bool(body.get("active"))

    await db.agency_catalog_variants.update_one(
        {"_id": variant_oid, "organization_id": org_id, "agency_id": agency_id},
        {"$set": {"active": active, "updated_at": now_utc()}},
    )

    doc = await db.agency_catalog_variants.find_one({"_id": variant_oid})
    assert doc is not None
    out = dict(doc)
    out["id"] = _sid(out.pop("_id"))
    out["product_id"] = _sid(out["product_id"])
    out.pop("organization_id", None)
    out.pop("agency_id", None)
    return out
