from __future__ import annotations

from typing import Any, Optional

from bson import ObjectId

from app.utils import now_utc


class OpsTaskService:
    """Service for ops_tasks (Phase 2.3 Ops Playbook).

    Currently scoped to refund_case entities but designed to be generic.
    """

    def __init__(self, db):
        self.db = db

    def _collection(self):
        return self.db.ops_tasks

    async def create_task(
        self,
        organization_id: str,
        *,
        entity_type: str,
        entity_id: str,
        booking_id: Optional[str],
        task_type: str,
        title: str,
        description: Optional[str],
        priority: str,
        due_at: Optional[Any],
        sla_hours: Optional[float],
        assignee_email: Optional[str],
        assignee_actor_id: Optional[str],
        tags: Optional[list[str]] = None,
        meta: Optional[dict[str, Any]] = None,
        created_by_email: Optional[str] = None,
        created_by_actor_id: Optional[str] = None,
    ) -> dict:
        now = now_utc()
        doc = {
            "organization_id": organization_id,
            "created_at": now,
            "created_by_email": created_by_email,
            "created_by_actor_id": created_by_actor_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "booking_id": booking_id,
            "task_type": task_type,
            "title": title,
            "description": description,
            "status": "open",
            "priority": priority or "normal",
            "due_at": due_at,
            "sla_hours": sla_hours,
            "is_overdue": bool(due_at and due_at < now),
            "assignee_email": assignee_email,
            "assignee_actor_id": assignee_actor_id,
            "tags": tags or [],
            "meta": meta or {},
            "updated_at": now,
            "updated_by_email": created_by_email,
        }
        res = await self._collection().insert_one(doc)
        return await self.get_task(organization_id, str(res.inserted_id))

    async def get_task(self, organization_id: str, task_id: str) -> Optional[dict]:
        try:
            oid = ObjectId(task_id)
        except Exception:
            return None
        doc = await self._collection().find_one({"_id": oid, "organization_id": organization_id})
        if not doc:
            return None
        doc["task_id"] = str(doc.pop("_id"))
        return doc

    async def list_tasks(
        self,
        organization_id: str,
        *,
        status: Optional[list[str]] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        booking_id: Optional[str] = None,
        assignee_email: Optional[str] = None,
        overdue: Optional[bool] = None,
        limit: int = 50,
    ) -> list[dict]:
        q: dict[str, Any] = {"organization_id": organization_id}
        if status:
            q["status"] = {"$in": status}
        if entity_type:
            q["entity_type"] = entity_type
        if entity_id:
            q["entity_id"] = entity_id
        if booking_id:
            q["booking_id"] = booking_id
        if assignee_email:
            q["assignee_email"] = assignee_email
        if overdue is True:
            from datetime import datetime
            now = now_utc()
            q["status"] = {"$in": ["open", "in_progress"]}
            q["due_at"] = {"$lt": now}
        cursor = (
            self._collection()
            .find(q)
            .sort("due_at", 1)
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        items: list[dict] = []
        for d in docs:
            d["task_id"] = str(d.pop("_id"))
            items.append(d)
        return items

    async def update_task(
        self,
        organization_id: str,
        task_id: str,
        updates: dict[str, Any],
        updated_by_email: Optional[str],
    ) -> Optional[dict]:
        try:
            oid = ObjectId(task_id)
        except Exception:
            return None
        now = now_utc()
        doc = await self._collection().find_one({"_id": oid, "organization_id": organization_id})
        if not doc:
            return None
        # track status change
        status_from = doc.get("status")
        status_to = updates.get("status", status_from)
        set_doc: dict[str, Any] = {**updates}
        set_doc["updated_at"] = now
        set_doc["updated_by_email"] = updated_by_email
        if "due_at" in updates or "status" in updates:
            due_at = updates.get("due_at", doc.get("due_at"))
            if status_to in {"open", "in_progress"} and due_at is not None:
                set_doc["is_overdue"] = due_at < now
            else:
                set_doc["is_overdue"] = False
        await self._collection().update_one(
            {"_id": oid, "organization_id": organization_id},
            {"$set": set_doc},
        )
        updated = await self._collection().find_one({"_id": oid})
        if not updated:
            return None
        updated["task_id"] = str(updated.pop("_id"))
        updated["_status_from"] = status_from
        updated["_status_to"] = status_to
        return updated

    async def mark_done_if_exists(
        self,
        organization_id: str,
        *,
        entity_type: str,
        entity_id: str,
        task_type: str,
        updated_by_email: Optional[str],
    ) -> Optional[dict]:
        q = {
            "organization_id": organization_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "task_type": task_type,
            "status": {"$in": ["open", "in_progress"]},
        }
        doc = await self._collection().find_one(q)
        if not doc:
            return None
        return await self.update_task(
            organization_id,
            str(doc["_id"]),
            {"status": "done"},
            updated_by_email=updated_by_email,
        )

    async def cancel_all_for_entity(
        self,
        organization_id: str,
        *,
        entity_type: str,
        entity_id: str,
        updated_by_email: Optional[str],
    ) -> list[dict]:
        now = now_utc()
        q = {
            "organization_id": organization_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "status": {"$in": ["open", "in_progress"]},
        }
        cursor = self._collection().find(q)
        docs = await cursor.to_list(length=500)
        results: list[dict] = []
        for d in docs:
            await self._collection().update_one(
                {"_id": d["_id"]},
                {
                    "$set": {
                        "status": "cancelled",
                        "updated_at": now,
                        "updated_by_email": updated_by_email,
                        "is_overdue": False,
                    }
                },
            )
            d["_status_from"] = d.get("status")
            d["_status_to"] = "cancelled"
            d["task_id"] = str(d.pop("_id"))
            results.append(d)
        return results

    async def ensure_single_open_task(
        self,
        organization_id: str,
        *,
        entity_type: str,
        entity_id: str,
        booking_id: Optional[str],
        task_type: str,
        title: str,
        description: Optional[str],
        priority: str,
        due_at: Optional[Any],
        sla_hours: Optional[float],
        assignee_email: Optional[str],
        assignee_actor_id: Optional[str],
        tags: Optional[list[str]],
        meta: Optional[dict[str, Any]],
        created_by_email: Optional[str],
        created_by_actor_id: Optional[str],
    ) -> Optional[dict]:
        q = {
            "organization_id": organization_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "task_type": task_type,
            "status": {"$in": ["open", "in_progress"]},
        }
        existing = await self._collection().find_one(q)
        if existing:
            existing["task_id"] = str(existing.pop("_id"))
            return existing
        return await self.create_task(
            organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            booking_id=booking_id,
            task_type=task_type,
            title=title,
            description=description,
            priority=priority,
            due_at=due_at,
            sla_hours=sla_hours,
            assignee_email=assignee_email,
            assignee_actor_id=assignee_actor_id,
            tags=tags,
            meta=meta,
            created_by_email=created_by_email,
            created_by_actor_id=created_by_actor_id,
        )
