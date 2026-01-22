from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.schemas import HotelCreateIn, HotelForceSalesOverrideIn
from app.services.audit import write_audit_log
from app.utils import now_utc, serialize_doc


router = APIRouter(prefix="/api/admin/hotels", tags=["admin_hotels"])

AdminDep = Depends(require_roles(["super_admin"]))


@router.get("/", dependencies=[AdminDep])
async def list_hotels(active: Optional[bool] = None, user=Depends(get_current_user), db=Depends(get_db)) -> List[Dict[str, Any]]:
    org_id = user["organization_id"]
    flt: Dict[str, Any] = {"organization_id": org_id}
    if active is not None:
        flt["active"] = active

    docs = await db.hotels.find(flt).sort("created_at", -1).to_list(500)
    return [serialize_doc(d) for d in docs]


@router.post("/", dependencies=[AdminDep])
async def create_hotel(payload: HotelCreateIn, user=Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
    org_id = user["organization_id"]

    now = now_utc()
    doc: Dict[str, Any] = payload.model_dump()
    doc.update(
        {
            "organization_id": org_id,
            "created_at": now,
            "updated_at": now,
            "created_by": user.get("email"),
            "updated_by": user.get("email"),
        }
    )

    res = await db.hotels.insert_one(doc)
    saved = await db.hotels.find_one({"_id": res.inserted_id})
    if not saved:
        raise HTTPException(status_code=500, detail="HOTEL_CREATE_FAILED")

    return serialize_doc(saved)


@router.patch("/{hotel_id}/force-sales", dependencies=[AdminDep])
async def patch_hotel_force_sales(
    hotel_id: str,
    payload: HotelForceSalesOverrideIn,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Toggle force_sales_open flag on a hotel.

    When force_sales_open is True, availability computation bypasses stop-sell and
    channel allocation rules and uses base inventory.
    """

    org_id = user["organization_id"]

    existing = await db.hotels.find_one({"organization_id": org_id, "_id": hotel_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Otel bulunamadı")

    now = now_utc()

    if payload.force_sales_open:
        from datetime import timedelta

        expires_at = now + timedelta(hours=payload.ttl_hours or 6)
        update = {
            "force_sales_open": True,
            "force_sales_open_expires_at": expires_at,
            "force_sales_open_reason": (payload.reason or "").strip() or None,
            "force_sales_open_updated_by": user.get("email"),
            "force_sales_open_updated_at": now,
            "updated_at": now,
            "updated_by": user.get("email"),
        }
    else:
        update = {
            "force_sales_open": False,
            "force_sales_open_expires_at": None,
            "force_sales_open_reason": None,
            "force_sales_open_updated_by": user.get("email"),
            "force_sales_open_updated_at": now,
            "updated_at": now,
            "updated_by": user.get("email"),
        }

    await db.hotels.update_one({"organization_id": org_id, "_id": hotel_id}, {"$set": update})
    saved = await db.hotels.find_one({"organization_id": org_id, "_id": hotel_id})
    if not saved:
        raise HTTPException(status_code=404, detail="Otel bulunamadı")

    meta = {
        "force_sales_open": payload.force_sales_open,
        "ttl_hours": payload.ttl_hours if payload.force_sales_open else None,
        "expires_at": saved.get("force_sales_open_expires_at"),
        "reason": (payload.reason or "").strip() or None,
    }

    # Audit log best-effort
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
            request=request,
            action="hotel.force_sales_override",
            target_type="hotel",
            target_id=str(hotel_id),
            before=existing,
            after=saved,
            meta=meta,
        )
    except Exception:
        pass

    return serialize_doc(saved)
