from __future__ import annotations

from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_roles
from app.db import get_db
from app.utils import to_object_id
from app.services.catalog_availability import expand_dates, compute_availability

router = APIRouter(prefix="/api/agency/catalog/availability", tags=["agency:catalog:availability"])


def _sid(x: Any) -> str:
    return str(x)


def _oid_or_404(id_str: str, code: str, message: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=404, detail={"code": code, "message": message})


@router.get("")
async def get_catalog_availability(
    product_id: str = Query(...),
    variant_id: str = Query(...),
    start: str = Query(...),
    end: Optional[str] = Query(default=None),
    pax: int = Query(default=1, ge=1),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """Compute availability for a catalog variant over a date range.

    Returns per-day capacity usage and whether requested pax can be booked.
    """

    org_id = _sid(user.get("organization_id"))
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "USER_NOT_IN_AGENCY", "message": "Kullanıcı bir acentaya bağlı değil."},
        )

    product_oid = _oid_or_404(product_id, "CATALOG_PRODUCT_NOT_FOUND", "Ürün bulunamadı.")
    variant_oid = _oid_or_404(variant_id, "CATALOG_VARIANT_NOT_FOUND", "Variant bulunamadı.")

    # Ensure product & variant belong to this agency
    prod = await db.agency_catalog_products.find_one(
        {"_id": product_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not prod:
        raise HTTPException(
            status_code=404,
            detail={"code": "CATALOG_PRODUCT_NOT_FOUND", "message": "Ürün bulunamadı."},
        )

    variant = await db.agency_catalog_variants.find_one(
        {"_id": variant_oid, "organization_id": org_id, "agency_id": agency_id, "product_id": product_oid}
    )
    if not variant:
        raise HTTPException(
            status_code=404,
            detail={"code": "CATALOG_VARIANT_NOT_FOUND", "message": "Variant bulunamadı."},
        )

    try:
        days = expand_dates(start, end)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_DATES", "message": "Geçersiz tarih aralığı."},
        )

    result = await compute_availability(
        db,
        org_id=org_id,
        agency_id=agency_id,
        product_oid=product_oid,
        variant=variant,
        days=days,
        pax=pax,
    )

    return {
        "product_id": product_id,
        "variant_id": variant_id,
        **result,
    }
