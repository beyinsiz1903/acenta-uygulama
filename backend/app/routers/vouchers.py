from __future__ import annotations

from typing import Any, Dict, List

from bson import ObjectId
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

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
from app.services.voucher_pdf import issue_voucher_pdf, get_latest_voucher_pdf


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


class VoucherIssueRequest(BaseModel):
    issue_reason: str = "INITIAL"  # INITIAL | AMEND | CANCEL
    locale: str = "tr"


class VoucherFileMeta(BaseModel):
    id: str
    booking_id: str
    version: int
    issue_reason: str
    locale: str
    filename: str
    mime: str
    size_bytes: int
    created_at: datetime | None = None
    created_by: str | None = None


@router.post("/api/ops/bookings/{booking_id}/voucher/issue", response_model=VoucherFileMeta)
async def ops_issue_voucher_pdf(
    booking_id: str,
    payload: VoucherIssueRequest,
    user=OpsUserDep,
    db=Depends(get_db),
) -> VoucherFileMeta:
    """Issue a voucher PDF for a booking (ops/admin only).

    This builds on the existing voucher HTML (services.vouchers) and persists
    a binary PDF file in files_vouchers. It also emits a VOUCHER_ISSUED event
    that is visible on the booking timeline.
    """

    org_id = user["organization_id"]
    email = user.get("email") or "ops@system"

    # Normalize issue_reason
    issue_reason = (payload.issue_reason or "INITIAL").upper()
    if issue_reason not in {"INITIAL", "AMEND", "CANCEL"}:
        issue_reason = "INITIAL"

    meta = await issue_voucher_pdf(
        db,
        organization_id=org_id,
        booking_id=booking_id,
        issue_reason=issue_reason,  # type: ignore[arg-type]
        locale=payload.locale or "tr",
        issued_by=email,
    )

    return VoucherFileMeta(**meta)


@router.get("/api/b2b/bookings/{booking_id}/voucher/latest")
async def b2b_download_latest_voucher_pdf(
    booking_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> Response:
    """Download latest voucher PDF for a booking (agency/hotel/admin).

    For Phase 1 we allow any authenticated user scoped to the same
    organization, with booking-level ownership checks for agency/hotel roles.
    """

    org_id = user.get("organization_id")
    roles = set(user.get("roles") or [])
    if not org_id:
        raise AppError(403, "forbidden", "Missing organization context")

    # Ownership checks: agency/hotel users must own the booking
    try:
        booking_oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

    booking = await db.bookings.find_one({"_id": booking_oid, "organization_id": org_id})
    if not booking:
        raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

    if roles & {"agency_admin", "agency_agent"}:
        if str(booking.get("agency_id")) != str(user.get("agency_id")):
            raise AppError(403, "forbidden", "Booking does not belong to this agency")

    if roles & {"hotel_admin", "hotel_staff"}:
        if str(booking.get("hotel_id")) != str(user.get("hotel_id")):
            raise AppError(403, "forbidden", "Booking does not belong to this hotel")

    # Admin/ops users can access any booking within org

    pdf_bytes, meta = await get_latest_voucher_pdf(
        db,
        organization_id=org_id,
        booking_id=booking_id,
    )

    filename = meta.get("filename") or f"voucher-{booking_id}.pdf"
    headers = {
        "Content-Disposition": f"inline; filename=\"{filename}\"",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)



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


@router.get("/api/ops/bookings/{booking_id}/voucher", response_class=HTMLResponse)
async def ops_view_voucher_html(
    booking_id: str,
    user=OpsUserDep,
    db=Depends(get_db),
):
    """Return active voucher HTML for ops users (org-scoped)."""

    org_id = user["organization_id"]

    # Ensure booking exists within org
    try:
        booking_oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

    booking = await db.bookings.find_one({"_id": booking_oid, "organization_id": org_id})
    if not booking:
        raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

    html = await render_voucher_html(db, org_id, booking_id)
    return HTMLResponse(content=html)


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

    P0.4: render active voucher to PDF and stream bytes back to caller.
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

    from app.services.vouchers import render_voucher_pdf  # noqa: WPS433

    pdf_bytes = await render_voucher_pdf(db, org_id, booking_id)

    headers = {
        "Content-Disposition": f"inline; filename=\"voucher-{booking_id}.pdf\"",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

