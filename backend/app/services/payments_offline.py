from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import HTTPException

from app.db import get_db
from app.utils import now_utc


CODE_BOOKING_NOT_PAYABLE = "BOOKING_NOT_PAYABLE"
CODE_OFFLINE_PAYMENT_DISABLED = "OFFLINE_PAYMENT_DISABLED"


def _utc_now() -> datetime:
    return now_utc()


def _compute_payable_amount(booking: Dict[str, Any]) -> tuple[float, str]:
    """Single source of truth for payable amount.

    - Prefer gross_amount if present
    - Fallback to rate_snapshot.price.total
    """
    currency = (
        booking.get("currency")
        or booking.get("rate_snapshot", {}).get("price", {}).get("currency")
        or "TRY"
    )
    amt = booking.get("gross_amount")
    if amt is None:
        amt = booking.get("rate_snapshot", {}).get("price", {}).get("total")
    if amt is None:
        raise HTTPException(
            status_code=409,
            detail=f"{CODE_BOOKING_NOT_PAYABLE}: PAYABLE_AMOUNT_MISSING",
        )
    return float(amt), currency


def _ensure_payable(organization_id: str, booking: Dict[str, Any]) -> None:
    if str(booking.get("organization_id")) != str(organization_id):
        raise HTTPException(status_code=403, detail="FORBIDDEN")
    status = (booking.get("status") or "").lower()
    if status != "confirmed":
        raise HTTPException(status_code=409, detail=CODE_BOOKING_NOT_PAYABLE)


async def _load_offline_config(organization_id: str) -> Dict[str, Any]:
    db = await get_db()
    org = await db.organizations.find_one({"_id": organization_id})
    cfg = (org or {}).get("payment_offline") or {}

    enabled = bool(cfg.get("enabled"))
    iban = (cfg.get("iban") or "").strip()
    account_holder = (cfg.get("account_holder") or "").strip()

    if not enabled or not iban or not account_holder:
        raise HTTPException(
            status_code=409,
            detail=f"{CODE_OFFLINE_PAYMENT_DISABLED}: Offline payment not configured",
        )

    return {
        "iban": iban,
        "account_holder": account_holder,
        "bank_name": (cfg.get("bank_name") or "").strip() or None,
        "note": cfg.get("note") or None,
    }


def _ensure_reference_code(base_code: str | None, *, booking_id: str) -> str:
    if base_code:
        return base_code

    # PAY-YYYYMMDD-rand4 (base36)
    today = _utc_now().strftime("%Y%m%d")
    import random

    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"

    def gen_rand4() -> str:
        return "".join(random.choice(alphabet) for _ in range(4))

    return f"PAY-{today}-{gen_rand4()}"


async def get_payment_instructions(*, organization_id: str, booking: Dict[str, Any]) -> Dict[str, Any]:
    """Return offline payment instructions for a confirmed booking.

    - Guard: booking must belong to org and be confirmed
    - Source of IBAN/config: organization.payment_offline
    - Auto-creates payment snapshot if missing (atomic)
    """
    db = await get_db()

    _ensure_payable(organization_id, booking)

    # Ensure payment snapshot with atomic upsert (only when missing)
    payment = booking.get("payment") or {}
    if not payment:
        amount, currency = _compute_payable_amount(booking)

        for _ in range(2):  # at most 1 retry on rare collision
            ref = _ensure_reference_code(
                None, booking_id=str(booking.get("_id"))
            )
            now = _utc_now()
            update = {
                "payment": {
                    "method": "offline_iban",
                    "status": "unpaid",
                    "amount": amount,
                    "currency": currency,
                    "reference_code": ref,
                    "marked_paid_at": None,
                    "marked_paid_by": None,
                    "notes": None,
                    "created_at": now,
                }
            }
            res = await db.bookings.update_one(
                {"_id": booking.get("_id"), "organization_id": organization_id, "payment": {"$exists": False}},
                {"$set": update},
            )
            if res.matched_count == 1:
                payment = update["payment"]
                break
        if not payment:
            # someone else wrote concurrently; reload
            fresh = await db.bookings.find_one({"_id": booking.get("_id"), "organization_id": organization_id})
            payment = (fresh or {}).get("payment") or {}

    amount, currency = _compute_payable_amount(booking)
    offline_cfg = await _load_offline_config(organization_id)

    reference_code = _ensure_reference_code(
        payment.get("reference_code"), booking_id=str(booking.get("_id"))
    )

    return {
        "booking_id": str(booking.get("_id")),
        "status": booking.get("status"),
        "payment": {
            "method": payment.get("method") or "offline_iban",
            "status": payment.get("status") or "unpaid",
            "amount": amount,
            "currency": currency,
            "reference_code": reference_code,
            "marked_paid_at": payment.get("marked_paid_at"),
            "marked_paid_by": payment.get("marked_paid_by"),
            "notes": payment.get("notes"),
        },
        "offline": {
            "enabled": True,
            **offline_cfg,
        },
    }


async def mark_payment_paid(*, organization_id: str, booking: Dict[str, Any], actor: Dict[str, Any], notes: str | None = None) -> Dict[str, Any]:
    """Mark booking payment as paid (idempotent).

    - Only hotel_admin by default; agency_admin allowed if org.allow_agency_mark_paid is True
    - Booking must be confirmed
    """
    db = await get_db()

    _ensure_payable(organization_id, booking)

    roles = set(actor.get("roles") or [])
    org = await db.organizations.find_one({"_id": organization_id})
    allow_agency = bool((org or {}).get("allow_agency_mark_paid"))

    is_hotel = roles.intersection({"hotel_admin"})
    is_agency = roles.intersection({"agency_admin"})

    if not is_hotel and not (allow_agency and is_agency):
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    # Ensure offline config is valid (even if we don't use fields here)
    await _load_offline_config(organization_id)

    payment = booking.get("payment") or {}
    if (payment.get("status") or "").lower() == "paid":
        # idempotent: already paid
        return booking

    amount, currency = _compute_payable_amount(booking)
    reference_code = _ensure_reference_code(
        payment.get("reference_code"), booking_id=str(booking.get("_id"))
    )

    now = _utc_now()

    updater: Dict[str, Any] = {
        "payment.method": "offline_iban",
        "payment.status": "paid",
        "payment.amount": amount,
        "payment.currency": currency,
        "payment.reference_code": reference_code,
        "payment.marked_paid_at": now,
        "payment.marked_paid_by": {
            "user_id": actor.get("id"),
            "role": list(roles)[0] if roles else None,
            "email": actor.get("email"),
        },
    }
    if notes is not None:
        updater["payment.notes"] = notes

    await db.bookings.update_one(
        {"_id": booking.get("_id"), "organization_id": organization_id},
        {"$set": updater},
    )

    updated = await db.bookings.find_one({"_id": booking.get("_id"), "organization_id": organization_id})
    return updated or booking
