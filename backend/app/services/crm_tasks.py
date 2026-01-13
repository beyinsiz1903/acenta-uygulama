from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from motor.core import AgnosticDatabase as Database

PROJECTION: Dict[str, int] = {"_id": 0}


def _clamp_pagination(page: int, page_size: int, *, default_size: int = 50, max_size: int = 100) -> tuple[int, int]:
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = default_size
    if page_size > max_size:
        page_size = max_size
    return page, page_size


def _utc_day_bounds(target: date) -> tuple[datetime, datetime]:
    start = datetime(target.year, target.month, target.day)
    end = start + timedelta(days=1)
    return start, end


def _due_filter(due: Optional[str]) -> Dict[str, Any]:
    """Build Mongo filter for due:

    - today: due_date within today (UTC)
    - overdue: due_date < now
    - week: due_date within next 7 days (UTC), incl today
    """

    if not due:
        return {}

    now = datetime.utcnow()

    if due == "today":
        start, end = _utc_day_bounds(now.date())
        return {"due_date": {"$gte": start, "$lt": end}}

    if due == "overdue":
        return {"due_date": {"$lt": now}}

    if due == "week":
        start, _ = _utc_day_bounds(now.date())
        end = start + timedelta(days=7)
        return {"due_date": {"$gte": start, "$lt": end}}

    return {}


async def create_task(db: Database, organization_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow()
    task_id = f"task_{uuid4().hex}"

    doc: Dict[str, Any] = {
        "id": task_id,
        "organization_id": organization_id,
        "owner_user_id": data.get("owner_user_id") or user_id,
        "title": (data.get("title") or "").strip(),
        "status": data.get("status") or "open",
        "priority": data.get("priority") or "normal",
        "due_date": data.get("due_date"),
        "related_type": data.get("related_type"),
        "related_id": data.get("related_id"),
        "created_at": now,
        "updated_at": now,
    }

    await db.crm_tasks.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def list_tasks(
    db: Database,
    organization_id: str,
    *,
    owner_user_id: Optional[str] = None,
    status: str = "open",
    due: Optional[str] = None,
    related_type: Optional[str] = None,
    related_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Dict[str, Any]], int]:
    page, page_size = _clamp_pagination(page, page_size, default_size=50, max_size=100)
    skip = (page - 1) * page_size

    q: Dict[str, Any] = {"organization_id": organization_id}

    if owner_user_id:
        q["owner_user_id"] = owner_user_id

    if status:
        q["status"] = status

    if related_type:
        q["related_type"] = related_type
    if related_id:
        q["related_id"] = related_id

    q.update(_due_filter(due))

    total = await db.crm_tasks.count_documents(q)

    if status == "open":
        cursor = (
            db.crm_tasks.find(q, PROJECTION)
            .sort([("due_date", 1), ("updated_at", -1)])
            .skip(skip)
            .limit(page_size)
        )
    else:
        cursor = (
            db.crm_tasks.find(q, PROJECTION)
            .sort([("updated_at", -1)])
            .skip(skip)
            .limit(page_size)
        )

    items = await cursor.to_list(length=page_size)
    return items, total


async def get_task(db: Database, organization_id: str, task_id: str) -> Optional[Dict[str, Any]]:
    return await db.crm_tasks.find_one({"organization_id": organization_id, "id": task_id}, PROJECTION)


async def patch_task(db: Database, organization_id: str, task_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    update = {k: v for k, v in patch.items() if v is not None}
    if not update:
        return await get_task(db, organization_id, task_id)

    if "title" in update and isinstance(update["title"], str):
        update["title"] = update["title"].strip()

    if "status" in update and update["status"] not in {"open", "done"}:
        update.pop("status", None)

    update["updated_at"] = datetime.utcnow()

    res = await db.crm_tasks.find_one_and_update(
        {"organization_id": organization_id, "id": task_id},
        {"$set": update},
        return_document=True,
        projection=PROJECTION,
    )
    return res
