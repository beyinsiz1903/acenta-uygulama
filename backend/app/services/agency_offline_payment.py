from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from fastapi import HTTPException

from app.db import get_db
from app.utils import now_utc


CODE_INVALID_STATUS_FOR_PAYMENT = "INVALID_STATUS_FOR_PAYMENT"
CODE_PAYMENT_SETTINGS_MISSING = "PAYMENT_SETTINGS_MISSING"
CODE_OFFLINE_PAYMENT_DISABLED = "OFFLINE_PAYMENT_DISABLED"


async def _load_agency_payment_settings(org_id: str, agency_id: str) -> Dict[str, Any]:
  db = await get_db()
  doc = await db.agency_payment_settings.find_one(
    {"organization_id": org_id, "agency_id": agency_id}
  )
  if not doc:
    raise HTTPException(
      status_code=404,
      detail={
        "code": CODE_PAYMENT_SETTINGS_MISSING,
        "message": "Offline ödeme ayarları tanımlı değil.",
      },
    )

  offline = (doc.get("offline") or {})
  if not offline.get("enabled"):
    raise HTTPException(
      status_code=409,
      detail={
        "code": CODE_OFFLINE_PAYMENT_DISABLED,
        "message": "Offline ödeme kapalı.",
      },
    )

  return offline


def _ensure_status_allows_payment(status: str) -> None:
  status_norm = (status or "").lower()
  if status_norm not in {"new", "approved"}:
    raise HTTPException(
      status_code=409,
      detail={
        "code": CODE_INVALID_STATUS_FOR_PAYMENT,
        "message": "Bu durumda ödeme hazırlanamaz.",
      },
    )


async def prepare_offline_payment_for_tour_booking(
  *, org_id: str, agency_id: str, booking: Dict[str, Any]
) -> Dict[str, Any]:
  """Prepare offline payment snapshot for a tour booking request.

  - Only allowed for status in {"new", "approved"}
  - Idempotent: if snapshot already exists, returns existing snapshot
  - Uses agency_payment_settings.offline as source
  """
  _ensure_status_allows_payment(booking.get("status"))

  payment = booking.get("payment") or {}
  mode = (payment.get("mode") or "").lower()
  ref = payment.get("reference_code")
  iban_snapshot = payment.get("iban_snapshot") or {}

  # Ensure new payment fields exist with backwards-compatible defaults
  if "status" not in payment:
    payment["status"] = "unpaid"

  if "paid_at" not in payment:
    payment["paid_at"] = None

  if "paid_by" not in payment:
    payment["paid_by"] = {
      "user_id": None,
      "name": None,
      "role": None,
    }

  if "paid_note" not in payment:
    payment["paid_note"] = None

  if "paid_method" not in payment:
    payment["paid_method"] = "manual"

  def has_offline_payment_snapshot() -> bool:
    return (
      mode == "offline"
      and bool(ref)
      and bool(payment.get("due_at"))
      and bool(iban_snapshot.get("iban"))
    )

  def has_voucher_meta() -> bool:
    v = booking.get("voucher") or {}
    return bool(v.get("voucher_id")) and bool(v.get("pdf_url"))

  has_payment = has_offline_payment_snapshot()
  has_voucher = has_voucher_meta()

  # C) Payment + voucher zaten varsa: tam idempotent erken dönüş
  if has_payment and has_voucher:
    return booking

  # Zaman damgası tüm yollar için burada hesaplanır
  now = now_utc()

  # B) Payment var ama voucher yoksa: sadece voucher üret, payment'a dokunma
  if has_payment and not has_voucher:
    from uuid import uuid4

    v_id = f"vtr_{uuid4().hex[:24]}"
    voucher = {
      "enabled": True,
      "voucher_id": v_id,
      "issued_at": now,
      "issued_by": {
        "user_id": None,
        "role": None,
      },
      "pdf_url": f"/api/public/vouchers/{v_id}.pdf",
      "version": 1,
    }

    db = await get_db()
    await db.tour_booking_requests.update_one(
      {"_id": booking.get("_id"), "agency_id": agency_id},
      {"$set": {"voucher": voucher, "updated_at": now}},
    )

    booking["voucher"] = voucher
    return booking

  # A) Payment snapshot yoksa: ayarlardan yeni snapshot + voucher üret
  offline = await _load_agency_payment_settings(org_id, agency_id)

  default_due_days = int(offline.get("default_due_days") or 2)
  due_at = now + timedelta(days=max(default_due_days, 0))

  # Simple readable reference code: SYR-TOUR-<last8 of id>
  booking_id = str(booking.get("_id"))
  tail = booking_id.replace("-", "").replace("_", "")[ -8 : ] or booking_id[:8]
  reference_code = ref or f"SYR-TOUR-{tail.upper()}"

  iban_snapshot = {
    "account_name": offline.get("account_name"),
    "bank_name": offline.get("bank_name"),
    "iban": offline.get("iban"),
    "swift": offline.get("swift"),
    "currency": offline.get("currency") or "TRY",
    "note_template": offline.get("note_template") or "Rezervasyon: {reference_code}",
  }

  update_payment = {
    "mode": "offline",
    "status": payment.get("status") or "unpaid",
    "paid_at": payment.get("paid_at"),
    "paid_by": payment.get("paid_by"),
    "paid_note": payment.get("paid_note"),
    "paid_method": payment.get("paid_method") or "manual",
    "currency": iban_snapshot["currency"],
    "due_at": due_at,
    "reference_code": reference_code,
    "iban_snapshot": iban_snapshot,
  }

  # Persist snapshot on tour_booking_requests (idempotent upsert-style)
  db = await get_db()

  # Idempotent voucher metadata
  voucher = booking.get("voucher") or {}
  if not voucher.get("voucher_id"):
    from uuid import uuid4

    v_id = f"vtr_{uuid4().hex[:24]}"
    voucher = {
      "enabled": True,
      "voucher_id": v_id,
      "issued_at": now,
      "issued_by": {
        "user_id": None,
        "role": None,
      },
      "pdf_url": f"/api/public/vouchers/{v_id}.pdf",
      "version": 1,
    }

  await db.tour_booking_requests.update_one(
    {"_id": booking.get("_id"), "agency_id": agency_id},
    {"$set": {"payment": update_payment, "voucher": voucher, "updated_at": now}},
  )

  booking["payment"] = update_payment
  booking["voucher"] = voucher
  return booking
