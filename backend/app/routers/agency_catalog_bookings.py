from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_roles
from app.db import get_db
from app.utils import now_utc, to_object_id, sign_voucher


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


def parse_iso_dt(s: Optional[str]):
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _offer_from_pricing(booking: Dict[str, Any], note: str = "", expires_at: Optional[datetime] = None) -> Dict[str, Any]:
    pricing = booking.get("pricing") or {}
    currency = pricing.get("currency") or "TRY"
    subtotal = float(pricing.get("subtotal") or 0.0)
    commission_amount = float(pricing.get("commission_amount") or 0.0)
    total = float(pricing.get("total") or (subtotal + commission_amount))
    return {
        "status": "draft",  # draft | sent | accepted | expired
        "expires_at": (expires_at.isoformat().replace("+00:00", "Z") if expires_at else None),
        "net_price": subtotal,
        "commission_amount": commission_amount,
        "gross_price": total,
        "currency": currency,
        "note": note or "",
    }


def _build_offer_snapshot(booking: Dict[str, Any], note: str = "", expires_at: Optional[datetime] = None) -> Dict[str, Any]:
    return _offer_from_pricing(booking, note=note, expires_at=expires_at)


async def _maybe_expire_offer(db, booking: Dict[str, Any]) -> Dict[str, Any]:
    offer = booking.get("offer") or None
    if not offer:
        return booking
    status = (offer.get("status") or "").lower()
    exp = parse_iso_dt(offer.get("expires_at"))
    if status in ("draft", "sent") and exp and exp < now_utc():
        offer["status"] = "expired"
        booking["offer"] = offer
        await db.agency_catalog_booking_requests.update_one(
            {"_id": booking["_id"]},
            {"$set": {"offer.status": "expired", "updated_at": now_utc()}},
        )
    return booking


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

    doc = await _maybe_expire_offer(db, doc)

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

    # Capacity check if variant is present
    allocation = None
    overbook_flag = False
    overbook_day: Optional[str] = None
    if variant is not None:
        from app.services.catalog_availability import expand_dates, compute_availability, compute_units

        dates_dict = {"start": start, "end": (dates.get("end") or None)}
        try:
            days = expand_dates(dates_dict["start"], dates_dict["end"])
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_DATES", "message": "Geçersiz tarih aralığı."},
            )

        capacity = variant.get("capacity") or {}
        mode_raw = (capacity.get("mode") or "pax").lower()
        mode = mode_raw if mode_raw in {"pax", "bookings"} else "pax"

        availability = await compute_availability(
            db,
            org_id=org_id,
            agency_id=agency_id,
            product_oid=product_oid,
            variant=variant,
            days=days,
            pax=pax,
        )
        summary = availability.get("summary") or {}
        requested_units = availability.get("requested_units") or compute_units(mode, pax)

        # Determine potential overbook days (where remaining < requested_units)
        days_info = availability.get("days") or []
        max_per_day_val = capacity.get("max_per_day")
        try:
            max_per_day = int(max_per_day_val) if max_per_day_val is not None else None
        except Exception:
            max_per_day = None

        for d in days_info:
            rem = d.get("remaining")
            day_max = d.get("max", max_per_day)
            if day_max is None or rem is None:
                continue
            if rem < requested_units:
                overbook_flag = True
                overbook_day = d.get("day")
                break

        overbook_allowed = bool(capacity.get("overbook", False))

        if not overbook_allowed and (summary.get("can_book") is False or overbook_flag):
            # Capacity not available and overbook not allowed
            blocking_day = overbook_day or summary.get("blocking_day")
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "CAPACITY_NOT_AVAILABLE",
                    "message": "Seçilen tarih(ler) için kapasite dolu.",
                    "meta": {
                        "blocking_day": blocking_day,
                        "mode": mode,
                        "requested_units": requested_units,
                    },
                },
            )

        # Build allocation snapshot for new bookings
        units = compute_units(mode, pax)
        allocation = {"mode": mode, "units": units, "days": days}
        if overbook_flag:
            allocation["overbook"] = True
            allocation["overbook_reason"] = "capacity"

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
        "allocation": allocation,
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

    # Overbook audit note: attach to doc before insert
    if allocation and allocation.get("overbook"):
        overbook_at = now
        allocation["overbook_at"] = overbook_at
        overbook_days = ", ".join(allocation.get("days") or [])
        note_text = f"Overbook yapıldı ({overbook_days}, pax={pax})"
        note_doc = {
            "text": note_text,
            "created_at": overbook_at,
            "actor": created_by,
        }
        doc.setdefault("internal_notes", []).append(note_doc)


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
        user=user,
    )


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


@router.post("/{booking_id}/offer/send")
async def send_catalog_offer(
    booking_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    org_id, agency_id = _ensure_agency(user)
    booking_oid = _oid_or_404(booking_id)

    booking = await _get_catalog_booking_or_404(db, booking_oid, org_id, agency_id)

    status = (booking.get("status") or "").lower()
    if status != "approved":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "BOOKING_NOT_APPROVED",
                "message": "Teklif göndermek için rezervasyon onaylanmış olmalı.",
            },
        )

    body_offer = booking.get("offer") or {}
    note = (body_offer.get("note") or "").strip()

    now = now_utc()
    # default 3 days expiry
    expires_at = body_offer.get("expires_at") or (now + timedelta(days=3))

    offer = _build_offer_snapshot(booking, note=note, expires_at=expires_at)
    offer["status"] = "sent"

    token = sign_voucher(booking_id, expires_at=expires_at)
    public_url = f"/api/public/catalog-offers/{booking_id}.pdf?t={token}"

    created_by = {
        "user_id": _sid(user.get("id")),
        "name": user.get("name", "Unknown"),
        "role": (user.get("roles") or ["unknown"])[0],
    }
    note_doc = {
        "text": f"Teklif gönderildi (expires_at={expires_at.isoformat()})",
        "created_at": now,
        "actor": created_by,
    }

    # Persist offer + internal note
    await db.agency_catalog_booking_requests.update_one(
        {"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id},
        {"$set": {"offer": offer, "updated_at": now}, "$push": {"internal_notes": note_doc}},
    )

    return {"ok": True, "offer": offer, "public_url": public_url}


@router.post("/{booking_id}/offer/send-email")
async def send_catalog_offer_email_endpoint(
    booking_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """Send catalog offer link via Resend to the guest's email.

    - Requires booking.status == approved
    - Requires guest.email present
    - Uses signed public catalog-offer PDF URL
    """
    from app.services.email_resend import (
        ResendEmailError,
        ResendNotConfigured,
        send_catalog_offer_email,
    )

    org_id, agency_id = _ensure_agency(user)
    booking_oid = _oid_or_404(booking_id)

    booking = await _get_catalog_booking_or_404(db, booking_oid, org_id, agency_id)

    status = (booking.get("status") or "").lower()
    if status != "approved":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "BOOKING_NOT_APPROVED",
                "message": "Teklif göndermek için rezervasyon onaylanmış olmalı.",
            },
        )

    guest = booking.get("guest") or {}
    to_email = (guest.get("email") or "").strip()
    if not to_email:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_GUEST_EMAIL", "message": "Misafir e-posta adresi bulunamadı."},
        )

    now = now_utc()
    offer = booking.get("offer") or {}
    note_text = (offer.get("note") or "").strip() or None

    # Ensure expires_at
    expires_at = offer.get("expires_at")
    if expires_at is None:
        from datetime import timedelta

        expires_at_dt = now + timedelta(days=3)
        offer = _build_offer_snapshot(booking, note=note_text or "", expires_at=expires_at_dt)
        offer["status"] = offer.get("status", "draft")
        expires_at = offer["expires_at"]
        await db.agency_catalog_booking_requests.update_one(
            {"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id},
            {"$set": {"offer": offer, "updated_at": now}},
        )

    # Signed URL (reuse voucher signing)
    from datetime import datetime as dt

    # expires_at stored as ISO string with Z
    if isinstance(expires_at, str):
        exp_str = expires_at
        if exp_str.endswith("Z"):
            exp_str = exp_str[:-1] + "+00:00"
        expires_dt = dt.fromisoformat(exp_str)
    else:
        expires_dt = now

    token = sign_voucher(booking_id, expires_at=expires_dt)
    public_url = f"/api/public/catalog-offers/{booking_id}.pdf?t={token}"

    # Absolute URL for email
    import os

    backend_base = os.environ.get("PUBLIC_BACKEND_BASE_URL") or os.environ.get("REACT_APP_BACKEND_URL")
    if backend_base:
        backend_base = backend_base.rstrip("/")
        public_url_abs = f"{backend_base}{public_url}"
    else:
        public_url_abs = public_url

    product_title = (booking.get("product_title") or "Katalog Ürün")
    dates = booking.get("dates") or {}
    start_date = dates.get("start") or "-"
    end_date = dates.get("end") or None
    pax = booking.get("pax") or 1
    pricing = booking.get("pricing") or {}
    total = pricing.get("total") or pricing.get("subtotal") or 0
    currency = pricing.get("currency") or "TRY"

    subject = f"Teklifiniz hazır: {product_title}"

    guest_name = guest.get("full_name") or "Misafir"
    expiry_text = expires_at or "-"

    html = f"""
    <div style='font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size:14px; color:#111827;'>
      <p>Merhaba {guest_name},</p>
      <p>Sizin için hazırlanan teklif detaylarını aşağıda bulabilirsiniz.</p>
      <h3 style="margin-top:16px; font-size:15px;">Rezervasyon Özeti</h3>
      <ul>
        <li><strong>Ürün:</strong> {product_title}</li>
        <li><strong>Tarih:</strong> {start_date}{(" - " + end_date) if end_date else ""}</li>
        <li><strong>Kişi sayısı:</strong> {pax}</li>
        <li><strong>Toplam:</strong> {total} {currency}</li>
      </ul>
      <p style="margin-top:12px;">Teklif detaylarını PDF olarak görüntülemek için aşağıdaki bağlantıyı kullanabilirsiniz:</p>
      <p><a href="{public_url_abs}" target="_blank" rel="noopener noreferrer">Teklifi PDF olarak aç</a></p>
      <p>Bu teklif {expiry_text} tarihine kadar geçerlidir.</p>
      <p>Teşekkürler.</p>
    </div>
    """

    text = (
        f"Merhaba {guest_name},\n\n"
        f"Ürün: {product_title}\n"
        f"Tarih: {start_date}{(' - ' + end_date) if end_date else ''}\n"
        f"Kişi sayısı: {pax}\n"
        f"Toplam: {total} {currency}\n\n"
        f"Teklif PDF bağlantısı: {public_url_abs}\n"
        f"Geçerlilik: {expiry_text}\n"
    )

    tags = []
    tag_env = os.environ.get("RESEND_TAG")
    if tag_env:
        tags.append(tag_env)
    tags.append("catalog-offer")

    try:
        resend_resp = await send_catalog_offer_email(
            to_email=to_email,
            subject=subject,
            html=html,
            text=text,
            tags=tags,
        )
    except ResendNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "EMAIL_PROVIDER_NOT_CONFIGURED",
                "message": "E-posta servisi yapılandırılmamış (RESEND_API_KEY / RESEND_FROM_EMAIL).",
            },
        ) from exc
    except ResendEmailError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "EMAIL_SEND_FAILED",
                "message": "Teklif e-postası gönderilemedi.",
                "meta": {"provider": "resend"},
            },
        ) from exc

    provider_id = resend_resp.get("id")

    # Internal note + offer.last_email snapshot
    actor = {
        "user_id": _sid(user.get("id")),
        "name": user.get("name", "Unknown"),
        "role": (user.get("roles") or ["unknown"])[0],
    }

    note_doc = {
        "text": f"Teklif e-posta ile gönderildi: {to_email} (provider_id={provider_id}, expires_at={expiry_text})",
        "created_at": now,
        "actor": actor,
    }

    last_email = {
        "provider": "resend",
        "provider_id": provider_id,
        "to_email": to_email,
        "sent_at": now,
    }

    await db.agency_catalog_booking_requests.update_one(
        {"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id},
        {"$set": {"offer.last_email": last_email, "updated_at": now}, "$push": {"internal_notes": note_doc}},
    )

    return {
        "ok": True,
        "provider": "resend",
        "provider_id": provider_id,
        "to_email": to_email,
        "public_url": public_url,
        "public_url_abs": public_url_abs,
        "offer": offer,
    }


@router.post("/{booking_id}/offer/accept")
async def accept_catalog_offer(
    booking_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    org_id, agency_id = _ensure_agency(user)
    booking_oid = _oid_or_404(booking_id)

    booking = await _get_catalog_booking_or_404(db, booking_oid, org_id, agency_id)

    offer = booking.get("offer") or {}
    status = (offer.get("status") or "").lower()
    if status != "sent":
        raise HTTPException(
            status_code=409,
            detail={"code": "OFFER_NOT_SENT", "message": "Teklif gönderilmeden kabul edilemez."},
        )

    expires_at = offer.get("expires_at")
    now = now_utc()
    if expires_at and isinstance(expires_at, datetime) and expires_at < now:
        raise HTTPException(
            status_code=409,
            detail={"code": "OFFER_EXPIRED", "message": "Teklifin süresi dolmuş."},
        )

    offer["status"] = "accepted"

    created_by = {
        "user_id": _sid(user.get("id")),
        "name": user.get("name", "Unknown"),
        "role": (user.get("roles") or ["unknown"])[0],
    }

    note_doc = {
        "text": "Teklif kabul edildi.",
        "created_at": now,
        "actor": created_by,
    }

    await db.agency_catalog_booking_requests.update_one(
        {"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id},
        {"$set": {"offer": offer, "updated_at": now}, "$push": {"internal_notes": note_doc}},
    )

    return {"ok": True, "offer": offer}


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
