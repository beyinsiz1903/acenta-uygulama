from __future__ import annotations

from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_roles
from app.db import get_db
from app.utils import to_object_id
from app.services.catalog_availability import expand_dates, compute_used_units

router = APIRouter(prefix="/api/agency/catalog/capacity-dashboard", tags=["agency:catalog:capacity-dashboard"])


def _sid(x: Any) -> str:
    return str(x)


def _oid_or_404(id_str: str, code: str, message: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=404, detail={"code": code, "message": message})


@router.get("")
async def get_capacity_dashboard(
    variant_id: str = Query(...),
    start: str = Query(...),
    end: str = Query(...),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """Capacity dashboard for a given catalog variant over a date range."""

    org_id = _sid(user.get("organization_id"))
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "USER_NOT_IN_AGENCY", "message": "Kullanıcı bir acentaya bağlı değil."},
        )

    variant_oid = _oid_or_404(variant_id, "CATALOG_VARIANT_NOT_FOUND", "Variant bulunamadı.")

    try:
        days = expand_dates(start, end)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_DATES", "message": "Geçersiz tarih aralığı."},
        )

    # Fetch variant with product + scope
    variant = await db.agency_catalog_variants.find_one(
        {"_id": variant_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not variant:
        raise HTTPException(
            status_code=404,
            detail={"code": "CATALOG_VARIANT_NOT_FOUND", "message": "Variant bulunamadı."},
        )

    product_id_val = variant.get("product_id")
    if not product_id_val:
        raise HTTPException(
            status_code=404,
            detail={"code": "CATALOG_PRODUCT_NOT_FOUND", "message": "Ürün bulunamadı."},
        )

    product_oid = product_id_val if isinstance(product_id_val, ObjectId) else _oid_or_404(
        str(product_id_val), "CATALOG_PRODUCT_NOT_FOUND", "Ürün bulunamadı."
    )

    capacity = variant.get("capacity") or {}
    mode_raw = (capacity.get("mode") or "pax").lower()
    mode = mode_raw if mode_raw in {"pax", "bookings"} else "pax"

    max_per_day_val = capacity.get("max_per_day")
    if max_per_day_val is None:
        max_per_day: Optional[int] = None
    else:
        try:
            max_per_day = int(max_per_day_val)
        except Exception:
            max_per_day = None

    used_map = await compute_used_units(
        db,
        org_id=org_id,
        agency_id=agency_id,
        product_oid=product_oid,
        variant_oid=variant_oid,
        days=days,
        mode=mode,
    )

    day_rows = []
    full_days = 0
    overbooked_days = 0
    total_used = 0

    for d in days:
        used = int(used_map.get(d, 0))
        remaining: Optional[int]
        can_book: bool
        overbooked = False
        if max_per_day is None:
            remaining = None
            can_book = True
        else:
            remaining = max_per_day - used
            if used > max_per_day:
                overbooked = True
            can_book = remaining > 0
            if remaining <= 0:
                full_days += 1
            if overbooked:
                overbooked_days += 1
        total_used += used

        day_rows.append(
            {
                "day": d,
                "used": used,
                "max": max_per_day,
                "remaining": remaining,
                "can_book": can_book,
                "mode": mode,
                "overbooked": overbooked,
            }
        )

    total_days = len(days)
    avg_used = float(total_used) / total_days if total_days else 0.0

    return {
        "variant_id": variant_id,
        "product_id": str(product_oid),
        "range": {"start": start, "end": end},
        "mode": mode,
        "max_per_day": max_per_day,
        "days": day_rows,
        "summary": {
            "total_days": total_days,
            "full_days": full_days,
            "overbooked_days": overbooked_days,
            "avg_used": round(avg_used, 2),
        },
    }
