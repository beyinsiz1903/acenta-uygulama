from __future__ import annotations

"""FAZ 1: Voucher PDF issuance & storage service.

This builds on top of the existing vouchers service (HTML-based) and adds:
- Binary PDF storage in files_vouchers collection
- VOUCHER_ISSUED booking_events
- Hooks for email outbox integration
"""

from typing import Any, Dict, Literal, Optional, Tuple
from datetime import datetime

from bson import ObjectId

from app.errors import AppError
from app.services.vouchers import render_voucher_html
from app.services.booking_events import emit_event
from app.utils import now_utc

IssueReason = Literal["INITIAL", "AMEND", "CANCEL"]


async def _ensure_booking(db, organization_id: str, booking_id: str) -> Dict[str, Any]:
    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    booking = await db.bookings.find_one({"_id": oid, "organization_id": organization_id}, {"_id": 0})
    if not booking:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})
    return booking


async def _compute_next_version(
    db,
    *,
    organization_id: str,
    booking_id: str,
) -> int:
    doc = await db.files_vouchers.find_one(
        {"organization_id": organization_id, "booking_id": booking_id},
        sort=[("version", -1)],
        projection={"version": 1, "_id": 0},
    )
    if not doc:
        return 1
    try:
        return int(doc.get("version", 0) or 0) + 1
    except Exception:
        return 1


async def _render_pdf_from_active_voucher(
    db,
    *,
    organization_id: str,
    booking_id: str,
) -> bytes:
    """Reuse existing active voucher HTML and render it to PDF bytes."""

    html = await render_voucher_html(db, organization_id, booking_id)

    try:
        from weasyprint import HTML  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise AppError(
            501,
            "pdf_not_configured",
            "PDF rendering backend is not available on this environment",
            {"booking_id": booking_id, "error": str(exc)},
        ) from exc

    try:
        pdf_bytes = HTML(string=html).write_pdf()
    except Exception as exc:  # pragma: no cover
        raise AppError(
            500,
            "pdf_render_failed",
            "Voucher PDF rendering failed",
            {"booking_id": booking_id, "error": str(exc)},
        ) from exc

    return pdf_bytes


async def issue_voucher_pdf(
    db,
    *,
    organization_id: str,
    booking_id: str,
    issue_reason: IssueReason,
    locale: str,
    issued_by: str,
) -> Dict[str, Any]:
    """Issue a voucher PDF for a booking and persist it.

    Idempotent per (org, booking_id, version, issue_reason) via unique index.
    For Phase 1 we simply increment version per booking; callers may choose
    issue_reason according to lifecycle (INITIAL / AMEND / CANCEL).
    """

    booking = await _ensure_booking(db, organization_id, booking_id)

    # Derive basic naming / metadata
    code = booking.get("code") or str(booking_id)
    now = now_utc()

    # Compute next version (per booking)
    version = await _compute_next_version(db, organization_id=organization_id, booking_id=booking_id)

    # Render PDF from existing active voucher HTML (services.vouchers)
    pdf_bytes = await _render_pdf_from_active_voucher(db, organization_id=organization_id, booking_id=booking_id)

    filename = f"voucher-{code}-v{version}-{issue_reason.lower()}.pdf"
    mime = "application/pdf"
    size_bytes = len(pdf_bytes)

    doc = {
        "organization_id": organization_id,
        "booking_id": booking_id,
        "version": version,
        "issue_reason": issue_reason,
        "locale": locale,
        "filename": filename,
        "mime": mime,
        "size_bytes": size_bytes,
        "created_at": now,
        "created_by": issued_by,
        "content": pdf_bytes,
    }

    # Insert with unique index; if a race happens, keep existing doc
    try:
        res = await db.files_vouchers.insert_one(doc)
        file_id = str(res.inserted_id)
    except Exception as exc:
        from pymongo.errors import DuplicateKeyError

        if isinstance(exc, DuplicateKeyError):  # pragma: no cover - rare
            existing = await db.files_vouchers.find_one(
                {
                    "organization_id": organization_id,
                    "booking_id": booking_id,
                    "version": version,
                    "issue_reason": issue_reason,
                },
                projection={"_id": 1},
            )
            if existing:
                file_id = str(existing["_id"])
            else:
                raise
        else:
            raise

    # Emit booking event for timeline
    await emit_event(
        db,
        organization_id,
        booking_id,
        "VOUCHER_ISSUED",
        actor={"role": "ops", "email": issued_by},
        meta={
            "version": version,
            "issue_reason": issue_reason,
            "file_id": file_id,
            "locale": locale,
        },
    )

    return {
        "id": file_id,
        "booking_id": booking_id,
        "version": version,
        "issue_reason": issue_reason,
        "locale": locale,
        "filename": filename,
        "mime": mime,
        "size_bytes": size_bytes,
        "created_at": now,
        "created_by": issued_by,
    }


async def get_latest_voucher_pdf(
    db,
    *,
    organization_id: str,
    booking_id: str,
) -> Tuple[bytes, Dict[str, Any]]:
    """Return latest voucher PDF bytes + metadata for a booking.

    If no file exists yet, this does **not** auto-create one; callers should
    explicitly call issue_voucher_pdf first. This keeps semantics clear.
    """

    doc = await db.files_vouchers.find_one(
        {"organization_id": organization_id, "booking_id": booking_id},
        sort=[("version", -1)],
    )
    if not doc:
        raise AppError(404, "voucher_not_found", "No voucher PDF for this booking", {"booking_id": booking_id})

    content = doc.get("content")
    if not isinstance(content, (bytes, bytearray)):
        raise AppError(
            500,
            "voucher_file_corrupt",
            "Stored voucher PDF content is missing or invalid",
            {"booking_id": booking_id},
        )

    meta = {
        "id": str(doc.get("_id")),
        "booking_id": booking_id,
        "version": int(doc.get("version", 0) or 0),
        "issue_reason": doc.get("issue_reason"),
        "locale": doc.get("locale"),
        "filename": doc.get("filename"),
        "mime": doc.get("mime"),
        "size_bytes": int(doc.get("size_bytes", 0) or 0),
        "created_at": doc.get("created_at"),
        "created_by": doc.get("created_by"),
    }

    return bytes(content), meta
