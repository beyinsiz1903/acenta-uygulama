from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db import get_db
from app.errors import AppError

logger = logging.getLogger(__name__)


class NotificationService:
    """In-app notification engine – hybrid rule + event based."""

    # ─── Create notification (event-based) ────────────────────────
    async def create(
        self,
        *,
        tenant_id: str,
        user_id: Optional[str] = None,
        notification_type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
    ) -> Dict[str, Any]:
        db = await get_db()
        now = datetime.now(timezone.utc)
        notif_id = f"ntf_{uuid.uuid4().hex}"

        valid_types = ["quota_warning", "payment_overdue", "case_open", "system", "b2b_match", "payment_recorded", "onboarding"]
        if notification_type not in valid_types:
            notification_type = "system"

        doc = {
            "_id": notif_id,
            "tenant_id": tenant_id,
            "user_id": user_id,  # None = broadcast to all tenant users
            "type": notification_type,
            "title": title,
            "message": message,
            "is_read": False,
            "link": link or "",
            "created_at": now,
        }
        await db.notifications.insert_one(doc)
        doc["id"] = doc.pop("_id")
        return doc

    # ─── List notifications ───────────────────────────────────────
    async def list_for_user(
        self,
        tenant_id: str,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 20,
        unread_only: bool = False,
    ) -> Dict[str, Any]:
        db = await get_db()
        query: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "$or": [{"user_id": user_id}, {"user_id": None}],
        }
        if unread_only:
            query["is_read"] = False

        total = await db.notifications.count_documents(query)
        cursor = db.notifications.find(query).sort("created_at", -1).skip(skip).limit(limit)
        items = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id", ""))
            items.append(doc)

        unread = await db.notifications.count_documents({**query, "is_read": False}) if not unread_only else total
        return {"items": items, "total": total, "unread_count": unread}

    # ─── Mark as read ─────────────────────────────────────────────
    async def mark_read(self, notification_id: str, tenant_id: str) -> bool:
        db = await get_db()
        result = await db.notifications.update_one(
            {"_id": notification_id, "tenant_id": tenant_id},
            {"$set": {"is_read": True}},
        )
        return result.modified_count > 0

    async def mark_all_read(self, tenant_id: str, user_id: str) -> int:
        db = await get_db()
        result = await db.notifications.update_many(
            {
                "tenant_id": tenant_id,
                "$or": [{"user_id": user_id}, {"user_id": None}],
                "is_read": False,
            },
            {"$set": {"is_read": True}},
        )
        return result.modified_count

    # ─── Unread count ─────────────────────────────────────────────
    async def unread_count(self, tenant_id: str, user_id: str) -> int:
        db = await get_db()
        return await db.notifications.count_documents({
            "tenant_id": tenant_id,
            "$or": [{"user_id": user_id}, {"user_id": None}],
            "is_read": False,
        })

    # ─── Rule-based triggers (call from cron/job) ─────────────────
    async def check_quota_warnings(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Check if any usage > 80% of quota and create notification."""
        db = await get_db()
        cap = await db.tenant_capabilities.find_one({"tenant_id": tenant_id})
        if not cap:
            return []

        from app.constants.plan_matrix import PLAN_MATRIX
        plan = cap.get("plan", "starter")
        quotas = PLAN_MATRIX.get(plan, {}).get("quotas", {})

        notifications = []
        for quota_key, limit_val in quotas.items():
            usage = await db.usage_ledger.count_documents({"tenant_id": tenant_id, "key": quota_key})
            if limit_val > 0 and usage / limit_val >= 0.8:
                notif = await self.create(
                    tenant_id=tenant_id,
                    notification_type="quota_warning",
                    title="Kota Uyarısı",
                    message=f"{quota_key} kullanımı %{int(usage/limit_val*100)} seviyesinde.",
                    link="/app/settings",
                )
                notifications.append(notif)
        return notifications

    async def check_overdue_payments(self, tenant_id: str, org_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Check for unpaid items older than N days."""
        db = await get_db()
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)

        overdue = await db.webpos_payments.count_documents({
            "tenant_id": tenant_id,
            "organization_id": org_id,
            "status": "recorded",
            "created_at": {"$lt": cutoff},
        })
        notifications = []
        if overdue > 0:
            notif = await self.create(
                tenant_id=tenant_id,
                notification_type="payment_overdue",
                title="Ödeme Gecikme Uyarısı",
                message=f"{overdue} adet ödeme {days} günden fazla süredir bekliyor.",
                link="/app/finance/webpos",
            )
            notifications.append(notif)
        return notifications

    async def check_open_cases(self, tenant_id: str, org_id: str, hours: int = 48) -> List[Dict[str, Any]]:
        """Check for cases open > N hours."""
        db = await get_db()
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        open_cases = await db.cases.count_documents({
            "organization_id": org_id,
            "status": {"$in": ["open", "pending"]},
            "created_at": {"$lt": cutoff},
        })
        notifications = []
        if open_cases > 0:
            notif = await self.create(
                tenant_id=tenant_id,
                notification_type="case_open",
                title="Açık Vakalar",
                message=f"{open_cases} adet vaka {hours} saatten fazla süredir açık.",
                link="/app/ops/guest-cases",
            )
            notifications.append(notif)
        return notifications


notification_service = NotificationService()
