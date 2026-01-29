from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.booking_repository import BookingRepository
from app.repositories.credit_profile_repository import CreditProfileRepository
from app.repositories.task_queue_repository import TaskQueueRepository
from app.repositories.task_repository import TaskRepository


async def _get_credit_limit(db: AsyncIOMotorDatabase, organization_id: str) -> float:
    repo = CreditProfileRepository(db)
    profile = await repo.get_for_org(organization_id)
    if not profile:
        return 0.0
    return float(profile.get("credit_limit", 0.0))


async def _calculate_exposure(db: AsyncIOMotorDatabase, organization_id: str) -> float:
    """Calculate current exposure for org as sum of booked booking amounts.

    P0 simplification: currency assumed TRY; multi-currency ignored.
    """
    booking_repo = BookingRepository(db)
    # Reuse list_bookings with state filter 'booked'
    booked = await booking_repo.list_bookings(organization_id, state="booked", limit=10000)
    return float(sum(float(b.get("amount", 0.0)) for b in booked))


async def has_available_credit(db: AsyncIOMotorDatabase, organization_id: str, amount: float) -> bool:
    limit = await _get_credit_limit(db, organization_id)
    exposure = await _calculate_exposure(db, organization_id)
    return (limit - exposure) >= amount


async def create_finance_hold_task_for_booking(db: AsyncIOMotorDatabase, organization_id: str, booking_id: str) -> None:
    """Create a Finance queue task for a held booking.

    P0: attach to the org's Finance queue if it exists; if not, fail silently.
    """
    queue_repo = TaskQueueRepository(db)
    queues = await queue_repo.list_for_org(organization_id)
    finance_queue_id: str | None = None
    for q in queues:
        # org_service seeds ["Ops", "Finance"] by name
        if str(q.get("name")).lower() == "finance":
            from bson import ObjectId

            q_id = q.get("_id")
            finance_queue_id = str(q_id) if isinstance(q_id, ObjectId) else str(q_id)
            break

    if not finance_queue_id:
        return

    task_repo = TaskRepository(db)
    await task_repo.create_finance_booking_task(organization_id, finance_queue_id, booking_id)
