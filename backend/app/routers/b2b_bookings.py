from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.repos_idempotency import IdempotencyRepo
from app.schemas_b2b_bookings import BookingCreateRequest, BookingCreateResponse
from app.services.b2b_pricing import B2BPricingService
from app.services.b2b_booking import B2BBookingService

router = APIRouter(prefix="/api/b2b", tags=["b2b-bookings"])


def get_pricing_service(db=Depends(get_db)) -> B2BPricingService:
    return B2BPricingService(db)


def get_booking_service(db=Depends(get_db)) -> B2BBookingService:
    return B2BBookingService(db)


def get_idem_repo(db=Depends(get_db)) -> IdempotencyRepo:
    return IdempotencyRepo(db)


@router.post(
    "/bookings",
    response_model=BookingCreateResponse,
    dependencies=[Depends(require_roles(["agency_agent", "agency_admin"]))],
)
async def create_b2b_booking(
    payload: BookingCreateRequest,
    user=Depends(get_current_user),
    pricing: B2BPricingService = Depends(get_pricing_service),
    booking_svc: B2BBookingService = Depends(get_booking_service),
    idem: IdempotencyRepo = Depends(get_idem_repo),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(403, "forbidden", "User is not bound to an agency")

    endpoint = "b2b_bookings_create"
    method = "POST"
    path = "/api/b2b/bookings"

    async def compute():
        quote_doc = await pricing.ensure_quote_valid(
            organization_id=org_id,
            agency_id=agency_id,
            quote_id=payload.quote_id,
        )
        # Context mismatch check (agency already enforced via query, channel optional here)
        booking = await booking_svc.create_booking_from_quote(
            organization_id=org_id,
            agency_id=agency_id,
            user_email=user.get("email"),
            quote_doc=quote_doc,
            booking_req=payload,
        )
        return 200, booking.model_dump()

    status, body = await idem.store_or_replay(
        org_id=org_id,
        agency_id=agency_id,
        endpoint=endpoint,
        key=idempotency_key,
        method=method,
        path=path,
        request_body=payload.model_dump(),
        compute_response_fn=compute,
    )

    if status == 200:
        return BookingCreateResponse(**body)

    return JSONResponse(status_code=status, content=body)



@router.post("/bookings/{booking_id}/refund-requests")
async def create_refund_request(
    booking_id: str,
    payload: dict,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Agency-initiated refund request for a booking.

    - Does not change booking status.
    - Creates a refund_case with computed amounts.
    """
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(
            status_code=403,
            code="forbidden",
            message="User is not bound to an agency",
        )

    requested_amount = payload.get("amount")
    requested_message = payload.get("message")
    reason = payload.get("reason", "customer_request")

    from app.services.refund_cases import RefundCaseService

    svc = RefundCaseService(db)
    case = await svc.create_refund_request(
        organization_id=org_id,
        booking_id=booking_id,
        agency_id=agency_id,
        requested_amount=requested_amount,
        requested_message=requested_message,
        reason=reason,
        created_by=user.get("email"),
    )
    return case



@router.post(
    "/bookings/{booking_id}/cancel",
    dependencies=[Depends(require_roles(["agency_agent", "agency_admin"]))],
)
async def cancel_b2b_booking(
    booking_id: str,
    payload: dict | None = None,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Cancel a CONFIRMED booking (after-sales v1).

    - Idempotent: if booking is already CANCELLED, returns current state.
    - Creates BOOKING_CANCELLED ledger posting as exact reversal of
      BOOKING_CONFIRMED in EUR.
    """
    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not agency_id:
        raise AppError(403, "forbidden", "User is not bound to an agency")

    from bson import ObjectId

    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    booking = await db.bookings.find_one(
        {"_id": oid, "organization_id": org_id, "agency_id": agency_id}
    )
    if not booking:
        raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

    status = booking.get("status")
    if status == "CANCELLED":
        # Idempotent behaviour: return current state
        return {
            "booking_id": booking_id,
            "status": status,
            "refund_status": "COMPLETED",
        }

    if status != "CONFIRMED":
        raise AppError(
            409,
            "cannot_cancel_in_status",
            f"Cannot cancel booking in status {status}",
            {"booking_id": booking_id, "status": status},
        )

    reason = (payload or {}).get("reason", "customer_request")

    # Update booking status
    from app.utils import now_utc

    now = now_utc()
    await db.bookings.update_one(
        {"_id": oid, "organization_id": org_id},
        {
            "$set": {
                "status": "CANCELLED",
                "cancel_reason": reason,
                "cancelled_at": now,
            }
        },
    )

    # Post BOOKING_CANCELLED event to ledger
    from app.services.booking_finance import BookingFinanceService

    bfs = BookingFinanceService(db)
    await bfs.post_booking_cancelled(
        organization_id=org_id,
        booking_id=booking_id,
        agency_id=agency_id,
        occurred_at=now,
    )

    # Update booking_financials refunded_total / penalty_total using current values
    bf = await db.booking_financials.find_one(
        {"organization_id": org_id, "booking_id": booking_id}
    )

    refund_eur = None
    penalty_eur = None
    if bf:
        refund_eur = float(bf.get("refunded_total", 0.0))
        penalty_eur = float(bf.get("penalty_total", 0.0))

    resp = {
        "booking_id": booking_id,
        "status": "CANCELLED",
        "refund_status": "COMPLETED",
    }
    if refund_eur is not None:
        resp["refund_eur"] = refund_eur
    if penalty_eur is not None:
        resp["penalty_eur"] = penalty_eur

    return resp
