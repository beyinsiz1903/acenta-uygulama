from __future__ import annotations

from typing import Any, Optional

from app.utils import now_utc
from app.services.ops_tasks import OpsTaskService


class OpsPlaybookEngine:
    """Ops Playbook for refund cases (Phase 2.3).

    Listens to refund lifecycle events and maintains ops_tasks accordingly.
    """

    def __init__(self, db):
        self.db = db
        self.tasks = OpsTaskService(db)

    async def _create_or_get(
        self,
        organization_id: str,
        *,
        case_id: str,
        booking_id: Optional[str],
        task_type: str,
        title: str,
        sla_hours: Optional[float],
        priority: str = "normal",
        actor_email: Optional[str] = None,
        actor_id: Optional[str] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> Optional[dict]:
        now = now_utc()
        due_at = None
        if sla_hours is not None:
            from datetime import timedelta

            due_at = now + timedelta(hours=sla_hours)
        return await self.tasks.ensure_single_open_task(
            organization_id,
            entity_type="refund_case",
            entity_id=case_id,
            booking_id=booking_id,
            task_type=task_type,
            title=title,
            description=None,
            priority=priority,
            due_at=due_at,
            sla_hours=sla_hours,
            assignee_email=None,
            assignee_actor_id=None,
            tags=None,
            meta=meta or {},
            created_by_email=actor_email,
            created_by_actor_id=actor_id,
        )

    async def on_refund_created(
        self,
        organization_id: str,
        *,
        case_id: str,
        booking_id: Optional[str],
        actor_email: Optional[str],
        actor_id: Optional[str],
    ) -> None:
        # Initial review step1 within 24h
        await self._create_or_get(
            organization_id,
            case_id=case_id,
            booking_id=booking_id,
            task_type="refund_review_step1",
            title="Refund 1. seviye inceleme",
            sla_hours=24.0,
            priority="normal",
            actor_email=actor_email,
            actor_id=actor_id,
            meta={"source": "refund_created"},
        )

    async def on_refund_step1(
        self,
        organization_id: str,
        *,
        case_id: str,
        booking_id: Optional[str],
        actor_email: Optional[str],
        actor_id: Optional[str],
    ) -> None:
        # Complete step1 review and open step2
        await self.tasks.mark_done_if_exists(
            organization_id,
            entity_type="refund_case",
            entity_id=case_id,
            task_type="refund_review_step1",
            updated_by_email=actor_email,
        )
        await self._create_or_get(
            organization_id,
            case_id=case_id,
            booking_id=booking_id,
            task_type="refund_review_step2",
            title="Refund 2. seviye inceleme",
            sla_hours=24.0,
            priority="normal",
            actor_email=actor_email,
            actor_id=actor_id,
            meta={"source": "refund_step1"},
        )

    async def on_refund_step2(
        self,
        organization_id: str,
        *,
        case_id: str,
        booking_id: Optional[str],
        actor_email: Optional[str],
        actor_id: Optional[str],
    ) -> None:
        # Complete step2 review and open payment task
        await self.tasks.mark_done_if_exists(
            organization_id,
            entity_type="refund_case",
            entity_id=case_id,
            task_type="refund_review_step2",
            updated_by_email=actor_email,
        )
        await self._create_or_get(
            organization_id,
            case_id=case_id,
            booking_id=booking_id,
            task_type="refund_payment",
            title="Refund ödeme işlemi",
            sla_hours=48.0,
            priority="high",
            actor_email=actor_email,
            actor_id=actor_id,
            meta={"source": "refund_step2"},
        )

    async def on_refund_marked_paid(
        self,
        organization_id: str,
        *,
        case_id: str,
        booking_id: Optional[str],
        actor_email: Optional[str],
        actor_id: Optional[str],
    ) -> None:
        # Complete payment and open close task
        await self.tasks.mark_done_if_exists(
            organization_id,
            entity_type="refund_case",
            entity_id=case_id,
            task_type="refund_payment",
            updated_by_email=actor_email,
        )
        await self._create_or_get(
            organization_id,
            case_id=case_id,
            booking_id=booking_id,
            task_type="refund_close",
            title="Refund case kapatma",
            sla_hours=24.0,
            priority="normal",
            actor_email=actor_email,
            actor_id=actor_id,
            meta={"source": "refund_paid"},
        )

    async def on_refund_rejected(
        self,
        organization_id: str,
        *,
        case_id: str,
        booking_id: Optional[str],
        actor_email: Optional[str],
        actor_id: Optional[str],
    ) -> None:
        # Cancel any open review tasks and open close task
        await self.tasks.cancel_all_for_entity(
            organization_id,
            entity_type="refund_case",
            entity_id=case_id,
            updated_by_email=actor_email,
        )
        await self._create_or_get(
            organization_id,
            case_id=case_id,
            booking_id=booking_id,
            task_type="refund_close",
            title="Refund case kapatma",
            sla_hours=24.0,
            priority="normal",
            actor_email=actor_email,
            actor_id=actor_id,
            meta={"source": "refund_rejected"},
        )

    async def on_refund_closed(
        self,
        organization_id: str,
        *,
        case_id: str,
        booking_id: Optional[str],
        actor_email: Optional[str],
        actor_id: Optional[str],
    ) -> None:
        # Mark all remaining tasks as done when refund case is closed
        from datetime import datetime

        now = now_utc()
        q = {
            "organization_id": organization_id,
            "entity_type": "refund_case",
            "entity_id": case_id,
            "status": {"$in": ["open", "in_progress"]},
        }
        cursor = self.db.ops_tasks.find(q)
        docs = await cursor.to_list(length=500)
        for d in docs:
            await self.db.ops_tasks.update_one(
                {"_id": d["_id"]},
                {
                    "$set": {
                        "status": "done",
                        "updated_at": now,
                        "updated_by_email": actor_email,
                        "is_overdue": False,
                    }
                },
            )
