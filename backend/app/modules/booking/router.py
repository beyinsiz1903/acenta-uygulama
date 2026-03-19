"""Booking command router — command-based endpoints for booking transitions.

Every booking status change flows through this router → transition service.
No direct status mutation is allowed elsewhere.

Endpoints:
  POST /api/bookings/{booking_id}/quote
  POST /api/bookings/{booking_id}/option
  POST /api/bookings/{booking_id}/confirm
  POST /api/bookings/{booking_id}/cancel
  POST /api/bookings/{booking_id}/complete
  POST /api/bookings/{booking_id}/mark-ticketed
  POST /api/bookings/{booking_id}/mark-vouchered
  POST /api/bookings/{booking_id}/mark-refunded

  GET  /api/bookings/{booking_id}/history
  GET  /api/bookings/{booking_id}/status
  GET  /api/booking-statuses/transitions
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.db import get_db
from app.modules.booking.errors import (
    BookingDomainError,
    BookingNotFoundError,
    InvalidTransitionError,
    PolicyViolationError,
    VersionConflictError,
)
from app.modules.booking.models import (
    ALLOWED_TRANSITIONS,
    BookingCommand,
    BookingStatus,
    FulfillmentStatus,
    PaymentStatus,
    get_status_label,
)
from app.modules.booking.service import ActorContext, BookingTransitionService

logger = logging.getLogger("booking.router")

router = APIRouter(prefix="/bookings", tags=["Booking Commands"])


# ── Request / Response schemas ────────────────────────────────

class TransitionRequest(BaseModel):
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None


class TransitionResponse(BaseModel):
    ok: bool = True
    booking_id: str
    status: str
    fulfillment_status: str = "none"
    payment_status: str = "unpaid"
    version: int = 0


# ── Helpers ───────────────────────────────────────────────────

def _build_actor(user: dict) -> ActorContext:
    return ActorContext(
        user_id=str(user.get("user_id", user.get("_id", ""))),
        email=user.get("email", ""),
        actor_type="user",
    )


def _org_id(user: dict) -> str:
    return user.get("organization_id", "")


def _tenant_id(user: dict) -> str:
    return user.get("tenant_id", user.get("organization_id", ""))


async def _execute_command(
    booking_id: str,
    command: str,
    user: dict,
    body: TransitionRequest,
) -> TransitionResponse:
    """Shared logic for all command endpoints."""
    db = await get_db()
    svc = BookingTransitionService(db)
    actor = _build_actor(user)

    try:
        result = await svc.transition(
            booking_id=booking_id,
            command=command,
            actor=actor,
            tenant_id=_tenant_id(user),
            organization_id=_org_id(user),
            payload=body.metadata,
            reason=body.reason,
            idempotency_key=body.idempotency_key,
        )
    except BookingNotFoundError:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")
    except InvalidTransitionError as e:
        raise HTTPException(status_code=422, detail={
            "code": e.code,
            "message": e.message,
            "details": e.details,
        })
    except PolicyViolationError as e:
        raise HTTPException(status_code=422, detail={
            "code": e.code,
            "message": e.message,
            "details": e.details,
        })
    except VersionConflictError:
        raise HTTPException(status_code=409, detail="VERSION_CONFLICT")
    except BookingDomainError as e:
        raise HTTPException(status_code=400, detail={
            "code": e.code,
            "message": e.message,
        })

    return TransitionResponse(
        booking_id=booking_id,
        status=result.get("status", "draft"),
        fulfillment_status=result.get("fulfillment_status", "none"),
        payment_status=result.get("payment_status", "unpaid"),
        version=result.get("version", 0),
    )


# ── Command endpoints ────────────────────────────────────────

@router.post(
    "/{booking_id}/quote",
    response_model=TransitionResponse,
    summary="Create a quote for a booking",
)
async def quote_booking(
    booking_id: str,
    body: TransitionRequest = TransitionRequest(),
    user: dict = Depends(get_current_user),
):
    return await _execute_command(booking_id, "create_quote", user, body)


@router.post(
    "/{booking_id}/option",
    response_model=TransitionResponse,
    summary="Place an option on a booking",
)
async def option_booking(
    booking_id: str,
    body: TransitionRequest = TransitionRequest(),
    user: dict = Depends(get_current_user),
):
    return await _execute_command(booking_id, "place_option", user, body)


@router.post(
    "/{booking_id}/confirm",
    response_model=TransitionResponse,
    summary="Confirm a booking",
)
async def confirm_booking(
    booking_id: str,
    body: TransitionRequest = TransitionRequest(),
    user: dict = Depends(get_current_user),
):
    return await _execute_command(booking_id, "confirm", user, body)


@router.post(
    "/{booking_id}/cancel",
    response_model=TransitionResponse,
    summary="Cancel a booking",
)
async def cancel_booking(
    booking_id: str,
    body: TransitionRequest = TransitionRequest(),
    user: dict = Depends(get_current_user),
):
    return await _execute_command(booking_id, "cancel", user, body)


@router.post(
    "/{booking_id}/complete",
    response_model=TransitionResponse,
    summary="Mark booking as completed (post-checkout)",
)
async def complete_booking(
    booking_id: str,
    body: TransitionRequest = TransitionRequest(),
    user: dict = Depends(get_current_user),
):
    return await _execute_command(booking_id, "complete", user, body)


@router.post(
    "/{booking_id}/mark-ticketed",
    response_model=TransitionResponse,
    summary="Mark booking fulfillment as ticketed",
)
async def mark_ticketed(
    booking_id: str,
    body: TransitionRequest = TransitionRequest(),
    user: dict = Depends(get_current_user),
):
    return await _execute_command(booking_id, "mark_ticketed", user, body)


@router.post(
    "/{booking_id}/mark-vouchered",
    response_model=TransitionResponse,
    summary="Mark booking fulfillment as vouchered",
)
async def mark_vouchered(
    booking_id: str,
    body: TransitionRequest = TransitionRequest(),
    user: dict = Depends(get_current_user),
):
    return await _execute_command(booking_id, "mark_vouchered", user, body)


@router.post(
    "/{booking_id}/mark-refunded",
    response_model=TransitionResponse,
    summary="Mark a cancelled booking as refunded",
)
async def mark_refunded(
    booking_id: str,
    body: TransitionRequest = TransitionRequest(),
    user: dict = Depends(get_current_user),
):
    return await _execute_command(booking_id, "mark_refunded", user, body)


# ── Read endpoints ────────────────────────────────────────────

@router.get(
    "/{booking_id}/history",
    summary="Get booking transition history",
)
async def get_booking_history(
    booking_id: str,
    user: dict = Depends(get_current_user),
):
    db = await get_db()
    org_id = _org_id(user)
    cursor = db.booking_history.find(
        {"booking_id": booking_id, "organization_id": org_id},
        {"_id": 0},
    ).sort("occurred_at", -1).limit(100)
    history = await cursor.to_list(100)
    return {"booking_id": booking_id, "history": history}


@router.get(
    "/{booking_id}/status",
    summary="Get current booking status summary",
)
async def get_booking_status(
    booking_id: str,
    user: dict = Depends(get_current_user),
):
    db = await get_db()
    org_id = _org_id(user)
    from bson import ObjectId as OID
    try:
        oid = OID(booking_id)
    except Exception:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

    booking = await db.bookings.find_one(
        {"_id": oid, "organization_id": org_id},
        {
            "_id": 0,
            "status": 1,
            "fulfillment_status": 1,
            "payment_status": 1,
            "version": 1,
            "status_changed_at": 1,
            "status_changed_by": 1,
        },
    )
    if not booking:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

    status = booking.get("status", "draft")
    return {
        "booking_id": booking_id,
        "status": status,
        "status_label": get_status_label(status),
        "fulfillment_status": booking.get("fulfillment_status", "none"),
        "payment_status": booking.get("payment_status", "unpaid"),
        "version": booking.get("version", 0),
        "status_changed_at": booking.get("status_changed_at"),
        "status_changed_by": booking.get("status_changed_by"),
        "allowed_transitions": list(ALLOWED_TRANSITIONS.get(status, set())),
    }


# ── Reference data endpoint ──────────────────────────────────

@router.get(
    "-statuses/transitions",
    summary="Get full transition matrix (reference data)",
)
async def get_transition_matrix():
    return {
        "statuses": [s.value for s in BookingStatus],
        "fulfillment_statuses": [f.value for f in FulfillmentStatus],
        "payment_statuses": [p.value for p in PaymentStatus],
        "transitions": {k: list(v) for k, v in ALLOWED_TRANSITIONS.items()},
        "commands": [c.value for c in BookingCommand],
    }
