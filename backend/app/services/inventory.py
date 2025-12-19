from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from bson import ObjectId
from pymongo import UpdateOne

from app.db import get_db
from app.utils import now_utc, to_object_id


async def upsert_inventory(org_id: str, user_email: str, payload: dict[str, Any]) -> dict[str, Any]:
    db = await get_db()

    try:
        product_oid = to_object_id(payload["product_id"])
    except Exception:
        raise ValueError("invalid product_id")

    doc = {
        "organization_id": org_id,
        "product_id": product_oid,
        "date": payload["date"],
        "capacity_total": int(payload["capacity_total"]),
        "capacity_available": int(payload["capacity_available"]),
        "price": payload.get("price"),
        "restrictions": payload.get("restrictions")
        or {"closed": False, "cta": False, "ctd": False},
        # FAZ-8
        "source": payload.get("source") or "local",
        "updated_at": now_utc(),
        "updated_by": user_email,
    }

    existing = await db.inventory.find_one(
        {
            "organization_id": org_id,
            "product_id": product_oid,
            "date": payload["date"],
        }
    )

    if existing:
        await db.inventory.update_one(
            {"_id": existing["_id"]},
            {"$set": doc, "$setOnInsert": {"created_at": now_utc(), "created_by": user_email}},
        )
        return {"status": "updated"}

    doc["created_at"] = now_utc()
    doc["created_by"] = user_email
    await db.inventory.insert_one(doc)
    return {"status": "inserted"}


async def bulk_upsert_inventory(org_id: str, user_email: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Upsert the same values for a date range (inclusive)."""
    db = await get_db()

    product_oid = to_object_id(payload["product_id"])
    start = date.fromisoformat(payload["start_date"])
    end = date.fromisoformat(payload["end_date"])
    if end < start:
        raise ValueError("end_date must be >= start_date")

    cap_total = int(payload["capacity_total"])
    cap_avail = int(payload["capacity_available"])
    price = payload.get("price")
    closed = bool(payload.get("closed"))

    ops: list[UpdateOne] = []
    cur = start

    while cur <= end:
        day_str = cur.isoformat()
        ops.append(
            UpdateOne(
                {
                    "organization_id": org_id,
                    "product_id": product_oid,
                    "date": day_str,
                },
                {
                    "$set": {
                        "capacity_total": cap_total,
                        "capacity_available": cap_avail,
                        "price": price,
                        "restrictions": {"closed": closed, "cta": False, "ctd": False},
                        # FAZ-8
                        "source": payload.get("source") or "local",
                        "updated_at": now_utc(),
                        "updated_by": user_email,
                    },
                    "$setOnInsert": {
                        "organization_id": org_id,
                        "product_id": product_oid,
                        "date": day_str,
                        "created_at": now_utc(),
                        "created_by": user_email,
                    },
                },
                upsert=True,
            )
        )
        cur += timedelta(days=1)

    if not ops:
        return {"matched": 0, "modified": 0, "upserted": 0}

    result = await db.inventory.bulk_write(ops, ordered=False)
    return {
        "matched": int(result.matched_count),
        "modified": int(result.modified_count),
        "upserted": int(len(result.upserted_ids or {})),
    }


async def consume_inventory(org_id: str, product_id: str, date_str: str, pax: int) -> bool:
    db = await get_db()
    product_oid = to_object_id(product_id)

    res = await db.inventory.find_one_and_update(
        {
            "organization_id": org_id,
            "product_id": product_oid,
            "date": date_str,
            "capacity_available": {"$gte": pax},
            "restrictions.closed": {"$ne": True},
        },
        {"$inc": {"capacity_available": -pax}, "$set": {"updated_at": now_utc()}},
        return_document=False,
    )

    return res is not None


async def release_inventory(org_id: str, product_id: ObjectId, date_str: str, pax: int) -> None:
    db = await get_db()
    await db.inventory.update_one(
        {"organization_id": org_id, "product_id": product_id, "date": date_str},
        {"$inc": {"capacity_available": pax}, "$set": {"updated_at": now_utc()}},
    )
