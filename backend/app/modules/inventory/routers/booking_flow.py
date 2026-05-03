"""Inventory Booking Flow — precheck, create, status, cancel, test-matrix.

Prefix: /api/inventory
Endpoints:
  POST /booking/precheck                — Pre-booking price revalidation
  POST /booking/create                  — Create booking (ETG v3 flow)
  GET  /booking/{id}/status             — Poll booking status
  POST /booking/{id}/cancel             — Cancel booking
  POST /booking/test-matrix             — Run booking test matrix
  GET  /booking/history                 — Booking history
  GET  /booking/test-matrix/history     — Test matrix history
  POST /booking/test                    — E2E booking lifecycle test
  GET  /booking/test/history            — E2E test history
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import require_roles

router = APIRouter(prefix="/api/inventory", tags=["inventory-booking"])

_ADMIN_ROLES = ["super_admin", "admin"]


class SyncTriggerPayload(BaseModel):
    supplier: str


class BookingPrecheckPayload(BaseModel):
    supplier: str
    hotel_id: str
    book_hash: str | None = None
    checkin: str
    checkout: str
    guests: int = 2
    currency: str = "EUR"


class BookingCreatePayload(BaseModel):
    supplier: str
    hotel_id: str
    book_hash: str
    checkin: str
    checkout: str
    guests: list[dict] = []
    contact: dict = {}
    user_ip: str = "127.0.0.1"
    currency: str = "EUR"
    precheck_id: str | None = None


# ── E2E Booking Test ──────────────────────────────────────────────────

@router.post("/booking/test")
async def booking_e2e_test(
    payload: SyncTriggerPayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Run E2E booking lifecycle test for a supplier."""
    from app.services.supplier_booking_test_service import run_booking_e2e_test
    return await run_booking_e2e_test(payload.supplier)


@router.get("/booking/test/history")
async def booking_test_history(
    supplier: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get history of E2E booking tests."""
    from app.services.supplier_booking_test_service import get_booking_test_history
    return await get_booking_test_history(supplier, limit)


# ── RateHawk Booking Flow (P0) ───────────────────────────────────────

@router.post("/booking/precheck")
async def booking_precheck_endpoint(
    payload: BookingPrecheckPayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Pre-booking price revalidation (ETG prebook equivalent)."""
    from app.services.ratehawk_booking_service import booking_precheck
    return await booking_precheck(
        supplier=payload.supplier,
        hotel_id=payload.hotel_id,
        book_hash=payload.book_hash,
        checkin=payload.checkin,
        checkout=payload.checkout,
        guests=payload.guests,
        currency=payload.currency,
    )


@router.post("/booking/create")
async def booking_create_endpoint(
    payload: BookingCreatePayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Create booking following ETG v3 flow."""
    from app.services.ratehawk_booking_service import create_booking
    return await create_booking(
        supplier=payload.supplier,
        hotel_id=payload.hotel_id,
        book_hash=payload.book_hash,
        checkin=payload.checkin,
        checkout=payload.checkout,
        guests=payload.guests,
        contact=payload.contact,
        user_ip=payload.user_ip,
        currency=payload.currency,
        precheck_id=payload.precheck_id,
    )


@router.get("/booking/{booking_id}/status")
async def booking_status_endpoint(
    booking_id: str,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get booking status with full history."""
    from app.services.ratehawk_booking_service import get_booking_status
    return await get_booking_status(booking_id)


@router.post("/booking/{booking_id}/cancel")
async def booking_cancel_endpoint(
    booking_id: str,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Cancel a booking through proper cancellation flow."""
    from app.services.ratehawk_booking_service import cancel_booking
    return await cancel_booking(booking_id)


@router.post("/booking/test-matrix")
async def booking_test_matrix_endpoint(
    payload: SyncTriggerPayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Run comprehensive booking test matrix."""
    from app.services.ratehawk_booking_service import run_booking_test_matrix
    return await run_booking_test_matrix(payload.supplier)


@router.get("/booking/history")
async def booking_history_endpoint(
    supplier: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get booking flow history."""
    from app.services.ratehawk_booking_service import get_booking_history
    return await get_booking_history(supplier, limit)


@router.get("/booking/test-matrix/history")
async def test_matrix_history_endpoint(
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get history of booking test matrix runs."""
    from app.services.ratehawk_booking_service import get_test_matrix_history
    return await get_test_matrix_history(limit)
