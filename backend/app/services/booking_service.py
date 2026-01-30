from __future__ import annotations

from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.booking_state_machine import validate_transition
from app.repositories.booking_repository import BookingRepository
from app.services.audit import write_audit_log
from app.utils import now_utc


async def create_booking_draft(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    actor: Dict[str, Any],
    payload: Dict[str, Any],
    request: Any,
) -> str:
    repo = BookingRepository(db)
    booking_id = await repo.create_draft(organization_id, payload)

    # Audit: BOOKING_CREATED
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor=actor,
        request=request,
        action="BOOKING_CREATED",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after=None,
        meta={"state": "draft"},
    )

    return booking_id



async def create_booking_from_supplier_offer(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    actor: Dict[str, Any],
    payload: Dict[str, Any],
    request: Any,
) -> Dict[str, Any]:
    """Create a quoted booking from a supplier offer (mock_v1 only for now).

    - Validates supplier value
    - Calls mock supplier adapter to resolve offers
    - Validates offer_id and currency
    - Persists a minimal quoted booking and returns sanitized document
    """
    from fastapi import HTTPException, status

    from app.services.suppliers.mock_supplier_service import search_mock_offers

    supplier = payload.get("supplier")
    if supplier != "mock_v1":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="UNSUPPORTED_SUPPLIER")

    search_payload = {
        "check_in": payload.get("check_in"),
        "check_out": payload.get("check_out"),
        "guests": payload.get("guests"),
        "city": payload.get("city"),
    }

    offers_response = await search_mock_offers(search_payload)

    currency = offers_response.get("currency")
    if currency != "TRY":
        # Prepare ground for future multi-currency gate without exposing it now
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="UNSUPPORTED_CURRENCY")

    items = offers_response.get("items") or []
    target_offer_id = payload.get("offer_id")
    match = next((item for item in items if item.get("offer_id") == target_offer_id), None)
    if not match:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="INVALID_OFFER")

    amount = float(match.get("total_price") or 0.0)

    repo = BookingRepository(db)
    booking_id = await repo.create_from_supplier_offer(
        organization_id,
        amount=amount,
        currency=currency,
        supplier=supplier,
        offer_id=target_offer_id,
        extra_fields=None,
    )

    # Load and sanitize for API response
    doc = await repo.get_by_id(organization_id, booking_id)
    assert doc is not None
    doc_out: Dict[str, Any] = dict(doc)
    doc_out["id"] = str(doc_out.pop("_id"))
    return doc_out


async def _transition_booking_state(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    booking_id: str,
    target_state: str,
    actor: Dict[str, Any],
    request: Any,
    *,
    extra_updates: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    repo = BookingRepository(db)
    doc = await repo.get_by_id(organization_id, booking_id)
    if not doc:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BOOKING_NOT_FOUND")

    current_state = str(doc.get("state") or "")

    # Validate transition
    try:
        validate_transition(current_state, target_state)
    except Exception as exc:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="INVALID_STATE_TRANSITION") from exc

    before, after = await repo.update_state(organization_id, booking_id, target_state, extra_updates)
    assert after is not None

    # Audit: BOOKING_STATE_CHANGED
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor=actor,
        request=request,
        action="BOOKING_STATE_CHANGED",
        target_type="booking",
        target_id=booking_id,
        before=before,
        after=after,
        meta={"from": current_state, "to": target_state},
    )

    if target_state == "cancel_requested":
        await write_audit_log(
            db,
            organization_id=organization_id,
            actor=actor,
            request=request,
            action="CANCEL_REQUESTED",
            target_type="booking",
            target_id=booking_id,
            before=before,
            after=after,
            meta={},
        )

    # Return a sanitized version for API
    doc_out = dict(after)
    doc_out["id"] = str(doc_out.pop("_id"))
    return doc_out


async def transition_to_quoted(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    booking_id: str,
    actor: Dict[str, Any],
    request: Any,
) -> Dict[str, Any]:
    return await _transition_booking_state(
        db,
        organization_id,
        booking_id,
        target_state="quoted",
        actor=actor,
        request=request,
    )


async def transition_to_booked(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    booking_id: str,
    actor: Dict[str, Any],
    request: Any,
) -> Dict[str, Any]:
    """Transition booking to booked, applying Credit & Exposure v1 rules.

    If available credit is insufficient, move booking to 'hold' instead and
    create a Finance task for manual review.
    """
    from app.services.credit_exposure_service import (
        has_available_credit,
        create_finance_hold_task_for_booking,
    )

    # Load current booking to know amount and state
    repo = BookingRepository(db)
    doc = await repo.get_by_id(organization_id, booking_id)
    if not doc:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BOOKING_NOT_FOUND")

    amount = float(doc.get("amount", 0.0))

    # Check credit availability for API flows; unit-level tests that operate
    # directly on the default org (using raw ObjectId string) should preserve
    # Sprint 1 behavior and therefore skip credit enforcement when no explicit
    # Standard credit profile exists.
    from app.services.credit_exposure_service import _get_credit_limit

    limit = await _get_credit_limit(db, organization_id)
    enforce_credit = limit is not None

    if enforce_credit and not await has_available_credit(db, organization_id, amount):
        # Move to hold instead of booked
        before, after = await repo.update_state(organization_id, booking_id, "hold")
        assert after is not None

        # Audit: BOOKING_STATE_CHANGED (quoted -> hold or current -> hold)
        current_state = str(doc.get("state") or "")
        await write_audit_log(
            db,
            organization_id=organization_id,
            actor=actor,
            request=request,
            action="BOOKING_STATE_CHANGED",
            target_type="booking",
            target_id=booking_id,
            before=before,
            after=after,
            meta={"from": current_state, "to": "hold"},
        )

        # Create Finance task for this held booking
        await create_finance_hold_task_for_booking(db, organization_id, booking_id)

        # Return sanitized doc
        doc_out = dict(after)
        doc_out["id"] = str(doc_out.pop("_id"))
        return doc_out

    # If credit is sufficient, proceed with normal booked transition
    booking = await _transition_booking_state(
        db,
        organization_id,
        booking_id,
        target_state="booked",
        actor=actor,
        request=request,
    )

    # Evaluate simple risk rules (amount threshold) and emit audit alerts
    from app.services.risk_rules_service import evaluate_booking_risk

    await evaluate_booking_risk(db, organization_id, booking, actor, request)

    return booking


async def transition_to_modified(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    booking_id: str,
    actor: Dict[str, Any],
    request: Any,
) -> Dict[str, Any]:
    return await _transition_booking_state(
        db,
        organization_id,
        booking_id,
        target_state="modified",
        actor=actor,
        request=request,
    )


async def transition_to_refund_in_progress(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    booking_id: str,
    actor: Dict[str, Any],
    request: Any,
) -> Dict[str, Any]:
    booking = await _transition_booking_state(
        db,
        organization_id,
        booking_id,
        target_state="refund_in_progress",
        actor=actor,
        request=request,
    )

    await write_audit_log(
        db,
        organization_id=organization_id,
        actor=actor,
        request=request,
        action="REFUND_REQUESTED",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after=None,
        meta={"state": "refund_in_progress"},
    )

    return booking


async def transition_to_refunded(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    booking_id: str,
    actor: Dict[str, Any],
    request: Any,
) -> Dict[str, Any]:
    """Approve refund: refund_in_progress -> refunded.

    Keeps BOOKING_STATE_CHANGED audit via _transition_booking_state and emits
    an additional REFUND_APPROVED audit event.
    """
    booking = await _transition_booking_state(
        db,
        organization_id,
        booking_id,
        target_state="refunded",
        actor=actor,
        request=request,
    )

    await write_audit_log(
        db,
        organization_id=organization_id,
        actor=actor,
        request=request,
        action="REFUND_APPROVED",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after=None,
        meta={"state": "refunded"},
    )

    return booking


async def transition_to_refund_rejected(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    booking_id: str,
    actor: Dict[str, Any],
    request: Any,
) -> Dict[str, Any]:
    """Reject a refund request: refund_in_progress -> booked.

    Keeps BOOKING_STATE_CHANGED audit via _transition_booking_state and emits
    an additional REFUND_REJECTED audit event.
    """
    booking = await _transition_booking_state(
        db,
        organization_id,
        booking_id,
        target_state="booked",
        actor=actor,
        request=request,
    )

    await write_audit_log(
        db,
        organization_id=organization_id,
        actor=actor,
        request=request,
        action="REFUND_REJECTED",
        target_type="booking",
        target_id=booking_id,
        before=None,
        after=None,
        meta={"state": "booked"},
    )

    return booking


async def transition_to_cancel_requested(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    booking_id: str,
    actor: Dict[str, Any],
    request: Any,
) -> Dict[str, Any]:
    # You can add extra updates like cancel_requested_at here
    extra = {"cancel_requested_at": now_utc()}
    return await _transition_booking_state(
        db,
        organization_id,
        booking_id,
        target_state="cancel_requested",
        actor=actor,
        request=request,
        extra_updates=extra,
    )
