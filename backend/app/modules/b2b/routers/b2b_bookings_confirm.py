"""B2B booking confirmation router (T009 / Task #3).

Extracted from `b2b_bookings.py` to keep each file under ~600 LOC.

Owns:
- POST /api/b2b/bookings/{booking_id}/confirm  (confirm_b2b_booking)

External contract (URL paths, request/response shapes, status codes,
audit log entries, lifecycle event emissions, supplier interaction order)
is preserved bit-for-bit.
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Depends, Request

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.services.audit import write_audit_log
from app.services.booking_lifecycle import BookingLifecycleService
from app.services.credit_exposure_service import has_available_credit
from app.services.suppliers.contracts import (
    ConfirmStatus,
    SupplierAdapterError,
    SupplierContext,
    run_with_deadline,
)
from app.services.suppliers.redaction import redact_sensitive_fields
from app.services.suppliers.registry import registry as supplier_registry
from app.utils import now_utc

router = APIRouter(prefix="/api/b2b", tags=["b2b-bookings"])


@router.post(
    "/bookings/{booking_id}/confirm",
    dependencies=[Depends(require_roles(["agency_agent", "agency_admin", "super_admin"]))],
)
async def confirm_b2b_booking(
    booking_id: str,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Confirm a draft B2B booking via supplier fulfilment (v1).

    Behaviour:
    - 404 BOOKING_NOT_FOUND if booking does not exist
    - If booking.status == CONFIRMED -> 200 idempotent response
    - If booking.status is anything else than PENDING (legacy) -> 422 BOOKING_NOT_CONFIRMABLE
    - For marketplace bookings (source == b2b_marketplace):
      - Requires tenant context (X-Tenant-Key)
      - buyer_tenant_id in offer_ref must match request.state.tenant_id
    - Requires offer_ref.supplier and offer_ref.supplier_offer_id; otherwise
      422 INVALID_SUPPLIER_MAPPING
    - On successful supplier fulfilment, appends BOOKING_CONFIRMED lifecycle
      event and emits B2B_BOOKING_CONFIRMED audit log.
    """

    org_id = user.get("organization_id")
    # agency_id is optional for v1; fall back to booking.agency_id if present

    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "BOOKING_NOT_FOUND", "BOOKING_NOT_FOUND")

    booking = await db.bookings.find_one({"_id": oid, "organization_id": org_id})
    if not booking:
        raise AppError(404, "BOOKING_NOT_FOUND", "BOOKING_NOT_FOUND")

    status_val = booking.get("status")
    if status_val == "RISK_REVIEW":
        raise AppError(
            409,
            "risk_review_required",
            "Booking is in RISK_REVIEW state and requires manual review.",
            details={"status": "RISK_REVIEW"},
        )

    if status_val == "RISK_REJECTED":
        raise AppError(
            409,
            "risk_rejected",
            "Booking was rejected by risk review.",
            details={"status": "RISK_REJECTED"},
        )

    if status_val == "CONFIRMED":
        # Idempotent confirm when projection is already CONFIRMED.
        # Ensure at least one BOOKING_CONFIRMED lifecycle event + audit exists,
        # but do not create duplicates on repeated calls.
        existing_event = await db.booking_events.find_one(
            {"organization_id": org_id, "booking_id": booking_id, "event": "BOOKING_CONFIRMED"}
        )
        existing_audit = await db.audit_logs.find_one(
            {
                "organization_id": org_id,
                "action": "B2B_BOOKING_CONFIRMED",
                "target.id": booking_id,
            }
        )
        if not existing_event or not existing_audit:
            attempt_id = str(uuid4())
            source = booking.get("source")
            offer_ref = (booking.get("offer_ref") or {})
            supplier_name = (offer_ref.get("supplier") or "").strip()
            supplier_offer_id = (offer_ref.get("supplier_offer_id") or "").strip()

            lifecycle = BookingLifecycleService(db)
            await lifecycle.append_event(
                organization_id=org_id,
                agency_id=booking.get("agency_id") or "",
                booking_id=booking_id,
                event="BOOKING_CONFIRMED",
                request_id=attempt_id,
                before={"status": status_val},
                after={"status": "CONFIRMED"},
                meta={
                    "source": source,
                    "supplier": supplier_name,
                    "supplier_offer_id": supplier_offer_id,
                },
            )

            actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
            meta = {
                "source": "supplier_fulfilment",
                "supplier": supplier_name,
                "supplier_offer_id": supplier_offer_id,
                "tenant_id": offer_ref.get("buyer_tenant_id"),
                "attempt_id": attempt_id,
            }
            await write_audit_log(
                db,
                organization_id=org_id,
                actor=actor,
                request=request,
                action="B2B_BOOKING_CONFIRMED",
                target_type="booking",
                target_id=booking_id,
                before=None,
                after=None,
                meta=meta,
            )

        return {"booking_id": booking_id, "state": "confirmed"}

    if status_val not in {None, "PENDING"}:
        raise AppError(
            422,
            "BOOKING_NOT_CONFIRMABLE",
            "Booking is not in a confirmable state",
            details={"reason": "invalid_state", "status": status_val},
        )

    source = booking.get("source")
    offer_ref = (booking.get("offer_ref") or {})

    # Tenant context guard for marketplace
    if source == "b2b_marketplace":
        buyer_tenant_id = offer_ref.get("buyer_tenant_id")
        req_tenant_id = getattr(request.state, "tenant_id", None)
        if not req_tenant_id:
            raise AppError(403, "TENANT_CONTEXT_REQUIRED", "TENANT_CONTEXT_REQUIRED")
        if buyer_tenant_id and req_tenant_id != buyer_tenant_id:
            raise AppError(
                422,
                "BOOKING_NOT_CONFIRMABLE",
                "Booking tenant does not match current tenant context",
                details={"reason": "invalid_state"},
            )

    # Credit limit / exposure guard
    amount = float(booking.get("amount") or 0.0)
    if amount > 0:
        has_credit = await has_available_credit(db, organization_id=org_id, amount=amount)
        if not has_credit:
            raise AppError(
                409,
                "credit_limit_exceeded",
                "Credit limit exceeded for this organization.",
                details={"amount": amount},
            )

    # Risk engine (PR-19): evaluate booking risk before supplier fulfilment
    from app.services.risk.engine import RiskDecision, evaluate_booking_risk

    risk_result = await evaluate_booking_risk(db, organization_id=org_id, booking=booking)

    # Always emit RISK_EVALUATED audit
    actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
    buyer_tenant_id = (booking.get("offer_ref") or {}).get("buyer_tenant_id")
    await write_audit_log(
        db,
        organization_id=org_id,
        actor=actor,
        request=request,
        action="RISK_EVALUATED",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after=None,
        meta={
            "booking_id": booking_id,
            "organization_id": org_id,
            "buyer_tenant_id": buyer_tenant_id,
            "amount": amount,
            "score": float(risk_result.score),
            "decision": risk_result.decision.value,
            "reasons": list(risk_result.reasons),
            "model_version": risk_result.model_version,
        },
    )

    # Persist risk snapshot on booking for non-allow decisions
    risk_snapshot = {
        "score": float(risk_result.score),
        "decision": risk_result.decision.value,
        "reasons": list(risk_result.reasons),
        "model_version": risk_result.model_version,
    }

    if risk_result.decision is RiskDecision.BLOCK:
        # Store risk info but do not change booking state
        await db.bookings.update_one(
            {"_id": oid, "organization_id": org_id},
            {"$set": {"risk": risk_snapshot, "updated_at": now_utc()}},
        )

        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="RISK_BLOCKED",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "booking_id": booking_id,
                "score": float(risk_result.score),
                "decision": "block",
            },
        )

        raise AppError(
            409,
            "risk_blocked",
            "Booking confirmation blocked by risk engine.",
            details={"score": float(risk_result.score), "decision": "block"},
        )

    if risk_result.decision is RiskDecision.REVIEW:
        # Set booking.status to RISK_REVIEW and persist risk snapshot
        await db.bookings.update_one(
            {"_id": oid, "organization_id": org_id},
            {"$set": {"status": "RISK_REVIEW", "risk": risk_snapshot, "updated_at": now_utc()}},
        )

        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="RISK_REVIEW_REQUIRED",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "booking_id": booking_id,
                "score": float(risk_result.score),
                "decision": "review",
            },
        )

        # Best-effort ops incident for manual risk review
        try:
            from app.services.ops_incidents_service import create_risk_review_incident

            await create_risk_review_incident(
                db,
                organization_id=org_id,
                booking_id=booking_id,
                risk_score=float(risk_result.score),
                tenant_id=buyer_tenant_id,
                amount=amount,
                currency=booking.get("currency") or "",
            )
        except Exception:
            pass

        # 202 with standard error envelope
        raise AppError(
            202,
            "risk_review_required",
            "Booking requires manual risk review.",
            details={"score": float(risk_result.score), "decision": "review"},
        )

    # Supplier resolution
    supplier_name = (offer_ref.get("supplier") or "").strip()
    supplier_offer_id = (offer_ref.get("supplier_offer_id") or "").strip()

    # Fallback: use booking.supplier.code if present
    supplier_doc = booking.get("supplier") or {}
    if not supplier_name:
        supplier_name = (supplier_doc.get("code") or "").strip()
        supplier_offer_id = supplier_offer_id or (supplier_doc.get("offer_id") or "").strip()

    # TODO v2: if still missing, try supplier_mapping via listing_id

    if not supplier_name:
        raise AppError(
            422,
            "INVALID_SUPPLIER_MAPPING",
            "Missing supplier on offer_ref for fulfilment",
            details={"reason": "missing_supplier"},
        )

    # Resolve adapter via registry (with alias support)
    try:
        adapter = supplier_registry.get(supplier_name)
    except SupplierAdapterError as exc:
        # adapter_not_found and similar registry-level errors
        raise AppError(
            502,
            "adapter_not_found",
            f"No supplier adapter registered for '{supplier_name}'.",
            details={"supplier_code": supplier_name, "adapter_error": exc.code},
        )

    attempt_id = str(uuid4())
    ctx = SupplierContext(
        request_id=attempt_id,
        organization_id=org_id,
        tenant_id=getattr(request.state, "tenant_id", None),
        user_id=str(user.get("id") or ""),
    )

    result = None
    try:
        result = await run_with_deadline(adapter.confirm_booking(ctx, booking), ctx)
    except SupplierAdapterError as exc:
        # Map adapter-level errors to HTTP responses and audit
        retryable = getattr(exc, "retryable", False)
        details = getattr(exc, "details", {})

        # Audit supplier confirm failure
        actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="SUPPLIER_CONFIRM_FAILED",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "supplier": supplier_name,
                "supplier_code_canonical": supplier_doc.get("code") or supplier_name,
                "supplier_code_legacy": supplier_name,
                "retryable": retryable,
                "timeout_ms": ctx.timeout_ms,
                "error_code": exc.code,
            },
        )

        raise AppError(
            502 if retryable else 409,
            exc.code,
            exc.message,
            details={"retryable": retryable, **details},
        )

    # Map ConfirmStatus to HTTP / state transitions
    if result.status is ConfirmStatus.CONFIRMED:
        supplier_booking_id = result.supplier_booking_id
        update_fields: dict[str, Any] = {"updated_at": now_utc()}
        if supplier_booking_id:
            update_fields["offer_ref.supplier_booking_id"] = supplier_booking_id

        # Persist normalized supplier snapshot (with redacted confirm snapshot)
        update_fields["supplier.code"] = result.supplier_code
        update_fields["supplier.offer_id"] = supplier_offer_id
        update_fields["supplier.booking_id"] = supplier_booking_id
        update_fields["supplier.confirm_snapshot"] = redact_sensitive_fields(result.raw or {})

        await db.bookings.update_one(
            {"_id": oid, "organization_id": org_id},
            {"$set": update_fields},
        )

        # Append lifecycle BOOKING_CONFIRMED event
        lifecycle = BookingLifecycleService(db)
        await lifecycle.append_event(
            organization_id=org_id,
            agency_id=booking.get("agency_id") or "",
            booking_id=booking_id,
            event="BOOKING_CONFIRMED",
            request_id=attempt_id,
            before={"status": status_val or "PENDING"},
            after={"status": "CONFIRMED"},
            meta={
                "source": source,
                # Preserve legacy supplier name in events for compatibility
                "supplier": supplier_name,
                "supplier_offer_id": supplier_offer_id,
                "supplier_code_canonical": result.supplier_code,
                "supplier_code_legacy": supplier_name,
                "timeout_ms": ctx.timeout_ms,
            },
        )

        # Audit log for B2B booking confirmation
        actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
        meta = {
            "source": "supplier_fulfilment",
            # Preserve legacy supplier name in audit for compatibility
            "supplier": supplier_name,
            "supplier_offer_id": supplier_offer_id,
            "tenant_id": offer_ref.get("buyer_tenant_id"),
            "attempt_id": attempt_id,
            "supplier_code_canonical": result.supplier_code,
            "supplier_code_legacy": supplier_name,
            "retryable": False,
            "timeout_ms": ctx.timeout_ms,
        }
        if supplier_booking_id:
            meta["supplier_booking_id"] = supplier_booking_id

        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="B2B_BOOKING_CONFIRMED",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta=meta,
        )

        return {"booking_id": booking_id, "state": "confirmed"}

    if result.status is ConfirmStatus.REJECTED:
        actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="SUPPLIER_CONFIRM_ATTEMPT",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "status": "rejected",
                "supplier": supplier_name,
                "supplier_code_canonical": result.supplier_code,
                "supplier_code_legacy": supplier_name,
                "retryable": False,
                "timeout_ms": ctx.timeout_ms,
                "raw": redact_sensitive_fields(result.raw or {}),
            },
        )
        raise AppError(
            409,
            "supplier_rejected",
            "Supplier rejected booking confirm.",
            details={"supplier": supplier_name},
        )

    if result.status is ConfirmStatus.PENDING:
        actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="SUPPLIER_CONFIRM_ATTEMPT",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "status": "pending",
                "supplier": supplier_name,
                "supplier_code_canonical": result.supplier_code,
                "supplier_code_legacy": supplier_name,
                "retryable": False,
                "timeout_ms": ctx.timeout_ms,
                "raw": redact_sensitive_fields(result.raw or {}),
            },
        )
        return AppError(
            202,
            "supplier_pending",
            "Supplier confirm is pending.",
            details={"supplier": supplier_name},
        ).to_dict()

    if result.status is ConfirmStatus.NOT_SUPPORTED:
        actor = {"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")}
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="SUPPLIER_CONFIRM_ATTEMPT",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "status": "not_supported",
                "supplier": supplier_name,
                "supplier_code_canonical": result.supplier_code,
                "supplier_code_legacy": supplier_name,
                "retryable": False,
                "timeout_ms": ctx.timeout_ms,
                "raw": redact_sensitive_fields(result.raw or {}),
            },
        )
        raise AppError(
            501,
            "supplier_not_supported",
            "Supplier confirm is not supported.",
            details={"supplier": supplier_name},
        )

    # Fallback for unknown statuses
    raise AppError(
        500,
        "SUPPLIER_FULFILMENT_FAILED",
        "Unexpected supplier confirm status.",
        details={"supplier": supplier_name, "status": result.status},
    )
