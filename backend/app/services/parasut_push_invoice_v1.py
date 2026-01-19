from __future__ import annotations

"""Paraşüt invoice push V1 (PZ3).

Bridges bookings -> ParasutContactInput / ParasutInvoiceInput and uses
ParasutPushLogService + ParasutClient (mock) to implement an idempotent
push entrypoint.
"""

from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from bson import ObjectId

from app.services.parasut_client import (
    ParasutClient,
    ParasutContactInput,
    ParasutInvoiceInput,
    get_parasut_client,
)
from app.services.parasut_push_log import ParasutPushLogService
from app.utils import now_utc


def _extract_amount_and_currency(booking: dict[str, Any]) -> tuple[Decimal, str]:
    """Best-effort extraction of invoice amount + currency from booking.

    MVP rules:
    - amount: prefer booking.amount_total_cents / 100; fallback to amounts.sell
    - currency: booking.currency or amounts.currency or EUR
    """

    amounts = booking.get("amounts") or {}

    # amount_total_cents from public checkout / b2b bookings
    amount_total_cents = booking.get("amount_total_cents")
    if amount_total_cents is not None:
        try:
            cents = int(amount_total_cents)
            amount = Decimal(cents) / Decimal(100)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(f"invalid_amount_total_cents: {exc}")
        currency = booking.get("currency") or amounts.get("currency") or "EUR"
        return amount, currency

    # Fallback: amounts.sell
    sell = amounts.get("sell")
    if sell is not None:
        amount = Decimal(str(sell))
        currency = booking.get("currency") or amounts.get("currency") or "EUR"
        return amount, currency

    raise ValueError("missing_amount")


def build_contact_input(organization_id: str, booking: dict[str, Any]) -> ParasutContactInput:
    """Build ParasutContactInput from booking.

    Rules:
    - B2B: use agency if present (agency_id + name)
    - B2C: fallback to guest full_name/email
    - external_id: stable key based on org + agency/guest
    """

    agency_id = booking.get("agency_id")
    guest = booking.get("guest") or {}
    guest_email = guest.get("email") or booking.get("guest_email")

    if agency_id:
        # B2B: agency contact
        name = booking.get("agency_name") or f"Agency {agency_id}"
        external_id = f"{organization_id}:agency:{agency_id}"
        email = guest_email
        phone = guest.get("phone")
    else:
        # B2C: guest contact
        full_name = guest.get("full_name") or guest.get("name") or "Guest"
        name = full_name
        external_id = f"{organization_id}:guest:{booking.get('id') or booking.get('_id')}"
        email = guest_email
        phone = guest.get("phone")

    return ParasutContactInput(name=name, external_id=str(external_id), email=email, phone=phone)


def build_invoice_input(
    organization_id: str,
    booking: dict[str, Any],
    contact_id: str,
) -> ParasutInvoiceInput:
    """Build ParasutInvoiceInput from booking + contact id."""

    amount, currency = _extract_amount_and_currency(booking)

    # Prefer paid_at or status_date fields; fallback to created_at or today
    issue_dt: Optional[date] = None
    for key in ("paid_at", "status_date", "confirmed_at", "created_at"):
        val = booking.get(key)
        if getattr(val, "date", None):
            issue_dt = val.date()
            break
    if issue_dt is None:
        issue_dt = now_utc().date()

    booking_id = booking.get("id") or booking.get("_id")
    external_id = f"{organization_id}:booking:{booking_id}"

    booking_code = booking.get("code") or booking.get("booking_code") or str(booking_id)
    description = f"Booking {booking_code}"

    return ParasutInvoiceInput(
        contact_id=contact_id,
        external_id=str(external_id),
        issue_date=issue_dt,
        currency=str(currency),
        amount=amount,
        description=description,
    )


async def run_parasut_invoice_push(
    db,
    *,
    organization_id: str,
    booking_id: str,
    client: Optional[ParasutClient] = None,
) -> dict[str, Any]:
    """Idempotent Paraşüt invoice push for a single booking (MVP).

    Behaviour:
    - Uses ParasutPushLogService for idempotency.
    - If a log row exists with status=success -> returns {status:"skipped", ...}.
    - Otherwise resolves booking, builds contact & invoice, delegates to client
      (MockParasutClient by default) and updates log success/failed.
    """

    log_service = ParasutPushLogService(db)

    # 1) Look up or create log row
    log_entry = await log_service.get_or_create_pending(
        organization_id=organization_id,
        booking_id=booking_id,
        push_type="invoice_v1",
    )

    status = log_entry.get("status")
    if status == "success":
        # Already pushed successfully; do not create another invoice
        return {
            "status": "skipped",
            "log_id": str(log_entry.get("_id")),
            "parasut_contact_id": log_entry.get("parasut_contact_id"),
            "parasut_invoice_id": log_entry.get("parasut_invoice_id"),
        }

    # 2) Resolve booking
    try:
        oid = ObjectId(booking_id)
        booking = await db.bookings.find_one({"_id": oid, "organization_id": organization_id})
    except Exception:  # pragma: no cover - defensive
        booking = None

    if not booking:
        await log_service.mark_failed(log_id=log_entry["_id"], error="booking_not_found")
        return {
            "status": "failed",
            "reason": "booking_not_found",
            "log_id": str(log_entry.get("_id")),
        }

    # 3) Build contact + invoice payloads
    try:
        contact_input = build_contact_input(organization_id, booking)
        amount, currency = _extract_amount_and_currency(booking)
        invoice_input = build_invoice_input(organization_id, booking, contact_id="pending")
        # overwrite amount/currency in case build_* logic changes later
        invoice_input.amount = amount
        invoice_input.currency = currency
    except ValueError as exc:
        await log_service.mark_failed(log_id=log_entry["_id"], error=str(exc))
        return {
            "status": "failed",
            "reason": str(exc),
            "log_id": str(log_entry.get("_id")),
        }

    # 4) Delegate to client (mock by default)
    client = client or get_parasut_client(mode="mock")

    try:
        contact_id = await client.upsert_contact(contact_input)
        invoice_input.contact_id = contact_id
        invoice_id = await client.create_invoice(invoice_input)
    except Exception as exc:  # pragma: no cover - network / client errors
        await log_service.mark_failed(log_id=log_entry["_id"], error=f"client_error:{exc}")
        return {
            "status": "failed",
            "reason": f"client_error:{exc}",
            "log_id": str(log_entry.get("_id")),
        }

    # 5) Mark success in log
    await log_service.mark_success(
        log_id=log_entry["_id"],
        parasut_contact_id=contact_id,
        parasut_invoice_id=invoice_id,
    )

    return {
        "status": "success",
        "log_id": str(log_entry.get("_id")),
        "parasut_contact_id": contact_id,
        "parasut_invoice_id": invoice_id,
        "contact": asdict(contact_input),
        "invoice": asdict(invoice_input),
    }
