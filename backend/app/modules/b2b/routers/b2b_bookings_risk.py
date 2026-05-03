"""B2B booking risk-review routers (T009 / Task #3).

Extracted from `b2b_bookings.py`.

Owns:
- POST /api/b2b/bookings/{id}/risk/approve  (approve_risk_review_booking)
- POST /api/b2b/bookings/{id}/risk/reject   (reject_risk_review_booking)

External contract preserved exactly.
"""
from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, Request

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.services.audit import write_audit_log
from app.services.booking_lifecycle import BookingLifecycleService
from app.utils import now_utc

router = APIRouter(prefix="/api/b2b", tags=["b2b-bookings"])


@router.post(
    "/bookings/{booking_id}/risk/approve",
    dependencies=[Depends(require_roles(["agency_admin"]))],
)
async def approve_risk_review_booking(
    booking_id: str,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Approve a booking currently in RISK_REVIEW state (PR-19.1).

    - Transitions status from RISK_REVIEW -> PENDING
    - Adds risk.review snapshot with state="approved"
    - Emits RISK_REVIEW_APPROVED audit (and optional lifecycle event)
    """

    org_id = user.get("organization_id")

    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "BOOKING_NOT_FOUND", "BOOKING_NOT_FOUND")

    booking = await db.bookings.find_one({"_id": oid, "organization_id": org_id})
    if not booking:
        raise AppError(404, "BOOKING_NOT_FOUND", "BOOKING_NOT_FOUND")

    status_val = booking.get("status")
    if status_val != "RISK_REVIEW":
        raise AppError(
            409,
            "RISK_REVIEW_NOT_REQUIRED",
            "Booking is not in RISK_REVIEW state.",
            details={"status": status_val},
        )

    now = now_utc()
    risk_block = booking.get("risk") or {}
    review_block = {
        "state": "approved",
        "reason": None,
        "by": user.get("email"),
        "at": now,
    }
    risk_block["review"] = review_block

    await db.bookings.update_one(
        {"_id": oid, "organization_id": org_id},
        {"$set": {"status": "PENDING", "risk": risk_block, "updated_at": now}},
    )

    actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
    buyer_tenant_id = (booking.get("offer_ref") or {}).get("buyer_tenant_id")
    await write_audit_log(
        db,
        organization_id=org_id,
        actor=actor,
        request=request,
        action="RISK_REVIEW_APPROVED",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after=None,
        meta={
            "booking_id": booking_id,
            "organization_id": org_id,
            "buyer_tenant_id": buyer_tenant_id,
            "previous_status": "RISK_REVIEW",
            "new_status": "PENDING",
            "review_state": "approved",
            "risk_score": risk_block.get("score"),
            "model_version": risk_block.get("model_version"),
        },
    )

    # Optional: lifecycle event for ops visibility
    lifecycle = BookingLifecycleService(db)
    await lifecycle.append_event(
        organization_id=org_id,
        agency_id=booking.get("agency_id") or "",
        booking_id=booking_id,
        event="RISK_REVIEW_APPROVED",
        request_id=None,
        before={"status": status_val},
        after={"status": "PENDING"},
        meta={"review_state": "approved", "by": user.get("email")},
    )

    return {"ok": True, "booking_id": booking_id, "status": "PENDING"}


@router.post(
    "/bookings/{booking_id}/risk/reject",
    dependencies=[Depends(require_roles(["agency_admin"]))],
)
async def reject_risk_review_booking(
    booking_id: str,
    payload: dict | None,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Reject a booking currently in RISK_REVIEW state (PR-19.1).

    - Transitions status from RISK_REVIEW -> RISK_REJECTED
    - Adds risk.review snapshot with state="rejected" and optional reason
    - Emits RISK_REVIEW_REJECTED audit (and optional lifecycle event)
    """

    org_id = user.get("organization_id")

    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "BOOKING_NOT_FOUND", "BOOKING_NOT_FOUND")

    booking = await db.bookings.find_one({"_id": oid, "organization_id": org_id})
    if not booking:
        raise AppError(404, "BOOKING_NOT_FOUND", "BOOKING_NOT_FOUND")

    status_val = booking.get("status")
    if status_val != "RISK_REVIEW":
        raise AppError(
            409,
            "RISK_REVIEW_NOT_REQUIRED",
            "Booking is not in RISK_REVIEW state.",
            details={"status": status_val},
        )

    reason = None
    if payload is not None:
        raw_reason = str(payload.get("reason") or "").strip()
        if raw_reason:
            reason = raw_reason[:200]

    now = now_utc()
    risk_block = booking.get("risk") or {}
    review_block = {
        "state": "rejected",
        "reason": reason,
        "by": user.get("email"),
        "at": now,
    }
    risk_block["review"] = review_block

    await db.bookings.update_one(
        {"_id": oid, "organization_id": org_id},
        {"$set": {"status": "RISK_REJECTED", "risk": risk_block, "updated_at": now}},
    )

    actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
    buyer_tenant_id = (booking.get("offer_ref") or {}).get("buyer_tenant_id")
    await write_audit_log(
        db,
        organization_id=org_id,
        actor=actor,
        request=request,
        action="RISK_REVIEW_REJECTED",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after=None,
        meta={
            "booking_id": booking_id,
            "organization_id": org_id,
            "buyer_tenant_id": buyer_tenant_id,
            "previous_status": "RISK_REVIEW",
            "new_status": "RISK_REJECTED",
            "review_state": "rejected",
            "review_reason": reason,
            "risk_score": risk_block.get("score"),
            "model_version": risk_block.get("model_version"),
        },
    )

    lifecycle = BookingLifecycleService(db)
    await lifecycle.append_event(
        organization_id=org_id,
        agency_id=booking.get("agency_id") or "",
        booking_id=booking_id,
        event="RISK_REVIEW_REJECTED",
        request_id=None,
        before={"status": status_val},
        after={"status": "RISK_REJECTED"},
        meta={"review_state": "rejected", "by": user.get("email"), "reason": reason},
    )

    return {"ok": True, "booking_id": booking_id, "status": "RISK_REJECTED"}
