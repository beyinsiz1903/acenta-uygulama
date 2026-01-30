from __future__ import annotations

from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.booking_repository import BookingRepository
from app.services.credit_exposure_service import _get_credit_limit, _calculate_exposure


async def get_exposure_summary(db: AsyncIOMotorDatabase, organization_id: str) -> Dict[str, Any]:
    """Return Finance exposure summary for an organization.

    Contract (v1):
    - currency: "TRY" (for now)
    - credit_limit: Standard credit limit, or None if no profile
    - total_exposure: sum of booked booking amounts (TRY)
    - available_credit: credit_limit - total_exposure, or None if no profile
    - booked_count: number of booked bookings
    """

    credit_limit = await _get_credit_limit(db, organization_id)
    total_exposure = await _calculate_exposure(db, organization_id)

    booking_repo = BookingRepository(db)
    booked = await booking_repo.list_bookings(organization_id, state="booked", limit=10000)
    booked_count = len(booked)

    available_credit: float | None
    if credit_limit is None:
        available_credit = None
    else:
        available_credit = float(credit_limit - total_exposure)

    return {
        "currency": "TRY",
        "credit_limit": credit_limit,
        "total_exposure": total_exposure,
        "available_credit": available_credit,
        "booked_count": booked_count,
    }
