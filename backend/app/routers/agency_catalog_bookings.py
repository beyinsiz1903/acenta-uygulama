from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_roles
from app.db import get_db
from app.utils import now_utc, to_object_id
from app.utils.voucher_signing import sign_voucher


router = APIRouter(prefix="/api/agency/catalog/bookings", tags=["agency:catalog:bookings"])


def _sid(x: Any) -> str:
    return str(x)

async def _get_catalog_booking_or_404(db, booking_oid, org_id, agency_id):
    doc = await db.agency_catalog_booking_requests.find_one(
        {"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"code": "CATALOG_BOOKING_NOT_FOUND", "message": "Rezervasyon bulunamadı."},
        )
    return doc


def _build_offer_snapshot(booking: Dict[str, Any], note: str = "", expires_at=None) -> Dict[str, Any]:
    pricing = booking.get("pricing") or {}
    subtotal = float(pricing.get("subtotal") or 0.0)
    commission_amount = float(pricing.get("commission_amount") or 0.0)
    total = float(pricing.get("total") or (subtotal + commission_amount))
    currency = pricing.get("currency") or "TRY"
    return {
        "status": "draft",
        "expires_at": expires_at,
        "net_price": subtotal,
        "commission_amount": commission_amount,
        "gross_price": total,
        "currency": currency,
        "note": note or "",
    }



def _oid_or_404(id_str: str, code: str = "CATALOG_BOOKING_NOT_FOUND", message: str = "Rezervasyon bulunamadı.") -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=404, detail={"code": code, "message": message})


def _ensure_agency(user: Dict[str, Any]) -> tuple[str, str]:
    org_id = _sid(user.get("organization_id"))
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "USER_NOT_IN_AGENCY", "message": "Kullanıcı bir acentaya bağlı değil."},
        )
    return org_id, agency_id


@router.get("")
async def list_catalog_bookings(
    status: Optional[str] = Query(default=None),
    type: Optional[str] = Query(default=None, alias="product_type"),
    date_from: Optional[str] = Query(default=None),  # YYYY-MM-DD
    date_to: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """List catalog booking requests for current agency."""

    org_id, agency_id = _ensure_agency(user)

    query: Dict[str, Any] = {
        "organization_id": org_id,
        "agency_id": agency_id,
    }
    if status:
        query["status"] = status
    if type:
        query["product_type"] = type

    # Date filter on created_at (inclusive bounds)
    if date_from or date_to:
        created_filter: Dict[str, Any] = {}
        try:
            if date_from:
                created_filter["$gte"] = datetime.fromisoformat(date_from + "T00:00:00")
            if date_to:
                created_filter["$lte"] = datetime.fromisoformat(date_to + "T23:59:59")
        except Exception:
            # Invalid date format -> ignore filter in MVP
            created_filter = {}
        if created_filter:
            query["created_at"] = created_filter

    cursor = (
        db.agency_catalog_booking_requests
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    items: List[Dict[str, Any]] = []
    async for doc in cursor:
        d = dict(doc)
        d["id"] = _sid(d.pop("_id"))
        # normalize IDs to strings
        if "product_id" in d:
            d["product_id"] = _sid(d["product_id"])
        if "variant_id" in d and isinstance(d["variant_id"], ObjectId):
            d["variant_id"] = _sid(d["variant_id"])
        d.pop("organization_id", None)
        d.pop("agency_id", None)
        items.append(d)

    return {"items": items}


@router.get("/{booking_id}")
async def get_catalog_booking_detail(
    booking_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    org_id, agency_id = _ensure_agency(user)
    booking_oid = _oid_or_404(booking_id)

    doc = await db.agency_catalog_booking_requests.find_one(
        {"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"code": "CATALOG_BOOKING_NOT_FOUND", "message": "Rezervasyon bulunamadı."},
        )

    d = dict(doc)
    d["id"] = _sid(d.pop("_id"))
    if "product_id" in d:
        d["product_id"] = _sid(d["product_id"])
    if "variant_id" in d and isinstance(d["variant_id"], ObjectId):
        d["variant_id"] = _sid(d["variant_id"])
    d.pop("organization_id", None)
    d.pop("agency_id", None)

    if "internal_notes" not in d or not isinstance(d["internal_notes"], list):
        d["internal_notes"] = []

    return d


@router.post("")
async def create_catalog_booking(
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    org_id, agency_id = _ensure_agency(user)

    product_id = (body.get("product_id") or "").strip()
    if not product_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "PRODUCT_ID_REQUIRED", "message": "product_id zorunludur."},
        )

    try:
        product_oid = to_object_id(product_id)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_PRODUCT_ID", "message": "Geçersiz ürün ID."},
        )

    prod = await db.agency_catalog_products.find_one(
        {"_id": product_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not prod:
        raise HTTPException(
            status_code=404,
            detail={"code": "CATALOG_PRODUCT_NOT_FOUND", "message": "Ürün bulunamadı."},
        )

    variant_id_raw = body.get("variant_id")
    variant_oid: Optional[ObjectId] = None
    variant = None
    if variant_id_raw:
        try:
            variant_oid = to_object_id(str(variant_id_raw))
        except Exception:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_VARIANT_ID", "message": "Geçersiz variant ID."},
            )
        variant = await db.agency_catalog_variants.find_one(
            {
                "_id": variant_oid,
                "organization_id": org_id,
                "agency_id": agency_id,
                "product_id": product_oid,
            }
        )
        if not variant:
            raise HTTPException(
                status_code=404,
                detail={"code": "CATALOG_VARIANT_NOT_FOUND", "message": "Variant bulunamadı."},
            )

    # Guest
    guest = body.get("guest") or {}
    full_name = (guest.get("full_name") or "").strip()
    if len(full_name) < 2:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_GUEST", "message": "Lütfen misafir için isim girin."},
        )

    dates = body.get("dates") or {}
    start = (dates.get("start") or "").strip()
    if not start:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_DATES", "message": "Başlangıç tarihi zorunludur."},
        )

    pax = int(body.get("pax", 1) or 1)
    if pax < 1:
        pax = 1

    # Pricing
    price = float(variant.get("price", 0.0) or 0.0) if variant else 0.0
    subtotal = round(price * pax, 2)

    try:
        commission_rate = float(body.get("commission_rate", 0.10) or 0.10)
    except Exception:
        commission_rate = 0.10
    # Clamp between 0 and 0.5 (0-50%)
    if commission_rate < 0.0:
        commission_rate = 0.0
    if commission_rate > 0.5:
        commission_rate = 0.5

    commission_amount = round(subtotal * commission_rate, 2)
    total = round(subtotal + commission_amount, 2)

    currency = (
        (variant or {}).get("currency")
        or prod.get("base_currency")
        or "TRY"
    )

    now = now_utc()

    created_by = {
        "user_id": _sid(user.get("id")),
        "name": user.get("name", "Unknown"),
        "role": (user.get("roles") or ["unknown"])[0],
    }

    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "agency_id": agency_id,
        "created_by": created_by,
        "product_id": product_oid,
        "product_type": prod.get("type"),
        "variant_id": variant_oid,
        "guest": {
            "full_name": full_name,
            "phone": (guest.get("phone") or "").strip(),
            "email": (guest.get("email") or "").strip(),
        },
        "dates": {
            "start": start,
            "end": (dates.get("end") or None),
        },
        "pax": pax,
        "pricing": {
            "subtotal": subtotal,
            "currency": currency,
            "commission_rate": commission_rate,
            "commission_amount": commission_amount,
            "total": total,
        },
        "offer": {
            "status": "draft",
            "expires_at": None,
            "net_price": subtotal,
            "commission_amount": commission_amount,
            "gross_price": total,
            "currency": currency,
            "note": "",
        },

        "status": "new",
        "internal_notes": [],
        "created_at": now,
        "updated_at": now,
    }

    res = await db.agency_catalog_booking_requests.insert_one(doc)
    saved = await db.agency_catalog_booking_requests.find_one({"_id": res.inserted_id})
    assert saved is not None

    d = dict(saved)
    d["id"] = _sid(d.pop("_id"))
    if "product_id" in d:
        d["product_id"] = _sid(d["product_id"])
    if d.get("variant_id") is not None and isinstance(d["variant_id"], ObjectId):
        d["variant_id"] = _sid(d["variant_id"])
    d.pop("organization_id", None)
    d.pop("agency_id", None)
    return d


async def _change_status(
    booking_id: str,
    next_status: str,
    *,
    allowed_from: Optional[List[str]] = None,
    reason_code: str = "CATALOG_INVALID_STATUS_TRANSITION",
    reason_message: str = "Bu işlem için geçersiz durum.",
    db,
    user: Dict[str, Any],
):
    org_id, agency_id = _ensure_agency(user)
    booking_oid = _oid_or_404(booking_id)

    doc = await db.agency_catalog_booking_requests.find_one(
        {"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"code": "CATALOG_BOOKING_NOT_FOUND", "message": "Rezervasyon bulunamadı."},
        )

    current_status = (doc.get("status") or "").lower()
    # Idempotent: already in desired status
    if current_status == next_status:
        d = dict(doc)
        d["id"] = _sid(d.pop("_id"))
        if "product_id" in d:
            d["product_id"] = _sid(d["product_id"])
        if d.get("variant_id") is not None and isinstance(d["variant_id"], ObjectId):
            d["variant_id"] = _sid(d["variant_id"])
        d.pop("organization_id", None)
        d.pop("agency_id", None)
        return d

    if allowed_from is not None and current_status not in allowed_from:
        raise HTTPException(
            status_code=409,
            detail={"code": reason_code, "message": reason_message},
        )

    now = now_utc()
    await db.agency_catalog_booking_requests.update_one(
        {"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id},
        {"$set": {"status": next_status, "updated_at": now}},
    )

    updated = await db.agency_catalog_booking_requests.find_one(
        {"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id}
    )
    assert updated is not None
    d = dict(updated)
    d["id"] = _sid(d.pop("_id"))
    if "product_id" in d:
        d["product_id"] = _sid(d["product_id"])
    if d.get("variant_id") is not None and isinstance(d["variant_id"], ObjectId):
        d["variant_id"] = _sid(d["variant_id"])
    d.pop("organization_id", None)
    d.pop("agency_id", None)
    return d


@router.post("/{booking_id}/approve")
async def approve_catalog_booking(
    booking_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin"])),
):
    """Approve booking: only allowed from new -> approved."""

    return await _change_status(
        booking_id,
        "approved",
        allowed_from=["new"],
        reason_code="CATALOG_APPROVE_INVALID_STATE",
        reason_message="Sadece 'Yeni' durumundaki talepler onaylanabilir.",
        db=db,


@router.post("/{booking_id}/offer/create")
async def create_catalog_offer(
    booking_id: str,
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    org_id, agency_id = _ensure_agency(user)
    booking_oid = _oid_or_404(booking_id)

    booking = await _get_catalog_booking_or_404(db, booking_oid, org_id, agency_id)

    note = (body.get("note") or "").strip()
    expires_at = body.get("expires_at") or None

    offer = _build_offer_snapshot(booking, note=note, expires_at=expires_at)

    now = now_utc()
    await db.agency_catalog_booking_requests.update_one(
        {"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id},
        {"$set": {"offer": offer, "updated_at": now}},
    )

    booking["offer"] = offer

    return {"ok": True, "offer": offer}


        user=user,
    )


@router.post("/{booking_id}/reject")
async def reject_catalog_booking(
    booking_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin"])),
):
    """Reject booking: only allowed from new -> rejected."""

    return await _change_status(
        booking_id,
        "rejected",
        allowed_from=["new"],
        reason_code="CATALOG_REJECT_INVALID_STATE",
        reason_message="Sadece 'Yeni' durumundaki talepler reddedilebilir.",
        db=db,
        user=user,
    )


@router.post("/{booking_id}/cancel")
async def cancel_catalog_booking(
    booking_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin"])),
):
    """Cancel booking: allowed from new or approved to cancelled."""

    return await _change_status(
        booking_id,
        "cancelled",
        allowed_from=["new", "approved"],
        reason_code="CATALOG_CANCEL_INVALID_STATE",
        reason_message="Sadece 'Yeni' veya 'Onaylandı' durumundaki talepler iptal edilebilir.",
        db=db,
        user=user,
    )


@router.post("/{booking_id}/internal-notes")
async def add_catalog_booking_internal_note(
    booking_id: str,
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """Add internal note to a catalog booking request."""

    org_id, agency_id = _ensure_agency(user)
    booking_oid = _oid_or_404(booking_id)

    text = (body.get("text") or "").strip()
    if len(text) < 2:
        raise HTTPException(
            status_code=400,
            detail={"code": "NOTE_EMPTY", "message": "Lütfen en az 2 karakterlik bir not girin."},
        )

    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    actor = {
        "user_id": _sid(user.get("id")),
        "name": user.get("name", "Unknown"),
        "role": (user.get("roles") or ["unknown"])[0],
    }

    note = {
        "text": text,
        "created_at": now,
        "actor": actor,
    }

    result = await db.agency_catalog_booking_requests.update_one(
        {"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id},
        {"$push": {"internal_notes": note}, "$set": {"updated_at": now_utc()}},
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail={"code": "CATALOG_BOOKING_NOT_FOUND", "message": "Rezervasyon bulunamadı."},
        )

    return {"ok": True}
