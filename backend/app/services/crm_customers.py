from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase as Database


def _normalize_contacts(contacts: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not contacts:
        return []
    normalized: List[Dict[str, Any]] = []
    primary_seen = False
    for raw in contacts:
        c = dict(raw)
        if c.get("type") not in {"phone", "email"}:
            continue
        # Trim value
        value = str(c.get("value", "")).strip()
        if not value:
            continue
        c["value"] = value
        # Only one primary
        if c.get("is_primary") and not primary_seen:
            primary_seen = True
            c["is_primary"] = True
        else:
            c["is_primary"] = False
        normalized.append(c)
    return normalized


def _normalize_tags(tags: Optional[List[str]]) -> List[str]:
    if not tags:
        return []
    seen = set()
    result: List[str] = []
    for raw in tags:
        if raw is None:
            continue
        t = str(raw).strip().lower()
        if not t:
            continue
        if t in seen:
            continue
        seen.add(t)
        result.append(t)
    return result


async def create_customer(db: Database, organization_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow()
    customer_id = f"cust_{uuid4().hex}"

    tags = _normalize_tags(data.get("tags"))
    contacts = _normalize_contacts(data.get("contacts"))

    doc = {
        "id": customer_id,
        "organization_id": organization_id,
        "type": data.get("type", "individual"),
        "name": data["name"],
        "tc_vkn": data.get("tc_vkn"),
        "tags": tags,
        "contacts": contacts,
        "assigned_user_id": data.get("assigned_user_id"),
        "created_at": now,
        "updated_at": now,
    }
    await db.customers.insert_one(doc)
    doc.pop("_id", None)
    return doc


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

    if "tags" in update:
        update["tags"] = _normalize_tags(update.get("tags"))
    if "contacts" in update:
        update["contacts"] = _normalize_contacts(update.get("contacts"))

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

    recent_bookings: list[dict] = []

    # When bookings.customer_id is present, load recent bookings for this customer.
    # Sort by created_at desc; if created_at is missing, fall back to updated_at.
    booking_sort_field = "created_at"
    sample_booking = await db.bookings.find_one(
        {"organization_id": organization_id, "customer_id": customer_id},
        {"created_at": 1, "updated_at": 1},
    )
    if sample_booking and not sample_booking.get("created_at") and sample_booking.get("updated_at"):
        booking_sort_field = "updated_at"

    cursor = (
        db.bookings.find(
            {"organization_id": organization_id, "customer_id": customer_id},
            {"_id": 0},
        )
        .sort([(booking_sort_field, -1)])
        .limit(5)
    )
    recent_bookings = await cursor.to_list(length=5)

    open_deals = await db.crm_deals.find(
        {
            "organization_id": organization_id,
            "customer_id": customer_id,
            "status": "open",
        },
        {"_id": 0},
    ).sort([("updated_at", -1)]).limit(10).to_list(length=10)

    open_tasks = await db.crm_tasks.find(
        {
            "organization_id": organization_id,
            "related_type": "customer",
            "related_id": customer_id,
            "status": "open",
        },
        {"_id": 0},
    ).sort([("due_date", 1), ("updated_at", -1)]).limit(10).to_list(length=10)

    return {
        "customer": customer,
        "recent_bookings": recent_bookings,
        "open_deals": open_deals,
        "open_tasks": open_tasks,
    }
