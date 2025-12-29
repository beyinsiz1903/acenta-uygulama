from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from app.auth import require_roles
from app.db import get_db
from app.utils import (
    now_utc,
    to_object_id,
    get_voucher_ttl_minutes,
    sign_voucher,
)
from app.services.agency_offline_payment import prepare_offline_payment_for_tour_booking

router = APIRouter(prefix="/api/agency", tags=["agency:tours:booking"])


def _oid_or_404(id_str: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")


def _sid(x: Any) -> str:
    return str(x)


@router.get("/tour-bookings")
async def list_tour_bookings(
    status: str | None = None,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    query: Dict[str, Any] = {"agency_id": agency_id}
    if status:
        query["status"] = status

    cursor = db.tour_booking_requests.find(query).sort("created_at", -1)
    items: List[Dict[str, Any]] = []
    async for doc in cursor:
        d = dict(doc)
        d["id"] = _sid(d.pop("_id"))
        items.append(d)
    return {"items": items}


@router.post("/tour-bookings/{request_id}/set-status")
async def set_tour_booking_status(
    request_id: str,
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    new_status = (body.get("status") or "").strip()
    if new_status not in {"new", "approved", "rejected", "cancelled"}:
        raise HTTPException(status_code=400, detail="INVALID_STATUS")

    # Convert string ID to ObjectId for MongoDB query
    request_oid = _oid_or_404(request_id)
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    result = await db.tour_booking_requests.update_one(
        {"_id": request_oid, "agency_id": agency_id},
        {"$set": {"status": new_status, "updated_at": now, "staff_note": body.get("note")}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")

    return {"ok": True, "status": new_status}


@router.get("/tour-bookings/{request_id}")
async def get_tour_booking_detail(
    request_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """Get tour booking request detail with internal notes"""
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    # Convert string ID to ObjectId for MongoDB query
    request_oid = _oid_or_404(request_id)

    doc = await db.tour_booking_requests.find_one(
        {"_id": request_oid, "agency_id": agency_id}
    )

    if not doc:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")

    # Convert to dict and format response
    result = dict(doc)
    result["id"] = _sid(result.pop("_id"))
    
    # Ensure internal_notes field exists (empty list if not present)
    if "internal_notes" not in result:
        result["internal_notes"] = []

    return result


@router.post("/tour-bookings/{request_id}/add-note")
async def add_internal_note(
    request_id: str,
    body: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """Add internal note to tour booking request"""
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    note_text = (body.get("text") or "").strip()
    if len(note_text) < 2:
        raise HTTPException(status_code=400, detail="INVALID_NOTE")

    # Convert string ID to ObjectId for MongoDB query
    request_oid = _oid_or_404(request_id)
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # Create note object
    note = {
        "text": note_text,
        "created_at": now,
        "actor": {
            "user_id": _sid(user.get("id")),
            "name": user.get("name", "Unknown"),
            "role": user.get("roles", ["unknown"])[0] if user.get("roles") else "unknown"
        }
    }

    # Add note to internal_notes array
    result = await db.tour_booking_requests.update_one(
        {"_id": request_oid, "agency_id": agency_id},
        {"$push": {"internal_notes": note}, "$set": {"updated_at": now}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")



@router.post("/tour-bookings/{request_id}/prepare-offline-payment")
async def prepare_offline_payment(
    request_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """Prepare offline payment snapshot for a tour booking request.

    - Only allowed for status in {"new", "approved"}
    - Uses agency_payment_settings.offline as source
    - Idempotent if snapshot already exists
    """
    agency_id = _sid(user.get("agency_id"))
    org_id = _sid(user.get("organization_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    request_oid = _oid_or_404(request_id)

    doc = await db.tour_booking_requests.find_one(
        {"_id": request_oid, "agency_id": agency_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")

    updated = await prepare_offline_payment_for_tour_booking(
        org_id=org_id,
        agency_id=agency_id,
        booking=doc,
    )

    # Normalize id field for response
    result = dict(updated)
    result["id"] = _sid(result.pop("_id"))
    return result


@router.post("/tour-bookings/{request_id}/voucher-signed-url")
async def create_tour_voucher_signed_url(
    request_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    """Generate a short-lived signed URL for tour voucher PDF.

    - Scope: agency_admin / agency_agent for their own agency's booking
    - Requires existing voucher metadata with enabled=True
    - Returns relative URL like /api/public/vouchers/{voucher_id}.pdf?t=...
    """
    agency_id = _sid(user.get("agency_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    request_oid = _oid_or_404(request_id)

    doc = await db.tour_booking_requests.find_one({"_id": request_oid, "agency_id": agency_id})
    if not doc:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")

    voucher = doc.get("voucher") or {}
    voucher_id = voucher.get("voucher_id")
    pdf_url = voucher.get("pdf_url")

    if not voucher_id or not pdf_url:
        raise HTTPException(
            status_code=409,
            detail={"code": "VOUCHER_NOT_READY", "message": "Bu talep için voucher henüz hazır değil."},
        )

    if voucher.get("enabled") is False:
        raise HTTPException(
            status_code=409,
            detail={"code": "VOUCHER_DISABLED", "message": "Bu voucher devre dışı bırakılmış."},
        )

    now = now_utc()
    ttl_min = get_voucher_ttl_minutes()
    from datetime import timedelta

    expires_at = now + timedelta(minutes=max(ttl_min, 1))

    token = sign_voucher(voucher_id, expires_at=expires_at)
    url = f"{pdf_url}?t={token}"

    return {"url": url, "expires_at": expires_at.isoformat()}



@router.post("/tour-bookings/{request_id}/send-voucher-email")
async def send_tour_voucher_email_endpoint(
    request_id: str,
    body: Dict[str, Any] | None = None,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin"])),
):
    """Send tour voucher + offline payment instructions via email using Resend.

    Preconditions:
    - Booking belongs to same agency + organization
    - guest.email or override to_email exists
    - offline payment snapshot prepared (payment.mode == 'offline')
    - voucher metadata exists and enabled
    """
    from app.services.tour_voucher_pdf import render_tour_voucher_pdf
    from app.utils import VoucherTokenError  # type: ignore[attr-defined]
    from app.services.email_resend import (
        ResendEmailError,
        ResendNotConfigured,
        send_tour_voucher_email,
    )

    agency_id = _sid(user.get("agency_id"))
    org_id = _sid(user.get("organization_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    request_oid = _oid_or_404(request_id)

    doc = await db.tour_booking_requests.find_one(
        {"_id": request_oid, "agency_id": agency_id, "organization_id": org_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")

    guest = doc.get("guest") or {}
    default_email = (guest.get("email") or "").strip()

    to_email = (body or {}).get("to_email") or default_email
    note_text = ((body or {}).get("note") or "").strip() or None

    if not to_email:
        raise HTTPException(
            status_code=409,
            detail={"code": "EMAIL_MISSING", "message": "Misafir e-posta adresi bulunamadı."},
        )

    payment = doc.get("payment") or {}
    mode = (payment.get("mode") or "").lower()
    ref = payment.get("reference_code")
    iban_snapshot = payment.get("iban_snapshot") or {}

    has_snapshot = (
        mode == "offline"
        and bool(ref)
        and bool(payment.get("due_at"))
        and bool(iban_snapshot.get("iban"))
    )
    if not has_snapshot:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "OFFLINE_PAYMENT_NOT_PREPARED",
                "message": "Önce offline ödeme talimatını hazırlayın.",
            },
        )

    voucher = doc.get("voucher") or {}
    if not voucher.get("voucher_id"):
        raise HTTPException(
            status_code=409,
            detail={"code": "VOUCHER_NOT_READY", "message": "Bu talep için voucher henüz hazır değil."},
        )
    if voucher.get("enabled") is False:
        raise HTTPException(
            status_code=409,
            detail={"code": "VOUCHER_DISABLED", "message": "Bu voucher devre dışı bırakılmış."},
        )

    # Build model for PDF renderer
    model = {
        "tour_title": doc.get("tour_title"),
        "tour_id": doc.get("tour_id"),
        "desired_date": doc.get("desired_date"),
        "pax": doc.get("pax"),
        "status": doc.get("status"),
        "guest": guest,
        "payment": payment,
        "reference_code": ref,
        "organization_id": doc.get("organization_id"),
        "agency_id": doc.get("agency_id"),
    }

    pdf_bytes, pdf_filename = render_tour_voucher_pdf(model)

    # Simple HTML email body
    snap = iban_snapshot
    currency = payment.get("currency") or snap.get("currency") or "TRY"
    due = payment.get("due_at")
    filled_note = (snap.get("note_template") or "Rezervasyon: {reference_code}").replace(
        "{reference_code}", ref or "",
    )

    guest_name = guest.get("full_name") or "Misafir"
    tour_title = doc.get("tour_title") or "Tur"
    desired_date = doc.get("desired_date") or "-"
    pax = doc.get("pax") or 1

    extra_note_html = f"<p>{note_text}</p>" if note_text else ""

    html = f"""
    <div style='font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size:14px; color:#111827;'>
      <p>Merhaba {guest_name},</p>
      {extra_note_html}
      <p>Bu e-postanın ekinde tur rezervasyonunuza ait voucher PDF ve offline ödeme talimatı bulunmaktadır.</p>

      <h3 style="margin-top:16px; font-size:15px;">Rezervasyon Özeti</h3>
      <ul>
        <li><strong>Tur:</strong> {tour_title}</li>
        <li><strong>Tarih:</strong> {desired_date}</li>
        <li><strong>Kişi sayısı:</strong> {pax}</li>
      </ul>

      <h3 style="margin-top:16px; font-size:15px;">Ödeme Bilgileri</h3>
      <ul>
        <li><strong>Hesap Sahibi:</strong> {snap.get("account_name") or "-"}</li>
        <li><strong>Banka Adı:</strong> {snap.get("bank_name") or "-"}</li>
        <li><strong>IBAN:</strong> {snap.get("iban") or "-"}</li>
        <li><strong>Para Birimi / SWIFT:</strong> {currency} {" / " + snap.get("swift") if snap.get("swift") else ""}</li>
        <li><strong>Son Ödeme Tarihi:</strong> {due or "-"}</li>
        <li><strong>Referans Kodu:</strong> {ref or "-"}</li>
        <li><strong>Ödeme Açıklaması Önerisi:</strong> {filled_note}</li>
      </ul>

      <p style="margin-top:16px;">Lütfen ödemenizi yaparken yukarıdaki referans kodunu ve açıklamayı kullanın.</p>
      <p>Teşekkürler.</p>
    </div>
    """

    subject = f"Tur Voucher - {ref or tour_title}"

    try:
        resend_resp = await send_tour_voucher_email(
            to_email=to_email,
            subject=subject,
            html=html,
            pdf_bytes=pdf_bytes,
            pdf_filename=pdf_filename,
        )
    except ResendNotConfigured as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "RESEND_NOT_CONFIGURED",
                "message": "E-posta servisi yapılandırılmamış (RESEND_API_KEY / RESEND_FROM_EMAIL).",
            },
        ) from exc
    except ResendEmailError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "EMAIL_SEND_FAILED", "message": "E-posta gönderimi başarısız oldu."},
        ) from exc

    # Internal note for audit
    note_created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    actor = {
        "user_id": _sid(user.get("id")),
        "name": user.get("name", "Unknown"),
        "role": (user.get("roles") or ["unknown"])[0],
    }
    internal_note = {
        "text": f"Voucher e-posta ile gönderildi: {to_email}",
        "created_at": note_created_at,
        "actor": actor,
    }
    await db.tour_booking_requests.update_one(
        {"_id": request_oid, "agency_id": agency_id, "organization_id": org_id},
        {"$push": {"internal_notes": internal_note}},
    )

    return {
        "ok": True,
        "to_email": to_email,
        "sent_at": now_utc().isoformat(),
        "provider": "resend",
        "provider_id": resend_resp.get("id"),
    }



@router.post("/tour-bookings/{request_id}/mark-offline-paid")
async def mark_offline_paid(
    request_id: str,
    body: Dict[str, Any] | None = None,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin"])),
):
    """Mark offline payment as paid for an approved tour booking.

    - Only agency_admin can perform this action
    - Booking must belong to same agency + organization
    - Booking status must be 'approved'
    - Payment.mode must be 'offline' and snapshot must exist
    - Idempotent: if already paid, returns current document without changes
    """
    agency_id = _sid(user.get("agency_id"))
    org_id = _sid(user.get("organization_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    request_oid = _oid_or_404(request_id)

    doc = await db.tour_booking_requests.find_one(
        {"_id": request_oid, "agency_id": agency_id, "organization_id": org_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")

    status = (doc.get("status") or "").lower()
    if status != "approved":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "OFFLINE_PAYMENT_NOT_APPROVED",
                "message": "Ödeme yalnızca Onaylandı durumundaki taleplerde işaretlenebilir.",
            },
        )

    payment = doc.get("payment") or {}
    mode = (payment.get("mode") or "").lower()
    ref = payment.get("reference_code")
    iban_snapshot = payment.get("iban_snapshot") or {}

    has_snapshot = (
        mode == "offline"
        and bool(ref)
        and bool(payment.get("due_at"))
        and bool(iban_snapshot.get("iban"))
    )
    if not has_snapshot:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "OFFLINE_PAYMENT_NOT_PREPARED",
                "message": "Önce offline ödeme talimatını hazırlayın.",
            },
        )

    # Idempotent: if already paid, return current document without changes
    if (payment.get("status") or "").lower() == "paid":
        result = dict(doc)
        result["id"] = _sid(result.pop("_id"))
        return result

    note: Optional[str] = None
    method: Optional[str] = None
    if body:
        raw_note = (body.get("note") or "").strip()
        note = raw_note or None
        method = (body.get("method") or "manual").strip() or "manual"

    now = now_utc()
    # Internal note timestamp as ISO string
    note_created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    actor = {
        "user_id": _sid(user.get("id")),
        "name": user.get("name", "Unknown"),
        "role": (user.get("roles") or ["unknown"])[0],
    }

    updates = {
        "payment.status": "paid",
        "payment.paid_at": now,
        "payment.paid_by": actor,
        "payment.paid_note": note,
        "payment.paid_method": method or "manual",
        "updated_at": now,
    }

    internal_note = {
        "text": "Offline ödeme ödendi olarak işaretlendi.",
        "created_at": note_created_at,
        "actor": actor,
    }

    await db.tour_booking_requests.update_one(
        {"_id": request_oid, "agency_id": agency_id, "organization_id": org_id},
        {"$set": updates, "$push": {"internal_notes": internal_note}},
    )

    updated = await db.tour_booking_requests.find_one(
        {"_id": request_oid, "agency_id": agency_id, "organization_id": org_id}
    )
    assert updated is not None
    result = dict(updated)
    result["id"] = _sid(result.pop("_id"))
    return result


@router.post("/tour-bookings/{request_id}/mark-offline-unpaid")
async def mark_offline_unpaid(
    request_id: str,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin"])),
):
    """Revert offline payment back to unpaid.

    - Only agency_admin can perform this action
    - Booking must belong to same agency + organization
    - Idempotent: if not paid, returns current document without changes
    """
    agency_id = _sid(user.get("agency_id"))
    org_id = _sid(user.get("organization_id"))
    if not agency_id:
        raise HTTPException(status_code=400, detail="USER_NOT_IN_AGENCY")

    request_oid = _oid_or_404(request_id)

    doc = await db.tour_booking_requests.find_one(
        {"_id": request_oid, "agency_id": agency_id, "organization_id": org_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="TOUR_BOOKING_REQUEST_NOT_FOUND")

    payment = doc.get("payment") or {}
    mode = (payment.get("mode") or "").lower()

    # If not offline or already unpaid, behave idempotently
    if mode != "offline" or (payment.get("status") or "unpaid").lower() != "paid":
        result = dict(doc)
        result["id"] = _sid(result.pop("_id"))
        return result

    now = now_utc()
    note_created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    actor = {
        "user_id": _sid(user.get("id")),
        "name": user.get("name", "Unknown"),
        "role": (user.get("roles") or ["unknown"])[0],
    }

    updates = {
        "payment.status": "unpaid",
        "payment.paid_at": None,
        "payment.paid_by": None,
        "payment.paid_note": None,
        "payment.paid_method": None,
        "updated_at": now,
    }

    internal_note = {
        "text": "Offline ödeme geri alındı.",
        "created_at": note_created_at,
        "actor": actor,
    }

    await db.tour_booking_requests.update_one(
        {"_id": request_oid, "agency_id": agency_id, "organization_id": org_id},
        {"$set": updates, "$push": {"internal_notes": internal_note}},
    )

    updated = await db.tour_booking_requests.find_one(
        {"_id": request_oid, "agency_id": agency_id, "organization_id": org_id}
    )
    assert updated is not None
    result = dict(updated)
    result["id"] = _sid(result.pop("_id"))
    return result
