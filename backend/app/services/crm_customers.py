from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase as Database


def _public_customer(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    data = dict(doc)
    data.pop("_id", None)
    return data


def create_customer(db: Database, organization_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow()
    customer_id = f"cust_{uuid4().hex}"
    doc = {
        "id": customer_id,
        "organization_id": organization_id,
        "type": data.get("type", "individual"),
        "name": data["name"],
        "tc_vkn": data.get("tc_vkn"),
        "tags": data.get("tags", []),
        "contacts": data.get("contacts", []),
        "assigned_user_id": data.get("assigned_user_id"),
        "created_at": now,
        "updated_at": now,
    }
    db.customers.insert_one(doc)
    return _public_customer(doc)


async def list_customers(
    db: Database,
    organization_id: str,
    *,
    search: Optional[str] = None,
    cust_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Dict[str, Any]], int]:
    q: Dict[str, Any] = {"organization_id": organization_id}

    if cust_type:
        q["type"] = cust_type

    if tags:
        q["tags"] = {"$in": tags}

    if search:
        s = search.strip()
        q["$or"] = [
            {"name": {"$regex": s, "$options": "i"}},
            {"contacts.value": {"$regex": s, "$options": "i"}},
        ]

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 25
    if page_size > 100:
        page_size = 100

    skip = (page - 1) * page_size

    total = await db.customers.count_documents(q)
    cursor = (
        db.customers.find(q, {"_id": 0})
        .sort([("updated_at", -1)])
        .skip(skip)
        .limit(page_size)
    )
    items = await cursor.to_list(length=page_size)
    return items, total


async def get_customer(db: Database, organization_id: str, customer_id: str) -> Optional[Dict[str, Any]]:
    doc = await db.customers.find_one({"organization_id": organization_id, "id": customer_id}, {"_id": 0})
    return doc


async def patch_customer(
    db: Database,
    organization_id: str,
    customer_id: str,
    patch: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    update = {k: v for k, v in patch.items() if v is not None}
    if not update:
        return await get_customer(db, organization_id, customer_id)

    update["updated_at"] = datetime.utcnow()

    res = await db.customers.find_one_and_update(
        {"organization_id": organization_id, "id": customer_id},
        {"$set": update},
        projection={"_id": 0},
        return_document=True,
    )
    return res


async def get_customer_detail(
    db: Database,
    organization_id: str,
    customer_id: str,
) -> Optional[Dict[str, Any]]:
    customer = await get_customer(db, organization_id, customer_id)
    if not customer:
        return None

    recent_bookings = []
    open_deals = []
    open_tasks = []

    return {
        "customer": customer,
        "recent_bookings": recent_bookings,
        "open_deals": open_deals,
        "open_tasks": open_tasks,
    }
