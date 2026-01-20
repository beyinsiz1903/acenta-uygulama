from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.utils import now_utc
from app.services.booking_events import emit_event


router = APIRouter(prefix="/api/ops", tags=["ops-b2b"])


OpsUserDep = Depends(require_roles(["admin", "ops", "super_admin"]))


@router.get("/bookings")
async def list_b2b_bookings_ops(
    status: Optional[str] = Query(None, description="Booking status filter (e.g. CONFIRMED, CANCELLED)"),
    from_: Optional[datetime] = Query(None, alias="from", description="Created_at >= from (ISO datetime)"),
    to: Optional[datetime] = Query(None, alias="to", description="Created_at <= to (ISO datetime)"),
    limit: int = Query(50, ge=1, le=200),
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Minimal booking queue for B2B bookings (ops view).

    Only bookings created via B2B flow are returned (quote_id exists).
    """

    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    query: Dict[str, Any] = {
        "organization_id": org_id,
        # B2B bookings always have a quote_id set
        "quote_id": {"$exists": True},
    }

    if status:
        # Stored as upper-case (e.g. CONFIRMED, CANCELLED)
        query["status"] = status.upper()

    if from_ or to:
        created_range: Dict[str, Any] = {}
        if from_:
            created_range["$gte"] = from_
        if to:
            created_range["$lte"] = to
        query["created_at"] = created_range

    cursor = (
        db.bookings.find(query)
        .sort("created_at", -1)
        .limit(limit)
    )
    docs: List[Dict[str, Any]] = await cursor.to_list(length=limit)

    # Join agency & channel names in-memory for readability
    agency_ids = {doc.get("agency_id") for doc in docs if doc.get("agency_id")}
    channel_ids = {doc.get("channel_id") for doc in docs if doc.get("channel_id")}

    agency_name_map: Dict[str, str] = {}
    channel_name_map: Dict[str, str] = {}

    if agency_ids:
        agencies = await db.agencies.find(
            {"organization_id": org_id, "_id": {"$in": list(agency_ids)}}
        ).to_list(length=None)
        agency_name_map = {str(a["_id"]): a.get("name") or "" for a in agencies}

    if hasattr(db, "channels") and channel_ids:
        channels = await db.channels.find(
            {"organization_id": org_id, "_id": {"$in": list(channel_ids)}}
        ).to_list(length=None)
        channel_name_map = {str(c["_id"]): c.get("name") or "" for c in channels}

    items: List[Dict[str, Any]] = []
    for doc in docs:
        amounts = doc.get("amounts") or {}
        agency_id = doc.get("agency_id")
        channel_id = doc.get("channel_id")
        flags = doc.get("finance_flags") or {}
        if flags.get("over_limit"):
            credit_status = "over_limit"
        elif flags.get("near_limit"):
            credit_status = "near_limit"
        else:
            credit_status = "ok"

        items.append(
            {
                "booking_id": str(doc.get("_id")),
                "agency_id": agency_id,
                "agency_name": agency_name_map.get(str(agency_id)),
                "status": doc.get("status"),
                "created_at": doc.get("created_at"),
                "currency": doc.get("currency"),
                "sell_price": amounts.get("sell"),
                "channel_id": channel_id,
                "channel_name": channel_name_map.get(str(channel_id)),
                "finance_flags": flags,
                "credit_status": credit_status,
            }
        )

    return {"items": items}


@router.get("/bookings/{booking_id}")
async def get_b2b_booking_detail_ops(
    booking_id: str,
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Booking detail with risk/policy snapshots for ops view."""

    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise AppError(400, "invalid_booking_id", "Booking id must be a valid ObjectId", {"booking_id": booking_id})

    booking = await db.bookings.find_one({"_id": oid, "organization_id": org_id})
    if not booking:
        raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

    amounts = booking.get("amounts") or {}
    flags = booking.get("finance_flags") or {}
    if flags.get("over_limit"):
        credit_status = "over_limit"
    elif flags.get("near_limit"):
        credit_status = "near_limit"
    else:
        credit_status = "ok"

    return {
        "booking_id": booking_id,
        "agency_id": booking.get("agency_id"),
        "channel_id": booking.get("channel_id"),
        "status": booking.get("status"),
        "payment_status": booking.get("payment_status"),
        "created_at": booking.get("created_at"),
        "updated_at": booking.get("updated_at"),
        "currency": booking.get("currency"),
        "amounts": amounts,
        "items": booking.get("items") or [],
        "customer": booking.get("customer") or {},
        "customer_id": booking.get("customer_id"),
        "travellers": booking.get("travellers") or [],
        "quote_id": booking.get("quote_id"),
        "risk_snapshot": booking.get("risk_snapshot") or {},
        "policy_snapshot": booking.get("policy_snapshot") or {},
        "finance_flags": flags,
        "credit_status": credit_status,
    }


class OpsBookingCustomerLinkIn(BaseModel):
    customer_id: Optional[str] = None


@router.patch("/bookings/{booking_id}/customer")
async def link_booking_customer_ops(
    booking_id: str,
    payload: OpsBookingCustomerLinkIn,
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Link or unlink a booking to a CRM customer from ops.

    - Auth: admin|ops|super_admin via OpsUserDep
    - Org-scope: booking and customer must belong to user's organization
    - If customer_id is null/empty -> unlink (unset booking.customer_id)
    """

    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise AppError(400, "invalid_booking_id", "Booking id must be a valid ObjectId", {"booking_id": booking_id})

    booking = await db.bookings.find_one({"_id": oid, "organization_id": org_id})
    if not booking:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    customer_id = (payload.customer_id or "").strip() if payload.customer_id is not None else None

    previous_customer_id = booking.get("customer_id")

    if customer_id:
        customer = await db.customers.find_one(
            {"organization_id": org_id, "id": customer_id},
            {"_id": 0},
        )
        if not customer:
            raise AppError(
                404,
                "customer_not_found",
                "Customer not found for this organization",
                {"customer_id": customer_id},
            )

        await db.bookings.update_one(
            {"_id": oid, "organization_id": org_id},
            {"$set": {"customer_id": customer_id, "updated_at": now_utc()}},
        )
        action = "customer_linked"
    else:
        await db.bookings.update_one(
            {"_id": oid, "organization_id": org_id},
            {"$unset": {"customer_id": ""}, "$set": {"updated_at": now_utc()}},
        )
        action = "customer_unlinked"

    # Fire-and-forget CRM event for booking-customer link/unlink
    try:
        from app.services.crm_events import log_crm_event

        await log_crm_event(
            db,
            org_id,
            entity_type="booking",
            entity_id=booking_id,
            action=action,
            payload={
                "booking_id": booking_id,
                "customer_id": customer_id,
                "previous_customer_id": previous_customer_id,
            },
            actor={"id": user.get("id"), "roles": user.get("roles") or []},
            source="api",
        )
    except Exception:
        # Audit event best-effort, ops endpoint shouldn't fail because of logging.
        pass

    return {"ok": True, "booking_id": booking_id, "customer_id": customer_id}


@router.get("/cases")
async def list_b2b_cases_ops(
    status: Optional[str] = Query(None, description="Case status filter (open/pending_approval/closed)"),
    type_: Optional[str] = Query(None, alias="type", description="Case type filter (e.g. cancel)"),
    from_: Optional[datetime] = Query(None, alias="from", description="Created_at >= from (ISO datetime)"),
    to: Optional[datetime] = Query(None, alias="to", description="Created_at <= to (ISO datetime)"),
    limit: int = Query(50, ge=1, le=200),
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Minimal case queue for B2B cancel cases (ops view)."""

    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    query: Dict[str, Any] = {
        "organization_id": org_id,
    }

    if status:
        query["status"] = status

    if type_:
        query["type"] = type_

    if from_ or to:
        created_range: Dict[str, Any] = {}
        if from_:
            created_range["$gte"] = from_
        if to:
            created_range["$lte"] = to
        query["created_at"] = created_range

    cursor = (
        db.cases.find(query)
        .sort("created_at", -1)
        .limit(limit)
    )
    docs: List[Dict[str, Any]] = await cursor.to_list(length=limit)

    items: List[Dict[str, Any]] = []
    for doc in docs:
        items.append(
            {
                "case_id": str(doc.get("_id")),
                "type": doc.get("type"),
                "booking_id": doc.get("booking_id"),
                "status": doc.get("status"),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
                "decision": doc.get("decision"),
            }
        )

    return {"items": items}


@router.get("/cases/{case_id}")
async def get_b2b_case_detail_ops(
    case_id: str,
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Case detail including cancel request payload (reason/amount/currency)."""

    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    try:
        oid = ObjectId(case_id)
    except Exception:
        raise AppError(404, "not_found", "Case not found", {"case_id": case_id})

    case = await db.cases.find_one({"_id": oid, "organization_id": org_id})
    if not case:
        raise AppError(404, "not_found", "Case not found", {"case_id": case_id})

    return {
        "case_id": case_id,
        "booking_id": case.get("booking_id"),
        "type": case.get("type"),
        "status": case.get("status"),
        "created_at": case.get("created_at"),
        "updated_at": case.get("updated_at"),
        "reason": case.get("reason"),
        "requested_refund_currency": case.get("requested_refund_currency"),
        "requested_refund_amount": case.get("requested_refund_amount"),
        "decision": case.get("decision"),
        "decision_by_email": case.get("decision_by_email"),
        "decision_at": case.get("decision_at"),
        "booking_status": case.get("booking_status"),
    }


async def _load_case_for_update(db, organization_id: str, case_id: str) -> Dict[str, Any]:
    try:
        oid = ObjectId(case_id)
    except Exception:
        raise AppError(404, "not_found", "Case not found", {"case_id": case_id})

    case = await db.cases.find_one({"_id": oid, "organization_id": organization_id})
    if not case:
        raise AppError(404, "not_found", "Case not found", {"case_id": case_id})

    if case.get("type") != "cancel":
        raise AppError(409, "unsupported_case_type", "Only cancel cases are supported in this view", {"case_id": case_id})

    status = case.get("status")
    if status not in {"open", "pending_approval"}:
        raise AppError(
            409,
            "invalid_case_state",
            "Case cannot be modified in its current state",
            {"case_id": case_id, "status": status},
        )

    return case


@router.post("/cases/{case_id}/approve")
async def approve_b2b_case_ops(
    case_id: str,
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Approve a cancel case: close case + mark booking as CANCELLED."""

    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    case = await _load_case_for_update(db, org_id, case_id)

    booking_id = case.get("booking_id")
    if not booking_id:
        raise AppError(400, "invalid_case_payload", "Case is missing booking_id", {"case_id": case_id})

    try:
        booking_oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    booking = await db.bookings.find_one({"_id": booking_oid, "organization_id": org_id})
    previous_status = booking.get("status")

    # If booking was VOUCHERED, reverse supplier accrual before status change
    if previous_status == "VOUCHERED":
        from app.services.supplier_accrual import SupplierAccrualService

        accrual_svc = SupplierAccrualService(db)
        await accrual_svc.reverse_accrual_for_booking(
            organization_id=org_id,
            booking_id=booking_id,
            triggered_by=user.get("email"),
            trigger="ops_cancel_approved",
        )


    if not booking:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    now = now_utc()

    # First close the case with decision metadata and booking_status snapshot for ops
    await db.cases.update_one(
        {"_id": case["_id"], "organization_id": org_id},
        {
            "$set": {
                "status": "closed",
                "decision": "approved",
                "decision_by_email": user.get("email"),
                "decision_at": now,
                "booking_status": "CANCELLED",
                "updated_at": now,
            }
        },
    )

    # Then mark the booking as CANCELLED
    await db.bookings.update_one(
        {"_id": booking_oid, "organization_id": org_id},
        {"$set": {"status": "CANCELLED", "updated_at": now}},
    )

    # Emit case decision and booking status change events
    actor = {"role": "ops", "email": user.get("email")}
    await emit_event(
        db,
        org_id,
        booking_id,
        "CASE_DECIDED",
        actor=actor,
        meta={"case_id": case_id, "decision": "approved"},
    )
    await emit_event(
        db,
        org_id,
        booking_id,
        "BOOKING_STATUS_CHANGED",
        actor=actor,
        meta={"status_from": booking.get("status"), "status_to": "CANCELLED"},
    )

    return {
        "case_id": case_id,
        "status": "closed",
        "decision": "approved",
        "booking_id": booking_id,
        "booking_status": "CANCELLED",
    }


@router.post("/cases/{case_id}/reject")
async def reject_b2b_case_ops(
    case_id: str,
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Reject a cancel case: close case, booking status remains unchanged."""

    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    case = await _load_case_for_update(db, org_id, case_id)

    booking_id = case.get("booking_id")

    now = now_utc()

    await db.cases.update_one(
        {"_id": case["_id"], "organization_id": org_id},
        {
            "$set": {
                "status": "closed",
                "decision": "rejected",
                "decision_by_email": user.get("email"),
                "decision_at": now,
                "updated_at": now,
            }
        },
    )

    # Emit case decision event (rejection)
    actor = {"role": "ops", "email": user.get("email")}
    await emit_event(
        db,
        org_id,
        booking_id,
        "CASE_DECIDED",
        actor=actor,
        meta={"case_id": case_id, "decision": "rejected"},
    )

    return {
        "case_id": case_id,
        "status": "closed",
        "decision": "rejected",
        "booking_id": booking_id,
    }
