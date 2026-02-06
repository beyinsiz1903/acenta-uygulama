from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase as Database


async def _normalize_stage_and_status(stage: Optional[str], status: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Enforce stage/status consistency.

    - stage won -> status won
    - stage lost -> status lost
    - all other stages -> status open
    """

    if stage in {"won", "lost"}:
        status = stage
    elif status in {"won", "lost"} and stage is None:
        stage = status

    if stage not in {"won", "lost"} and status not in {"won", "lost", None}:
        pass

    if status is None:
        if stage in {"won", "lost"}:
            status = stage
        else:
            status = "open"

    return stage, status


async def create_deal(
    db: Database,
    organization_id: str,
    user_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    now = datetime.utcnow()
    deal_id = f"deal_{uuid4().hex}"

    stage, status = await _normalize_stage_and_status(data.get("stage"), data.get("status"))

    doc = {
        "id": deal_id,
        "organization_id": organization_id,
        "customer_id": data.get("customer_id"),
        "title": data.get("title"),
        "stage": stage or "lead",
        "status": status or "open",
        "amount": data.get("amount"),
        "currency": data.get("currency"),
        "owner_user_id": data.get("owner_user_id") or user_id,
        "expected_close_date": data.get("expected_close_date"),
        "next_action_at": data.get("next_action_at"),
        "won_booking_id": None,
        "created_at": now,
        "updated_at": now,
    }

    await db.crm_deals.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def list_deals(
    db: Database,
    organization_id: str,
    *,
    status: Optional[str] = "open",
    stage: Optional[str] = None,
    owner_user_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Dict[str, Any]], int]:
    q: Dict[str, Any] = {"organization_id": organization_id}

    if status:
        q["status"] = status
    if stage:
        q["stage"] = stage
    if owner_user_id:
        q["owner_user_id"] = owner_user_id
    if customer_id:
        q["customer_id"] = customer_id

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 25
    if page_size > 200:
        page_size = 200

    skip = (page - 1) * page_size

    total = await db.crm_deals.count_documents(q)
    cursor = (
        db.crm_deals.find(q, {"_id": 0})
        .sort([("updated_at", -1)])
        .skip(skip)
        .limit(page_size)
    )
    items = await cursor.to_list(length=page_size)
    return items, total


async def get_deal(
    db: Database,
    organization_id: str,
    deal_id: str,
) -> Optional[Dict[str, Any]]:
    doc = await db.crm_deals.find_one({"organization_id": organization_id, "id": deal_id}, {"_id": 0})
    return doc


async def patch_deal(
    db: Database,
    organization_id: str,
    deal_id: str,
    patch: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    update = {k: v for k, v in patch.items() if v is not None}

    stage = update.get("stage")
    status = update.get("status")

    if stage is not None or status is not None:
        stage, status = await _normalize_stage_and_status(stage, status)
        if stage is not None:
            update["stage"] = stage
        if status is not None:
            update["status"] = status

    if not update:
        return await get_deal(db, organization_id, deal_id)

    update["updated_at"] = datetime.utcnow()

    res = await db.crm_deals.find_one_and_update(
        {"organization_id": organization_id, "id": deal_id},
        {"$set": update},
        projection={"_id": 0},
        return_document=True,
    )
    return res


async def link_deal_booking(
    db: Database,
    organization_id: str,
    deal_id: str,
    booking_id: str,
) -> Optional[Dict[str, Any]]:
    now = datetime.utcnow()
    update = {
        "won_booking_id": booking_id,
        "stage": "won",
        "status": "won",
        "updated_at": now,
    }

    res = await db.crm_deals.find_one_and_update(
        {"organization_id": organization_id, "id": deal_id},
        {"$set": update},
        projection={"_id": 0},
        return_document=True,
    )
    return res
