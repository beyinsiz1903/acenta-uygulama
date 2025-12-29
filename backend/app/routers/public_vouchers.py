from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Response

from app.db import get_db
from app.utils import now_utc
from app.services.tour_voucher_pdf import render_tour_voucher_pdf

router = APIRouter(prefix="/api/public/vouchers", tags=["public-vouchers"])


@router.get("/{voucher_id}.pdf")
async def get_public_voucher_pdf(voucher_id: str):
  """Public voucher PDF for tour booking request.

  - No auth (public) for now
  - Uses tour_booking_requests.voucher + payment snapshot
  """
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

  model: Dict[str, Any] = {
    "reference": payment.get("reference_code") or voucher.get("voucher_id") or "-",
    "guest_full_name": guest.get("full_name") or "-",
    "guest_phone": guest.get("phone") or "-",
    "guest_email": guest.get("email") or "-",
    "tour_title": doc.get("tour_title") or "-",
    "desired_date": doc.get("desired_date") or "-",
    "pax": doc.get("pax") or "-",
    "status": doc.get("status") or "-",
    "amount": payment.get("amount"),
    "currency": payment.get("currency") or "TRY",
    "due_at": payment.get("due_at"),
    "iban_snapshot": payment.get("iban_snapshot") or {},
  }

  try:
    pdf_bytes = render_voucher_pdf_reportlab(model)  # reuse existing renderer with compatible model
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail={"code": "PDF_RENDER_FAILED", "message": "Voucher PDF oluşturulamadı."},
    ) from e

  filename = f"voucher-{model['reference']}.pdf"
  headers = {
    "Content-Disposition": f'inline; filename="{filename}"',
    "Cache-Control": "no-store",
    "Content-Length": str(len(pdf_bytes)),
  }
  return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
