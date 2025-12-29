from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Response

from app.db import get_db
from app.utils import (
  now_utc,
  VoucherTokenExpired,
  VoucherTokenInvalid,
  VoucherTokenMissing,
  verify_voucher_token,
)
from app.services.tour_voucher_pdf import render_tour_voucher_pdf

router = APIRouter(prefix="/api/public/vouchers", tags=["public-vouchers"])


@router.get("/{voucher_id}.pdf")
async def get_public_voucher_pdf(voucher_id: str, t: str | None = None):
  """Public voucher PDF for tour booking request.

  - Public endpoint, but protected with short-lived HMAC token (?t=...)
  - Uses tour_booking_requests.voucher + payment snapshot
  """
  if not t:
    raise HTTPException(
      status_code=401,
      detail={"code": "VOUCHER_TOKEN_MISSING", "message": "Geçerli bir voucher erişim token'ı gerekli."},
    )

  now = now_utc()
  try:
    verify_voucher_token(voucher_id, t, now)
  except VoucherTokenMissing:
    raise HTTPException(
      status_code=401,
      detail={"code": "VOUCHER_TOKEN_MISSING", "message": "Geçerli bir voucher erişim token'ı gerekli."},
    )
  except VoucherTokenExpired:
    raise HTTPException(
      status_code=403,
      detail={"code": "VOUCHER_TOKEN_EXPIRED", "message": "Voucher erişim süresi dolmuş."},
    )
  except VoucherTokenInvalid:
    raise HTTPException(
      status_code=403,
      detail={"code": "VOUCHER_TOKEN_INVALID", "message": "Voucher token'ı geçersiz."},
    )

  db = await get_db()

  doc = await db.tour_booking_requests.find_one({"voucher.voucher_id": voucher_id})
  if not doc:
    raise HTTPException(
      status_code=404,
      detail={"code": "VOUCHER_NOT_FOUND", "message": "Voucher bulunamadı."},
    )

  voucher = doc.get("voucher") or {}
  if not voucher.get("enabled", True):
    raise HTTPException(
      status_code=409,
      detail={"code": "VOUCHER_DISABLED", "message": "Voucher devre dışı."},
    )

  # Build a minimal model from tour booking + payment snapshot for PDF
  payment = doc.get("payment") or {}
  guest = doc.get("guest") or {}

  # Agency/organization name if needed for header branding
  org_name = "-"
  agency_name = doc.get("agency_name") or None
  org_display = doc.get("organization_name") or None
  if agency_name:
    org_name = agency_name
  elif org_display:
    org_name = org_display

  model: Dict[str, Any] = {
    "agency_name": org_name,
    "reference_code": payment.get("reference_code") or voucher.get("voucher_id") or "-",
    "request_id": str(doc.get("_id") or doc.get("id") or "-"),
    "guest_full_name": guest.get("full_name") or "-",
    "guest_phone": guest.get("phone") or "-",
    "guest_email": guest.get("email") or "-",
    "tour_title": doc.get("tour_title") or "-",
    "desired_date": doc.get("desired_date"),
    "pax": doc.get("pax") or "-",
    "status": doc.get("status") or "-",
    "payment": {
      "amount": payment.get("amount"),
      "currency": (payment.get("currency") or (payment.get("iban_snapshot") or {}).get("currency") or "TRY"),
      "due_at": payment.get("due_at"),
      "iban_snapshot": payment.get("iban_snapshot") or {},
    },
  }

  try:
    pdf_bytes = render_tour_voucher_pdf(model)
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail={"code": "PDF_RENDER_FAILED", "message": "Voucher PDF oluşturulamadı."},
    ) from e

  # Simple, safe filename based on reference code (fallback if helper not available)
  ref = (model.get("reference_code") or "voucher").replace("/", "-").replace(" ", "_")
  filename = f"tour-voucher-{ref}.pdf"
  headers = {
    "Content-Disposition": f'inline; filename="{filename}"',
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Content-Length": str(len(pdf_bytes)),
  }
  return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
