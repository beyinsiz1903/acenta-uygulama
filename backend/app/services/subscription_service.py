from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from typing import Any, Dict, Optional as _Opt

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.errors import AppError
from app.repositories.subscription_repository import SubscriptionRepository
from app.request_context import RequestContext


class SubscriptionService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._repo = SubscriptionRepository(db)

    async def get_active_for_org(self, org_id: str) -> Optional[Dict[str, Any]]:
        doc = await self._repo.get_current_for_org(org_id)
        if not doc:
            return None
        # Basic time window check
        now = datetime.now(timezone.utc)
        period_start = doc.get("period_start")
        period_end = doc.get("period_end")
        if period_start and isinstance(period_start, str):
            period_start = datetime.fromisoformat(period_start)
        if period_end and isinstance(period_end, str):
            period_end = datetime.fromisoformat(period_end)
        if period_end and period_end < now:
            # Expired subscription; treat as no active
            return None
        return doc

    async def set_subscription(
        self,
        org_id: str,
        plan_id: str,
        status: str,
        period_start: datetime,
        period_end: datetime,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        payload: Dict[str, Any] = {
            "org_id": org_id,
            "plan_id": plan_id,
            "status": status,
            "period_start": period_start,
            "period_end": period_end,
        }
        if extra:
            payload.update(extra)
        return await self._repo.upsert_subscription(payload)

    async def ensure_allowed(self, ctx: RequestContext) -> None:
        """Guard that enforces subscription status.

        - suspended/canceled  AppError(403, subscription_suspended)
        - past_due allowed but ctx.subscription_status must be set by caller
        """
        if not ctx.org_id:
            # For safety, if org_id is missing we fail closed
            raise AppError(
                status_code=403,
                code="organization_missing",
                message="Organization context missing for subscription check.",
                details=None,
            )
        doc = await self.get_active_for_org(ctx.org_id)
        if not doc:
            # No subscription configured for this organization
            if ctx.is_super_admin:
                # Super admins are allowed even without subscription (ops/debug)
                return
            raise AppError(
                status_code=403,
                code="subscription_missing",
                message="No active subscription configured for organization.",
                details={"org_id": ctx.org_id},
            )
        status = doc.get("status")
        if status in ("suspended", "canceled"):
            raise AppError(
                status_code=403,
                code="subscription_suspended",
                message="Organization subscription is suspended.",
                details={"org_id": ctx.org_id, "status": status},
            )
        # past_due and active are allowed; caller may inspect doc if needed
