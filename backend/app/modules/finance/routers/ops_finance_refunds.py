"""Refund Cases Router — Decomposed from ops_finance.py.

Handles: refund CRUD, approve step1/step2, mark-paid, close, reject.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, Query, Request
from typing import Optional

from bson import ObjectId

from app.db import get_db
from app.auth import require_roles
from app.errors import AppError
from app.services.refund_cases import RefundCaseService
from app.services.booking_events import emit_event
from app.services.ops_playbook import OpsPlaybookEngine
from app.services.audit import write_audit_log, audit_snapshot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ops/finance", tags=["ops_finance_refunds"])


def _actor(user):
    return {
        "actor_type": "user",
        "actor_id": user.get("id") or user.get("email"),
        "email": user.get("email"),
        "roles": user.get("roles") or [],
    }


@router.get("/refunds")
async def list_refunds(
    status: Optional[str] = Query(None),
    booking_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    svc = RefundCaseService(db)
    return await svc.list_refunds(current_user["organization_id"], status, limit, booking_id)


@router.post("/refunds")
async def create_refund_case(
    payload: dict,
    request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    booking_id = payload.get("booking_id")
    if not booking_id:
        raise AppError(422, "validation_error", "booking_id is required")
    booking = await db.bookings.find_one({"_id": ObjectId(booking_id), "organization_id": org_id})
    if not booking:
        raise AppError(404, "booking_not_found", "Booking not found")
    agency_id = booking.get("agency_id", "default_agency")
    svc = RefundCaseService(db)
    result = await svc.create_refund_request(
        organization_id=org_id, booking_id=booking_id, agency_id=agency_id,
        requested_amount=payload.get("requested_amount"),
        requested_message=payload.get("customer_note"),
        reason=payload.get("reason", "Customer request"),
        created_by=current_user.get("email", "admin"),
    )
    try:
        engine = OpsPlaybookEngine(db)
        await engine.on_refund_created(org_id, case_id=result["case_id"], booking_id=booking_id, actor_email=current_user.get("email"), actor_id=current_user.get("id"))
    except Exception:
        logger.exception("ops_playbook_refund_created_failed")
    return result


@router.get("/refunds/{case_id}")
async def get_refund_case(
    case_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    svc = RefundCaseService(db)
    return await svc.get_case(current_user["organization_id"], case_id)


@router.post("/refunds/{case_id}/approve")
async def approve_refund_case(
    case_id: str, payload: dict, request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    approved_amount = float(payload.get("approved_amount") or 0.0)
    svc = RefundCaseService(db)
    existing = await svc.get_case(org_id, case_id)
    if not existing:
        raise AppError(404, "refund_case_not_found", "Refund case not found")
    status = existing.get("status")
    booking_id = existing.get("booking_id")
    if status not in {"open", "pending_approval", "pending_approval_1", "pending_approval_2"}:
        raise AppError(409, "invalid_case_state", "Refund case is not open for approval")
    actor = _actor(current_user)
    if status in {"open", "pending_approval", "pending_approval_1"}:
        result_step1 = await svc.approve_step1(organization_id=org_id, case_id=case_id, approved_amount=approved_amount, actor_email=current_user["email"], actor_id=current_user.get("id"))
        try:
            await write_audit_log(db, organization_id=org_id, actor=actor, request=request, action="refund_approve_step1", target_type="refund_case", target_id=case_id, before=audit_snapshot("refund_case", existing), after=audit_snapshot("refund_case", result_step1), meta={"approved_amount": approved_amount, "via": "compat"})
            if booking_id:
                await emit_event(db, organization_id=org_id, booking_id=booking_id, type="REFUND_APPROVED_STEP1", actor={"email": current_user.get("email"), "actor_id": current_user.get("id"), "roles": current_user.get("roles") or []}, meta={"case_id": case_id, "approved_amount": approved_amount, "via": "compat"})
        except Exception:
            pass
        existing = result_step1
        status = result_step1.get("status")
    result = await svc.approve_step2(organization_id=org_id, case_id=case_id, actor_email=current_user["email"], actor_id=current_user.get("id"), note=payload.get("note"))
    try:
        await write_audit_log(db, organization_id=org_id, actor=actor, request=request, action="refund_approve_step2", target_type="refund_case", target_id=case_id, before=audit_snapshot("refund_case", existing), after=audit_snapshot("refund_case", result), meta={"note": payload.get("note"), "via": "compat"})
        if booking_id:
            await emit_event(db, organization_id=org_id, booking_id=booking_id, type="REFUND_APPROVED_STEP2", actor={"email": current_user.get("email"), "actor_id": current_user.get("id"), "roles": current_user.get("roles") or []}, meta={"case_id": case_id, "via": "compat"})
    except Exception:
        pass
    return result


@router.post("/refunds/{case_id}/approve-step1")
async def approve_refund_step1(
    case_id: str, payload: dict, request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    approved_amount = float(payload.get("approved_amount") or 0.0)
    svc = RefundCaseService(db)
    existing = await svc.get_case(org_id, case_id)
    result = await svc.approve_step1(organization_id=org_id, case_id=case_id, approved_amount=approved_amount, actor_email=current_user["email"], actor_id=current_user.get("id"))
    try:
        await write_audit_log(db, organization_id=org_id, actor=_actor(current_user), request=request, action="refund_approve_step1", target_type="refund_case", target_id=case_id, before=audit_snapshot("refund_case", existing), after=audit_snapshot("refund_case", result), meta={"approved_amount": approved_amount})
        booking_id = result.get("booking_id")
        if booking_id:
            await emit_event(db, organization_id=org_id, booking_id=booking_id, type="REFUND_APPROVED_STEP1", actor={"email": current_user.get("email"), "actor_id": current_user.get("id"), "roles": current_user.get("roles") or []}, meta={"case_id": case_id, "approved_amount": approved_amount})
        engine = OpsPlaybookEngine(db)
        await engine.on_refund_step1(org_id, case_id=case_id, booking_id=booking_id, actor_email=current_user.get("email"), actor_id=current_user.get("id"))
    except Exception:
        pass
    return result


@router.post("/refunds/{case_id}/approve-step2")
async def approve_refund_step2(
    case_id: str, payload: dict, request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    note = payload.get("note")
    svc = RefundCaseService(db)
    existing = await svc.get_case(org_id, case_id)
    result = await svc.approve_step2(organization_id=org_id, case_id=case_id, actor_email=current_user["email"], actor_id=current_user.get("id"), note=note)
    try:
        await write_audit_log(db, organization_id=org_id, actor=_actor(current_user), request=request, action="refund_approve_step2", target_type="refund_case", target_id=case_id, before=audit_snapshot("refund_case", existing), after=audit_snapshot("refund_case", result), meta={"note": note})
        booking_id = result.get("booking_id")
        if booking_id:
            await emit_event(db, organization_id=org_id, booking_id=booking_id, type="REFUND_APPROVED_STEP2", actor={"email": current_user.get("email"), "actor_id": current_user.get("id"), "roles": current_user.get("roles") or []}, meta={"case_id": case_id, "note": note})
        engine = OpsPlaybookEngine(db)
        await engine.on_refund_step2(org_id, case_id=case_id, booking_id=booking_id, actor_email=current_user.get("email"), actor_id=current_user.get("id"))
    except Exception:
        pass
    return result


@router.post("/refunds/{case_id}/mark-paid")
async def mark_refund_paid(
    case_id: str, payload: dict, request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    payment_reference = (payload.get("payment_reference") or "").strip()
    svc = RefundCaseService(db)
    existing = await svc.get_case(org_id, case_id)
    result = await svc.mark_paid(organization_id=org_id, case_id=case_id, payment_reference=payment_reference, actor_email=current_user["email"], actor_id=current_user.get("id"))
    try:
        await write_audit_log(db, organization_id=org_id, actor=_actor(current_user), request=request, action="refund_mark_paid", target_type="refund_case", target_id=case_id, before=audit_snapshot("refund_case", existing), after=audit_snapshot("refund_case", result), meta={"payment_reference": payment_reference})
        booking_id = result.get("booking_id")
        if booking_id:
            await emit_event(db, organization_id=org_id, booking_id=booking_id, type="REFUND_MARKED_PAID", actor={"email": current_user.get("email"), "actor_id": current_user.get("id"), "roles": current_user.get("roles") or []}, meta={"refund_case_id": case_id, "payment_reference": payment_reference})
        engine = OpsPlaybookEngine(db)
        await engine.on_refund_marked_paid(org_id, case_id=case_id, booking_id=booking_id, actor_email=current_user.get("email"), actor_id=current_user.get("id"))
    except Exception:
        pass
    return result


@router.post("/refunds/{case_id}/close")
async def close_refund_case(
    case_id: str, payload: dict, request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    note = payload.get("note")
    svc = RefundCaseService(db)
    existing = await svc.get_case(org_id, case_id)
    result = await svc.close_case(organization_id=org_id, case_id=case_id, actor_email=current_user["email"], actor_id=current_user.get("id"), note=note)
    try:
        await write_audit_log(db, organization_id=org_id, actor=_actor(current_user), request=request, action="refund_close", target_type="refund_case", target_id=case_id, before=audit_snapshot("refund_case", existing), after=audit_snapshot("refund_case", result), meta={"note": note})
        booking_id = result.get("booking_id")
        if booking_id:
            await emit_event(db, organization_id=org_id, booking_id=booking_id, type="REFUND_CLOSED", actor={"email": current_user.get("email"), "actor_id": current_user.get("id"), "roles": current_user.get("roles") or []}, meta={"refund_case_id": case_id, "note": note})
        engine = OpsPlaybookEngine(db)
        await engine.on_refund_closed(org_id, case_id=case_id, booking_id=booking_id, actor_email=current_user.get("email"), actor_id=current_user.get("id"))
    except Exception:
        pass
    return result


@router.post("/refunds/{case_id}/reject")
async def reject_refund_case(
    case_id: str, payload: dict, request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    reason = payload.get("reason")
    svc = RefundCaseService(db)
    existing = await svc.get_case(org_id, case_id)
    await svc.reject(organization_id=org_id, case_id=case_id, decided_by=current_user["email"], reason=reason)
    saved = await svc.get_case(org_id, case_id)
    try:
        await write_audit_log(db, organization_id=org_id, actor=_actor(current_user), request=request, action="refund_reject", target_type="refund_case", target_id=case_id, before=audit_snapshot("refund_case", existing), after=audit_snapshot("refund_case", saved), meta={"reason": reason})
        booking_id = saved.get("booking_id") if saved else None
        if booking_id:
            await emit_event(db, organization_id=org_id, booking_id=booking_id, type="REFUND_REJECTED", actor={"email": current_user.get("email"), "actor_id": current_user.get("id"), "roles": current_user.get("roles") or []}, meta={"case_id": case_id, "reason": reason})
        engine = OpsPlaybookEngine(db)
        await engine.on_refund_rejected(org_id, case_id=case_id, booking_id=booking_id, actor_email=current_user.get("email"), actor_id=current_user.get("id"))
    except Exception as e:
        logger.warning("audit_write_failed refund_reject case_id=%s err=%s", case_id, str(e))
    return saved
