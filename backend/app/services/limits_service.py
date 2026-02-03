from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.errors import AppError
from app.metrics import METRIC_BOOKINGS_CREATED
from app.repositories.plan_repository import PlanRepository
from app.request_context import RequestContext
from app.services.subscription_service import SubscriptionService
from app.services.usage_service import UsageService


@dataclass
class OrgPlan:
    org_id: str
    plan: Optional[dict]


class LimitsService:
    """Enforce SaaS plan limits (users, bookings, etc.)."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._subs = SubscriptionService(db)
        self._plans = PlanRepository(db)
        self._usage = UsageService(db)

    async def _load_org_plan(self, org_id: str) -> OrgPlan:
        """Return current active subscription and plan for an org.

        SubscriptionService.ensure_allowed should already have been called
        for security; this helper is for limit enforcement only.
        """
        sub = await self._subs.get_active_for_org(org_id)
        if not sub:
            return OrgPlan(org_id=org_id, plan=None)
        plan_id = sub.get("plan_id")
        plan = None
        if plan_id:
            plan = await self._plans.get_by_id(str(plan_id))
        return OrgPlan(org_id=org_id, plan=plan)

    async def enforce_max_users(self, org_id: str) -> None:
        """Enforce plan.max_users based on active user count.

        This should be called before creating a new user for an org.
        """
        if not org_id:
            return

        org_plan = await self._load_org_plan(org_id)
        plan = org_plan.plan
        if not plan or "max_users" not in plan:
            # No explicit user limit defined for plan
            return

        max_users = int(plan.get("max_users") or 0)
        if max_users <= 0:
            # 0 or negative treated as unlimited
            return

        current = await self._db.users.count_documents({
            "organization_id": org_id,
            "status": "active",
        })
        if current >= max_users:
            raise AppError(
                status_code=403,
                code="limit_exceeded",
                message="Plan user limit exceeded.",
                details={
                    "metric": "users.active",
                    "max": max_users,
                    "current": current,
                },
            )

    async def enforce_booking_limit(self, ctx: RequestContext) -> None:
        """Enforce plan.max_bookings_per_month using usage logs.

        Should be called before creating a booking.
        """
        org_id = ctx.org_id
        if not org_id:
            return

        org_plan = await self._load_org_plan(org_id)
        plan = org_plan.plan
        if not plan or "max_bookings_per_month" not in plan:
            return

        max_bookings = int(plan.get("max_bookings_per_month") or 0)
        if max_bookings <= 0:
            return

        # Month window: first day of current month to first day of next month (UTC)
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            month_end = month_start.replace(year=now.year + 1, month=1)
        else:
            month_end = month_start.replace(month=now.month + 1)

        current = await self._usage.get_monthly_count(org_id, METRIC_BOOKINGS_CREATED, month_start, month_end)
        if current >= max_bookings:
            raise AppError(
                status_code=403,
                code="limit_exceeded",
                message="Plan booking limit exceeded.",
                details={
                    "metric": METRIC_BOOKINGS_CREATED,
                    "max": max_bookings,
                    "current": current,
                },
            )
