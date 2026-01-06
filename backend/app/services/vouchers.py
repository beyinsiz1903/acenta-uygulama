from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId

from app.errors import AppError
from app.utils import now_utc
from app.services.booking_events import emit_event

import uuid


DEFAULT_TEMPLATE_KEY = "b2b_booking_default"


def _build_snapshot(booking: Dict[str, Any]) -> Dict[str, Any]:
    """Minimal immutable snapshot for voucher rendering.

    Keep this small and schema-agnostic for Phase 1.
    """

    customer = (booking.get("customer") or {})
    items = booking.get("items") or []

    # first item for simple template usage
    first_item = items[0] if items else {}

    return {
        "booking_id": str(booking.get("_id")),
        "status": booking.get("status"),
        "agency_id": booking.get("agency_id"),
        "channel_id": booking.get("channel_id"),
        "customer_name": customer.get("name"),
        "customer_email": customer.get("email"),
        "check_in": first_item.get("check_in"),
        "check_out": first_item.get("check_out"),
        "created_at": booking.get("created_at"),
        "currency": booking.get("currency"),
        "amount_sell": (booking.get("amounts") or {}).get("sell"),
    }


def _get_next_version(existing: list[Dict[str, Any]]) -> int:
    if not existing:
        return 1
    return max(int(doc.get("version", 0) or 0) for doc in existing) + 1


def _render_template_html(template_doc: Optional[Dict[str, Any]], snapshot: Dict[str, Any]) -> str:
    """Very small, safe-ish template renderer for Phase 1.

    Uses str.format with a constrained context.
    """

    context = {
        "booking_id": snapshot.get("booking_id", ""),
        "customer_name": snapshot.get("customer_name", ""),
        "customer_email": snapshot.get("customer_email", ""),
        "check_in": snapshot.get("check_in", ""),
        "check_out": snapshot.get("check_out", ""),
        "amount_sell": snapshot.get("amount_sell", ""),
        "currency": snapshot.get("currency", ""),
    }

    if template_doc and template_doc.get("html"):
        template = template_doc["html"]
    else:
        template = (
            "<html><body>"
            "<h1>Booking Voucher</h1>"
            "<p>Booking ID: {booking_id}</p>"
            "<p>Guest: {customer_name} ({customer_email})</p>"
            "<p>Dates: {check_in} → {check_out}</p>"
            "<p>Amount: {amount_sell} {currency}</p>"
            "</body></html>"
        )

    try:
        return template.format(**context)
    except Exception:
        # If formatting fails, fall back to plain snapshot dump
        return f"<html><body><pre>{snapshot}</pre></body></html>"


async def generate_for_booking(db, organization_id: str, booking_id: str, created_by_email: str) -> Dict[str, Any]:
    """Generate (or regenerate) a voucher for a booking with single-active rule."""

    try:
        booking_oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

    booking = await db.bookings.find_one({"_id": booking_oid, "organization_id": organization_id})
    if not booking:
        raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

    status = booking.get("status")
    if status not in {"CONFIRMED", "VOUCHERED", "COMPLETED"}:
        raise AppError(
            409,
            "invalid_booking_state",
            "Voucher can only be generated for CONFIRMED/VOUCHERED/COMPLETED bookings",
            {"booking_id": booking_id, "status": status},
        )

    now = now_utc()

    # Find existing vouchers for this booking
    existing = await db.vouchers.find({
        "organization_id": organization_id,
        "booking_id": booking_id,
    }).sort("version", -1).to_list(length=None)

    # Enforce single-active: void all existing active vouchers
    await db.vouchers.update_many(
        {
            "organization_id": organization_id,
            "booking_id": booking_id,
            "status": "active",
        },
        {"$set": {"status": "void", "updated_at": now}},
    )

    version = _get_next_version(existing)
    snapshot = _build_snapshot(booking)

    # Load template (if any)
    template = await db.voucher_templates.find_one(
        {"organization_id": organization_id, "key": DEFAULT_TEMPLATE_KEY, "status": "active"}
    )

    html = _render_template_html(template, snapshot)

    voucher_doc = {
        "organization_id": organization_id,
        "booking_id": booking_id,
        "version": version,
        "status": "active",
        "template_key": DEFAULT_TEMPLATE_KEY,
        "html": html,
        "data_snapshot": snapshot,
        "delivery_log": [],
        "created_at": now,
        "updated_at": now,
        "created_by_email": created_by_email,
    }

    res = await db.vouchers.insert_one(voucher_doc)
    voucher_id = str(res.inserted_id)

    # Update booking status to VOUCHERED (if it was not already)
    booking_status_before = booking.get("status")
    await db.bookings.update_one(
        {"_id": booking_oid, "organization_id": organization_id},
        {"$set": {"status": "VOUCHERED", "updated_at": now}},
    )

    # Emit voucher-related events
    actor = {"role": "ops", "email": created_by_email}
    await emit_event(
        db,
        organization_id,
        booking_id,
        "VOUCHER_GENERATED",
        actor=actor,
        meta={
            "voucher_id": voucher_id,
            "voucher_version": version,
            "template_key": DEFAULT_TEMPLATE_KEY,
        },
    )

    if booking_status_before != "VOUCHERED":
        await emit_event(
            db,
            organization_id,
            booking_id,
            "BOOKING_STATUS_CHANGED",
            actor=actor,
            meta={"status_from": booking_status_before, "status_to": "VOUCHERED"},
        )

    return {
        "booking_id": booking_id,
        "voucher_id": voucher_id,
        "version": version,
        "status": "active",
        "html_url": f"/api/b2b/bookings/{booking_id}/voucher",
        "pdf_url": f"/api/b2b/bookings/{booking_id}/voucher.pdf",
    }


async def get_active_voucher(db, organization_id: str, booking_id: str) -> Optional[Dict[str, Any]]:
    return await db.vouchers.find_one(
        {"organization_id": organization_id, "booking_id": booking_id, "status": "active"},
        sort=[("version", -1)],
    )


async def list_vouchers_for_booking(db, organization_id: str, booking_id: str) -> list[Dict[str, Any]]:
    docs = await db.vouchers.find(
        {"organization_id": organization_id, "booking_id": booking_id}
    ).sort("version", -1).to_list(length=None)
    return docs


async def append_delivery_log(
    db,
    organization_id: str,
    booking_id: str,
    voucher_id: str,
    to_email: str,
    by_email: str,
    message: Optional[str] = None,
) -> None:
    now = now_utc()
    try:
        oid = ObjectId(voucher_id)
    except Exception:
        return

    entry = {
        "to_email": to_email,
        "message": message,
        "status": "queued",
        "created_at": now,
        "created_by_email": by_email,
    }

    await db.vouchers.update_one(
        {"_id": oid, "organization_id": organization_id},
        {"$push": {"delivery_log": entry}, "$set": {"updated_at": now}},
    )


async def render_voucher_html(db, organization_id: str, booking_id: str) -> str:
    voucher = await get_active_voucher(db, organization_id, booking_id)
    if not voucher:
        raise AppError(404, "voucher_not_found", "No active voucher for this booking", {"booking_id": booking_id})

    # Prefer stored html if present, but also support re-rendering from snapshot/template
    if voucher.get("html"):
        return voucher["html"]

    snapshot = voucher.get("data_snapshot") or {}
    template = await db.voucher_templates.find_one(
        {"organization_id": organization_id, "key": voucher.get("template_key") or DEFAULT_TEMPLATE_KEY}
    )
    return _render_template_html(template, snapshot)


async def render_voucher_pdf(db, organization_id: str, booking_id: str) -> bytes:
    # Phase 1: PDF rendering not yet configured, always raise
    raise AppError(501, "pdf_not_configured", "PDF rendering not yet configured", {"booking_id": booking_id})

