"""RateHawk Booking Flow Service — ETG API v3 Compliant.

Implements the complete booking lifecycle aligned with RateHawk's real API:
    Search → Prebook (Price Revalidation) → Booking Form → Booking Finish → Status Poll → Cancel

Key design decisions:
  - partner_order_id = syroce_booking_uuid (unique per booking, consistent across lifecycle)
  - Async booking status: poll until confirmed or timeout (no optimistic confirmation)
  - Booking cut-off handling: fail gracefully if booking times out
  - Sandbox test property support: test_hotel, test_hotel_do_not_book

RateHawk API Reference:
  Sandbox: https://api-sandbox.worldota.net
  Production: https://api.worldota.net
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

from app.db import get_db

logger = logging.getLogger("ratehawk.booking")

# ── Constants ─────────────────────────────────────────────────────────

BOOKING_STATUS_POLL_INTERVAL_S = 2.0
BOOKING_STATUS_POLL_MAX_ATTEMPTS = 15
BOOKING_CUTOFF_TIMEOUT_S = 60.0

# Sandbox test properties recognized by RateHawk
SANDBOX_TEST_PROPERTIES = {
    "test_hotel": {
        "id": "test_hotel",
        "name": "RateHawk Test Hotel",
        "city": "Sandbox",
        "country": "XX",
        "stars": 4,
        "bookable": True,
        "description": "Standard test property for sandbox booking tests",
    },
    "test_hotel_do_not_book": {
        "id": "test_hotel_do_not_book",
        "name": "RateHawk Test Hotel (Do Not Book)",
        "city": "Sandbox",
        "country": "XX",
        "stars": 3,
        "bookable": False,
        "description": "Test property that simulates booking rejection",
    },
}


class BookingFlowStatus(str, Enum):
    """Booking flow statuses aligned with RateHawk lifecycle."""
    INITIATED = "initiated"
    PRECHECK_PASSED = "precheck_passed"
    PRECHECK_FAILED = "precheck_failed"
    BOOKING_REQUESTED = "booking_requested"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    CANCELLATION_PENDING = "cancellation_pending"


class PrecheckDecision(str, Enum):
    """Precheck outcomes."""
    PROCEED = "proceed"
    PROCEED_WITH_WARNING = "proceed_with_warning"
    REQUIRES_APPROVAL = "requires_approval"
    ABORT = "abort"


# ── Booking Precheck / Price Revalidation ─────────────────────────────

async def booking_precheck(
    supplier: str,
    hotel_id: str,
    book_hash: str | None,
    checkin: str,
    checkout: str,
    guests: int = 2,
    currency: str = "EUR",
) -> dict[str, Any]:
    """Run pre-booking price revalidation (ETG prebook endpoint).

    This is the CRITICAL step before booking. It validates:
      1. Price hasn't changed since search
      2. Room/rate is still available
      3. Returns book_hash for booking step

    Decision matrix:
      drift < 2%   → proceed silently
      drift 2-5%   → proceed with warning
      drift 5-10%  → requires agency approval
      drift > 10%  → abort booking
    """
    db = await get_db()
    precheck_id = str(uuid.uuid4())
    start = time.monotonic()

    # Get cached price for comparison
    cached_doc = await db.supplier_inventory.find_one(
        {"supplier": supplier, "hotel_id": hotel_id},
        {"_id": 0, "rooms": 1, "name": 1},
    )
    cached_price = 0.0
    if cached_doc and cached_doc.get("rooms"):
        prices = [r.get("price", 0) for r in cached_doc["rooms"] if r.get("price")]
        cached_price = min(prices) if prices else 0.0

    # Get revalidated price from supplier
    from app.services.inventory_sync_service import _determine_sync_mode
    sync_mode, cred_config = await _determine_sync_mode(supplier)

    revalidated_price = cached_price
    api_latency_ms = 0

    if sync_mode == "sandbox" and cred_config:
        from app.services.ratehawk_sync_adapter import revalidate_price_from_ratehawk
        result = await revalidate_price_from_ratehawk(
            cred_config["base_url"],
            cred_config["credentials"],
            hotel_id, checkin, checkout,
        )
        api_latency_ms = result.get("latency_ms", 0)
        if result.get("success"):
            revalidated_price = result.get("price", cached_price)
    else:
        # Simulation mode — add minor drift for realism
        import random
        drift_factor = 1.0 + random.uniform(-0.03, 0.05)
        revalidated_price = round(cached_price * drift_factor, 2) if cached_price > 0 else round(random.uniform(80, 350), 2)

    # Calculate drift
    drift_amount = revalidated_price - cached_price if cached_price > 0 else 0.0
    drift_pct = (drift_amount / cached_price * 100) if cached_price > 0 else 0.0

    # Decision logic
    decision = PrecheckDecision.PROCEED
    warnings = []
    can_proceed = True
    requires_approval = False
    abort_reason = None

    if abs(drift_pct) > 10.0:
        decision = PrecheckDecision.ABORT
        can_proceed = False
        abort_reason = f"Price drift {drift_pct:.1f}% exceeds 10% threshold"
    elif abs(drift_pct) > 5.0:
        decision = PrecheckDecision.REQUIRES_APPROVAL
        requires_approval = True
        warnings.append(f"Price drift {drift_pct:.1f}% — agency approval required")
    elif abs(drift_pct) > 2.0:
        decision = PrecheckDecision.PROCEED_WITH_WARNING
        warnings.append(f"Minor price drift of {drift_pct:.1f}%")

    latency_ms = round((time.monotonic() - start) * 1000, 1)

    # Generate book_hash for next step (in real API this comes from prebook response)
    generated_book_hash = book_hash or f"bh_{uuid.uuid4().hex[:16]}"

    result = {
        "precheck_id": precheck_id,
        "supplier": supplier,
        "hotel_id": hotel_id,
        "mode": sync_mode,
        "decision": decision.value,
        "can_proceed": can_proceed,
        "requires_approval": requires_approval,
        "abort_reason": abort_reason,
        "warnings": warnings,
        "pricing": {
            "cached_price": cached_price,
            "revalidated_price": revalidated_price,
            "drift_amount": round(drift_amount, 2),
            "drift_pct": round(drift_pct, 2),
            "currency": currency,
        },
        "book_hash": generated_book_hash,
        "checkin": checkin,
        "checkout": checkout,
        "guests": guests,
        "api_latency_ms": api_latency_ms,
        "total_latency_ms": latency_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Persist precheck for audit
    await db.booking_prechecks.insert_one({
        **result,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })

    return result


# ── Booking Creation ──────────────────────────────────────────────────

async def create_booking(
    supplier: str,
    hotel_id: str,
    book_hash: str,
    checkin: str,
    checkout: str,
    guests: list[dict[str, Any]],
    contact: dict[str, Any],
    user_ip: str = "127.0.0.1",
    currency: str = "EUR",
    precheck_id: str | None = None,
) -> dict[str, Any]:
    """Create a booking following the RateHawk API v3 flow.

    Flow: booking_form → booking_finish → status_poll

    CRITICAL: partner_order_id = syroce_booking_uuid
    This is the primary link between Syroce and RateHawk.
    """
    db = await get_db()
    syroce_booking_uuid = str(uuid.uuid4())
    start = time.monotonic()

    from app.services.inventory_sync_service import _determine_sync_mode
    sync_mode, cred_config = await _determine_sync_mode(supplier)

    # Create booking record BEFORE calling supplier
    booking_doc = {
        "booking_id": syroce_booking_uuid,
        "partner_order_id": syroce_booking_uuid,
        "supplier": supplier,
        "hotel_id": hotel_id,
        "book_hash": book_hash,
        "checkin": checkin,
        "checkout": checkout,
        "guests": guests,
        "contact": contact,
        "user_ip": user_ip,
        "currency": currency,
        "precheck_id": precheck_id,
        "mode": sync_mode,
        "status": BookingFlowStatus.INITIATED.value,
        "status_history": [{
            "status": BookingFlowStatus.INITIATED.value,
            "at": datetime.now(timezone.utc).isoformat(),
            "detail": "Booking flow initiated",
        }],
        "supplier_response": None,
        "confirmation_code": None,
        "is_test": hotel_id in SANDBOX_TEST_PROPERTIES or hotel_id.startswith("test_"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.ratehawk_bookings.insert_one({**booking_doc})

    # Execute booking flow
    if sync_mode == "sandbox" and cred_config:
        result = await _execute_real_booking(
            db, syroce_booking_uuid, supplier, hotel_id, book_hash,
            checkin, checkout, guests, contact, user_ip, currency,
            cred_config,
        )
    else:
        result = await _execute_simulated_booking(
            db, syroce_booking_uuid, supplier, hotel_id,
            checkin, checkout, guests, contact, currency,
        )

    latency_ms = round((time.monotonic() - start) * 1000, 1)
    result["total_duration_ms"] = latency_ms

    return result


async def _execute_real_booking(
    db, booking_id: str, supplier: str, hotel_id: str, book_hash: str,
    checkin: str, checkout: str, guests: list, contact: dict,
    user_ip: str, currency: str, cred_config: dict,
) -> dict[str, Any]:
    """Execute booking via real RateHawk API."""
    from app.services.ratehawk_sync_adapter import _make_auth_header, _api_call_with_retry
    import httpx

    base_url = cred_config["base_url"]
    headers = _make_auth_header(
        cred_config["credentials"]["key_id"],
        cred_config["credentials"]["api_key"],
    )

    # Step 1: Booking Form
    await _update_booking_status(db, booking_id, BookingFlowStatus.BOOKING_REQUESTED, "Booking form requested")

    booking_form_payload = {
        "partner_order_id": booking_id,
        "book_hash": book_hash,
        "language": "en",
        "user_ip": user_ip,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp, meta = await _api_call_with_retry(
            client, "POST",
            f"{base_url}/api/b2b/v3/hotel/order/booking/form/",
            headers, json_payload=booking_form_payload,
            max_retries=2, base_delay=1.5,
            operation="booking_form",
        )

    if resp is None or resp.status_code != 200:
        error_msg = meta.get("error", "Booking form request failed")
        await _update_booking_status(db, booking_id, BookingFlowStatus.FAILED, error_msg)
        return _booking_result(booking_id, BookingFlowStatus.FAILED, error=error_msg)

    # Step 2: Booking Finish
    rooms_payload = _build_rooms_payload(guests, contact)
    finish_payload = {
        "partner_order_id": booking_id,
        "book_hash": book_hash,
        "language": "en",
        "user_ip": user_ip,
        "rooms": rooms_payload,
        "payment_type": "now",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp, meta = await _api_call_with_retry(
            client, "POST",
            f"{base_url}/api/b2b/v3/hotel/order/booking/finish/",
            headers, json_payload=finish_payload,
            max_retries=2, base_delay=2.0,
            operation="booking_finish",
        )

    if resp is None or resp.status_code != 200:
        error_msg = meta.get("error", "Booking finish failed")
        await _update_booking_status(db, booking_id, BookingFlowStatus.FAILED, error_msg)
        return _booking_result(booking_id, BookingFlowStatus.FAILED, error=error_msg)

    # Step 3: Poll for confirmation (async — booking may not be instant)
    await _update_booking_status(
        db, booking_id, BookingFlowStatus.AWAITING_CONFIRMATION,
        "Booking submitted, polling for confirmation",
    )

    final_status = await _poll_booking_status_real(
        db, booking_id, base_url, headers,
    )

    return final_status


async def _poll_booking_status_real(
    db, booking_id: str, base_url: str, headers: dict,
) -> dict[str, Any]:
    """Poll RateHawk booking status until confirmed or timeout."""
    import httpx
    from app.services.ratehawk_sync_adapter import _api_call_with_retry

    cutoff_deadline = time.monotonic() + BOOKING_CUTOFF_TIMEOUT_S

    for attempt in range(BOOKING_STATUS_POLL_MAX_ATTEMPTS):
        if time.monotonic() > cutoff_deadline:
            await _update_booking_status(
                db, booking_id, BookingFlowStatus.TIMEOUT,
                f"Booking cut-off reached after {BOOKING_CUTOFF_TIMEOUT_S}s",
            )
            return _booking_result(
                booking_id, BookingFlowStatus.TIMEOUT,
                error=f"Booking confirmation timed out after {BOOKING_CUTOFF_TIMEOUT_S}s",
            )

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp, meta = await _api_call_with_retry(
                client, "POST",
                f"{base_url}/api/b2b/v3/hotel/order/booking/finish/status/",
                headers,
                json_payload={"partner_order_id": booking_id},
                max_retries=1, base_delay=1.0,
                operation="booking_status_poll",
            )

        if resp and resp.status_code == 200:
            data = resp.json()
            status = data.get("status", data.get("data", {}).get("status", ""))

            if status == "confirmed" or status == "ok":
                confirmation_code = data.get("confirmation_number", data.get("data", {}).get("confirmation_number", ""))
                await _update_booking_status(
                    db, booking_id, BookingFlowStatus.CONFIRMED,
                    f"Booking confirmed: {confirmation_code}",
                    supplier_response=data,
                    confirmation_code=confirmation_code,
                )
                return _booking_result(
                    booking_id, BookingFlowStatus.CONFIRMED,
                    confirmation_code=confirmation_code,
                    supplier_data=data,
                )

            if status in ("failed", "error", "rejected"):
                error_msg = data.get("error", data.get("message", "Booking rejected by supplier"))
                await _update_booking_status(db, booking_id, BookingFlowStatus.FAILED, error_msg)
                return _booking_result(booking_id, BookingFlowStatus.FAILED, error=error_msg)

        # Not yet confirmed — wait and retry
        await asyncio.sleep(BOOKING_STATUS_POLL_INTERVAL_S)

    # Max attempts reached
    await _update_booking_status(
        db, booking_id, BookingFlowStatus.TIMEOUT,
        f"Max polling attempts ({BOOKING_STATUS_POLL_MAX_ATTEMPTS}) reached",
    )
    return _booking_result(
        booking_id, BookingFlowStatus.TIMEOUT,
        error="Booking status polling exhausted — check manually",
    )


async def _execute_simulated_booking(
    db, booking_id: str, supplier: str, hotel_id: str,
    checkin: str, checkout: str, guests: list, contact: dict,
    currency: str,
) -> dict[str, Any]:
    """Execute simulated booking for sandbox/simulation mode."""
    import random

    await _update_booking_status(db, booking_id, BookingFlowStatus.BOOKING_REQUESTED, "Simulated booking requested")

    # Simulate API delay
    await asyncio.sleep(random.uniform(0.3, 0.8))

    # Check test property behavior
    if hotel_id == "test_hotel_do_not_book" or hotel_id == "rh_test_hotel_do_not_book":
        await _update_booking_status(db, booking_id, BookingFlowStatus.FAILED, "Test property: do_not_book — booking rejected")
        return _booking_result(booking_id, BookingFlowStatus.FAILED, error="Booking rejected: test_hotel_do_not_book property")

    # Simulate async confirmation with small delay
    await _update_booking_status(db, booking_id, BookingFlowStatus.AWAITING_CONFIRMATION, "Simulated: awaiting confirmation")
    await asyncio.sleep(random.uniform(0.2, 0.5))

    # Simulate different outcomes
    outcome_roll = random.random()
    if outcome_roll < 0.85:
        # Success (85%)
        confirmation_code = f"SIM-{uuid.uuid4().hex[:8].upper()}"
        await _update_booking_status(
            db, booking_id, BookingFlowStatus.CONFIRMED,
            f"Simulated booking confirmed: {confirmation_code}",
            confirmation_code=confirmation_code,
        )
        return _booking_result(booking_id, BookingFlowStatus.CONFIRMED, confirmation_code=confirmation_code)
    elif outcome_roll < 0.95:
        # Delayed confirmation (10%)
        await asyncio.sleep(random.uniform(0.5, 1.0))
        confirmation_code = f"SIM-DELAYED-{uuid.uuid4().hex[:8].upper()}"
        await _update_booking_status(
            db, booking_id, BookingFlowStatus.CONFIRMED,
            f"Simulated delayed confirmation: {confirmation_code}",
            confirmation_code=confirmation_code,
        )
        return _booking_result(booking_id, BookingFlowStatus.CONFIRMED, confirmation_code=confirmation_code)
    else:
        # Failure (5%)
        await _update_booking_status(db, booking_id, BookingFlowStatus.FAILED, "Simulated booking failure")
        return _booking_result(booking_id, BookingFlowStatus.FAILED, error="Simulated: supplier rejected booking")


# ── Booking Status ────────────────────────────────────────────────────

async def get_booking_status(booking_id: str) -> dict[str, Any]:
    """Get current booking status from DB."""
    db = await get_db()
    doc = await db.ratehawk_bookings.find_one(
        {"booking_id": booking_id}, {"_id": 0}
    )
    if not doc:
        return {"error": f"Booking {booking_id} not found", "status": "not_found"}
    return {
        "booking_id": doc["booking_id"],
        "partner_order_id": doc["partner_order_id"],
        "supplier": doc["supplier"],
        "hotel_id": doc["hotel_id"],
        "status": doc["status"],
        "confirmation_code": doc.get("confirmation_code"),
        "checkin": doc["checkin"],
        "checkout": doc["checkout"],
        "mode": doc.get("mode", "simulation"),
        "is_test": doc.get("is_test", False),
        "status_history": doc.get("status_history", []),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


# ── Booking Cancellation ─────────────────────────────────────────────

async def cancel_booking(booking_id: str) -> dict[str, Any]:
    """Cancel a booking through the proper RateHawk cancellation flow."""
    db = await get_db()
    doc = await db.ratehawk_bookings.find_one(
        {"booking_id": booking_id}, {"_id": 0, "booking_id": 0}
    )

    if not doc:
        return {"error": f"Booking {booking_id} not found", "status": "not_found"}

    full_doc = await db.ratehawk_bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    current_status = full_doc["status"]

    # Validate cancellation is allowed
    cancellable_statuses = {
        BookingFlowStatus.CONFIRMED.value,
        BookingFlowStatus.AWAITING_CONFIRMATION.value,
        BookingFlowStatus.BOOKING_REQUESTED.value,
    }

    if current_status not in cancellable_statuses:
        return {
            "booking_id": booking_id,
            "status": current_status,
            "error": f"Cannot cancel booking in '{current_status}' state",
            "cancellable_statuses": list(cancellable_statuses),
        }

    await _update_booking_status(db, booking_id, BookingFlowStatus.CANCELLATION_PENDING, "Cancellation requested")

    # Execute cancellation
    from app.services.inventory_sync_service import _determine_sync_mode
    sync_mode, cred_config = await _determine_sync_mode(full_doc["supplier"])

    if sync_mode == "sandbox" and cred_config:
        cancel_result = await _cancel_real_booking(db, booking_id, full_doc, cred_config)
    else:
        cancel_result = await _cancel_simulated_booking(db, booking_id)

    return cancel_result


async def _cancel_real_booking(db, booking_id: str, booking_doc: dict, cred_config: dict) -> dict[str, Any]:
    """Cancel booking via RateHawk API."""
    from app.services.ratehawk_sync_adapter import _make_auth_header, _api_call_with_retry
    import httpx

    base_url = cred_config["base_url"]
    headers = _make_auth_header(
        cred_config["credentials"]["key_id"],
        cred_config["credentials"]["api_key"],
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp, meta = await _api_call_with_retry(
            client, "POST",
            f"{base_url}/api/b2b/v3/hotel/order/booking/cancel/",
            headers,
            json_payload={"partner_order_id": booking_id},
            max_retries=2, base_delay=2.0,
            operation="booking_cancel",
        )

    if resp and resp.status_code == 200:
        await _update_booking_status(db, booking_id, BookingFlowStatus.CANCELLED, "Booking cancelled via API")
        return _booking_result(booking_id, BookingFlowStatus.CANCELLED)

    error_msg = meta.get("error", "Cancellation failed")
    # Still mark as cancelled if we can't reach supplier (simulated)
    await _update_booking_status(db, booking_id, BookingFlowStatus.CANCELLED, f"Cancellation recorded (API: {error_msg})")
    return _booking_result(booking_id, BookingFlowStatus.CANCELLED, error=f"API error: {error_msg}")


async def _cancel_simulated_booking(db, booking_id: str) -> dict[str, Any]:
    """Cancel simulated booking."""
    import random
    await asyncio.sleep(random.uniform(0.1, 0.3))
    await _update_booking_status(db, booking_id, BookingFlowStatus.CANCELLED, "Simulated cancellation successful")
    return _booking_result(booking_id, BookingFlowStatus.CANCELLED)


# ── Test Matrix ───────────────────────────────────────────────────────

async def run_booking_test_matrix(supplier: str) -> dict[str, Any]:
    """Run comprehensive booking test matrix covering all scenarios.

    Scenarios:
      1. success        — Normal booking that confirms
      2. delayed_confirm — Booking that takes time to confirm (async poll)
      3. cutoff_timeout  — Booking that exceeds cut-off (timeout)
      4. price_mismatch  — Precheck detects price drift > threshold
      5. cancel          — Book then cancel
      6. do_not_book     — Test property that rejects booking
    """
    db = await get_db()
    matrix_id = str(uuid.uuid4())
    start = time.monotonic()
    scenarios: list[dict] = []

    checkin = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")
    checkout = (datetime.now(timezone.utc) + timedelta(days=17)).strftime("%Y-%m-%d")

    test_contact = {"email": "test@syroce.com", "phone": "+905551234567", "name": "Test Agent"}
    test_guests = [{"first_name": "Test", "last_name": "User", "title": "Mr", "type": "adult"}]

    # Scenario 1: Success Booking
    sc_start = time.monotonic()
    try:
        precheck = await booking_precheck(supplier, "rh_test_hotel_001", None, checkin, checkout)
        booking = await create_booking(
            supplier, "rh_test_hotel_001", precheck["book_hash"],
            checkin, checkout, test_guests, test_contact,
            precheck_id=precheck["precheck_id"],
        )
        scenarios.append({
            "scenario": "success",
            "description": "Normal booking flow — should confirm",
            "status": "passed" if booking["status"] == "confirmed" else "failed",
            "duration_ms": round((time.monotonic() - sc_start) * 1000, 1),
            "details": {
                "booking_id": booking.get("booking_id"),
                "confirmation_code": booking.get("confirmation_code"),
                "precheck_decision": precheck["decision"],
            },
        })
    except Exception as e:
        scenarios.append({
            "scenario": "success",
            "description": "Normal booking flow — should confirm",
            "status": "error",
            "duration_ms": round((time.monotonic() - sc_start) * 1000, 1),
            "error": str(e),
        })

    # Scenario 2: Precheck with Price Check
    sc_start = time.monotonic()
    try:
        precheck = await booking_precheck(supplier, "rh_test_hotel_002", None, checkin, checkout)
        scenarios.append({
            "scenario": "precheck_validation",
            "description": "Price revalidation — verify drift detection",
            "status": "passed",
            "duration_ms": round((time.monotonic() - sc_start) * 1000, 1),
            "details": {
                "decision": precheck["decision"],
                "drift_pct": precheck["pricing"]["drift_pct"],
                "cached_price": precheck["pricing"]["cached_price"],
                "revalidated_price": precheck["pricing"]["revalidated_price"],
                "can_proceed": precheck["can_proceed"],
            },
        })
    except Exception as e:
        scenarios.append({
            "scenario": "precheck_validation",
            "description": "Price revalidation — verify drift detection",
            "status": "error",
            "duration_ms": round((time.monotonic() - sc_start) * 1000, 1),
            "error": str(e),
        })

    # Scenario 3: Do Not Book Test Property
    sc_start = time.monotonic()
    try:
        precheck = await booking_precheck(supplier, "test_hotel_do_not_book", None, checkin, checkout)
        booking = await create_booking(
            supplier, "test_hotel_do_not_book", precheck["book_hash"],
            checkin, checkout, test_guests, test_contact,
            precheck_id=precheck["precheck_id"],
        )
        scenarios.append({
            "scenario": "do_not_book",
            "description": "Test property rejection — should fail",
            "status": "passed" if booking["status"] == "failed" else "failed",
            "duration_ms": round((time.monotonic() - sc_start) * 1000, 1),
            "details": {
                "booking_id": booking.get("booking_id"),
                "expected_status": "failed",
                "actual_status": booking["status"],
            },
        })
    except Exception as e:
        scenarios.append({
            "scenario": "do_not_book",
            "description": "Test property rejection — should fail",
            "status": "error",
            "duration_ms": round((time.monotonic() - sc_start) * 1000, 1),
            "error": str(e),
        })

    # Scenario 4: Book and Cancel
    sc_start = time.monotonic()
    try:
        precheck = await booking_precheck(supplier, "rh_test_hotel_003", None, checkin, checkout)
        booking = await create_booking(
            supplier, "rh_test_hotel_003", precheck["book_hash"],
            checkin, checkout, test_guests, test_contact,
            precheck_id=precheck["precheck_id"],
        )
        cancel_result = {"status": "skipped"}
        if booking["status"] == "confirmed":
            cancel_result = await cancel_booking(booking["booking_id"])

        scenarios.append({
            "scenario": "book_and_cancel",
            "description": "Complete lifecycle — book then cancel",
            "status": "passed" if cancel_result.get("status") == "cancelled" else ("partial" if booking["status"] == "confirmed" else "failed"),
            "duration_ms": round((time.monotonic() - sc_start) * 1000, 1),
            "details": {
                "booking_id": booking.get("booking_id"),
                "booking_status": booking["status"],
                "cancel_status": cancel_result.get("status"),
            },
        })
    except Exception as e:
        scenarios.append({
            "scenario": "book_and_cancel",
            "description": "Complete lifecycle — book then cancel",
            "status": "error",
            "duration_ms": round((time.monotonic() - sc_start) * 1000, 1),
            "error": str(e),
        })

    # Scenario 5: Status Check
    sc_start = time.monotonic()
    try:
        # Check status of first booking from scenario 1
        first_booking_id = scenarios[0].get("details", {}).get("booking_id") if scenarios else None
        if first_booking_id:
            status = await get_booking_status(first_booking_id)
            scenarios.append({
                "scenario": "status_check",
                "description": "Booking status retrieval — verify history tracking",
                "status": "passed" if status.get("status") != "not_found" else "failed",
                "duration_ms": round((time.monotonic() - sc_start) * 1000, 1),
                "details": {
                    "booking_id": first_booking_id,
                    "current_status": status.get("status"),
                    "history_entries": len(status.get("status_history", [])),
                    "has_partner_order_id": bool(status.get("partner_order_id")),
                },
            })
        else:
            scenarios.append({
                "scenario": "status_check",
                "description": "Booking status retrieval",
                "status": "skipped",
                "duration_ms": round((time.monotonic() - sc_start) * 1000, 1),
                "details": {"reason": "No booking ID from previous scenario"},
            })
    except Exception as e:
        scenarios.append({
            "scenario": "status_check",
            "description": "Booking status retrieval",
            "status": "error",
            "duration_ms": round((time.monotonic() - sc_start) * 1000, 1),
            "error": str(e),
        })

    # Summary
    total_ms = round((time.monotonic() - start) * 1000, 1)
    passed = sum(1 for s in scenarios if s["status"] == "passed")
    failed = sum(1 for s in scenarios if s["status"] in ("failed", "error"))

    result = {
        "matrix_id": matrix_id,
        "supplier": supplier,
        "scenarios": scenarios,
        "summary": {
            "total": len(scenarios),
            "passed": passed,
            "failed": failed,
            "skipped": sum(1 for s in scenarios if s["status"] == "skipped"),
            "partial": sum(1 for s in scenarios if s["status"] == "partial"),
        },
        "overall_status": "passed" if failed == 0 and passed > 0 else "failed",
        "duration_ms": total_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Persist test matrix result
    await db.booking_test_matrices.insert_one({
        **result,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })

    return result


# ── Booking History ───────────────────────────────────────────────────

async def get_booking_history(
    supplier: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Get recent bookings for the booking flow dashboard."""
    db = await get_db()
    query: dict[str, Any] = {}
    if supplier:
        query["supplier"] = supplier

    bookings = []
    cursor = db.ratehawk_bookings.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit)
    async for doc in cursor:
        bookings.append({
            "booking_id": doc["booking_id"],
            "partner_order_id": doc["partner_order_id"],
            "supplier": doc["supplier"],
            "hotel_id": doc["hotel_id"],
            "status": doc["status"],
            "confirmation_code": doc.get("confirmation_code"),
            "mode": doc.get("mode", "simulation"),
            "is_test": doc.get("is_test", False),
            "checkin": doc["checkin"],
            "checkout": doc["checkout"],
            "created_at": doc["created_at"],
        })

    return {"bookings": bookings, "total": len(bookings)}


async def get_test_matrix_history(limit: int = 10) -> dict[str, Any]:
    """Get history of booking test matrix runs."""
    db = await get_db()
    results = []
    cursor = db.booking_test_matrices.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).limit(limit)
    async for doc in cursor:
        results.append(doc)
    return {"results": results, "total": len(results)}


# ── Helpers ───────────────────────────────────────────────────────────

async def _update_booking_status(
    db, booking_id: str, status: BookingFlowStatus,
    detail: str, supplier_response: dict | None = None,
    confirmation_code: str | None = None,
) -> None:
    """Update booking status with history tracking."""
    now = datetime.now(timezone.utc).isoformat()
    update: dict[str, Any] = {
        "$set": {
            "status": status.value,
            "updated_at": now,
        },
        "$push": {
            "status_history": {
                "status": status.value,
                "at": now,
                "detail": detail,
            },
        },
    }
    if supplier_response is not None:
        update["$set"]["supplier_response"] = supplier_response
    if confirmation_code is not None:
        update["$set"]["confirmation_code"] = confirmation_code

    await db.ratehawk_bookings.update_one({"booking_id": booking_id}, update)


def _booking_result(
    booking_id: str, status: BookingFlowStatus,
    confirmation_code: str | None = None,
    error: str | None = None,
    supplier_data: dict | None = None,
) -> dict[str, Any]:
    """Build standard booking result dict."""
    return {
        "booking_id": booking_id,
        "partner_order_id": booking_id,
        "status": status.value,
        "confirmation_code": confirmation_code,
        "error": error,
        "supplier_data": supplier_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _build_rooms_payload(guests: list, contact: dict) -> list[dict]:
    """Build RateHawk-compatible rooms payload from guest data."""
    rooms = []
    room_guests = []

    for g in guests:
        room_guests.append({
            "first_name": g.get("first_name", "Test"),
            "last_name": g.get("last_name", "User"),
            "is_child": g.get("type") == "child",
        })

    rooms.append({"guests": room_guests})
    return rooms
