from __future__ import annotations

from typing import Any, Dict, List

from bson import ObjectId
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.schemas_vouchers import (
    VoucherGenerateResponse,
    VoucherHistoryItem,
    VoucherHistoryResponse,
    VoucherResendRequest,
    VoucherResendResponse,
)
from app.services.vouchers import (
    append_delivery_log,
    generate_for_booking,
    list_vouchers_for_booking,
    render_voucher_html,
)


router = APIRouter(tags=["vouchers"])


OpsUserDep = Depends(require_roles(["admin", "ops", "super_admin"]))


@router.post("/api/ops/bookings/{booking_id}/voucher/generate", response_model=VoucherGenerateResponse)
async def ops_generate_voucher_for_booking(
    booking_id: str,
    user=OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user["organization_id"]
    created_by_email = user.get("email")
    return await generate_for_booking(db, org_id, booking_id, created_by_email)


@router.get("/api/ops/bookings/{booking_id}/vouchers", response_model=VoucherHistoryResponse)
async def ops_list_vouchers_for_booking(
    booking_id: str,
    user=OpsUserDep,
    db=Depends(get_db),
) -> VoucherHistoryResponse:
    org_id = user["organization_id"]
    docs = await list_vouchers_for_booking(db, org_id, booking_id)

    items: List[VoucherHistoryItem] = []
    for doc in docs:
        items.append(
            VoucherHistoryItem(
                voucher_id=str(doc.get("_id")),
                version=int(doc.get("version", 0) or 0),
                status=str(doc.get("status") or ""),
                created_at=doc.get("created_at"),
                created_by_email=doc.get("created_by_email"),
            )
        )

    return VoucherHistoryResponse(items=items)


@router.post("/api/ops/bookings/{booking_id}/voucher/resend", response_model=VoucherResendResponse)
async def ops_resend_voucher(
    booking_id: str,
    payload: VoucherResendRequest,
    user=OpsUserDep,
    db=Depends(get_db),
) -> VoucherResendResponse:
    org_id = user["organization_id"]

    # Ensure there is an active voucher
    docs = await list_vouchers_for_booking(db, org_id, booking_id)
    active = next((d for d in docs if d.get("status") == "active"), None)
    if not active:
        raise AppError(404, "voucher_not_found", "No active voucher for this booking", {"booking_id": booking_id})

    voucher_id = str(active.get("_id"))

    await append_delivery_log(
        db,
        organization_id=org_id,
        booking_id=booking_id,
        voucher_id=voucher_id,
        to_email=payload.to_email,
        by_email=user.get("email"),
        message=payload.message,
    )

    # Phase 1: we only log delivery, real email sending is handled elsewhere
    return VoucherResendResponse(voucher_id=voucher_id, status="queued")


@router.get("/api/b2b/bookings/{booking_id}/voucher", response_class=HTMLResponse)
async def b2b_view_voucher_html(
    booking_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Return active voucher HTML for agency-scoped booking."""

    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not org_id or not agency_id:
        raise AppError(403, "forbidden", "Only agency users can view vouchers")

    # Ensure booking belongs to this agency
    try:
        booking_oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

    booking = await db.bookings.find_one({"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id})
    if not booking:
        raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

    html = await render_voucher_html(db, org_id, booking_id)
    return HTMLResponse(content=html)


@router.get("/api/b2b/bookings/{booking_id}/voucher.pdf")
async def b2b_download_voucher_pdf(
    booking_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> Response:
    """Return voucher PDF for agency-scoped booking.

    Phase 1: PDF rendering not configured; raise AppError(501, pdf_not_configured).
    """

    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not org_id or not agency_id:
        raise AppError(403, "forbidden", "Only agency users can view vouchers")

    # Ensure booking belongs to this agency (even if we error afterwards)
    try:
        booking_oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

    booking = await db.bookings.find_one({"_id": booking_oid, "organization_id": org_id, "agency_id": agency_id})
    if not booking:
        raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

    # Phase 1: always raise configured error
    from app.services.vouchers import render_voucher_pdf  # noqa: WPS433

    # This will always raise AppError(501, pdf_not_configured, ...)
    await render_voucher_pdf(db, org_id, booking_id)

    # Unreachable, but keeps type checkers happy
    return Response(status_code=501)

