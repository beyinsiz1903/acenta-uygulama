from __future__ import annotations

from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc


async def upsert_inventory(org_id: str, user_email: str, payload: dict[str, Any]) -> dict[str, Any]:
    db = await get_db()

    doc = {
        "organization_id": org_id,
        "product_id": payload["product_id"],
        "date": payload["date"],
        "capacity_total": int(payload["capacity_total"]),
        "capacity_available": int(payload["capacity_available"]),
        "price": payload.get("price"),
        "restrictions": payload.get("restrictions") or {"closed": False, "cta": False, "ctd": False},
        "updated_at": now_utc(),
        "updated_by": user_email,
    }

    existing = await db.inventory.find_one({
        "organization_id": org_id,
        "product_id": payload["product_id"],
        "date": payload["date"],
    })

    if existing:
        await db.inventory.update_one({"_id": existing["_id"]}, {"$set": doc, "$setOnInsert": {"created_at": now_utc(), "created_by": user_email}})
        return {"status": "updated"}

    doc["created_at"] = now_utc()
    doc["created_by"] = user_email
    await db.inventory.insert_one(doc)
    return {"status": "inserted"}


async def consume_inventory(org_id: str, product_id: str, date_str: str, pax: int) -> bool:
    db = await get_db()

    res = await db.inventory.find_one_and_update(
        {
            "organization_id": org_id,
            "product_id": product_id,
            "date": date_str,
            "capacity_available": {"$gte": pax},
            "restrictions.closed": {"$ne": True},
        },
        {"$inc": {"capacity_available": -pax}, "$set": {"updated_at": now_utc()}},
        return_document=False,
    )

    return res is not None


async def release_inventory(org_id: str, product_id: str, date_str: str, pax: int) -> None:
    db = await get_db()
    await db.inventory.update_one(
        {"organization_id": org_id, "product_id": product_id, "date": date_str},
        {"$inc": {"capacity_available": pax}, "$set": {"updated_at": now_utc()}},
    )
