from __future__ import annotations

import os
import random
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc

router = APIRouter(prefix="/api/dev", tags=["dev-seed-settlements"])


def _is_dev_env() -> bool:
    return os.getenv("ENABLE_DEV_ROUTERS") == "true"


@router.post(
    "/seed/settlements",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def seed_settlements(month: str, count: int = 10, user=Depends(get_current_user)):
    """Seed booking_financial_entries documents for a given month.

    This is purely for demo/testing so that settlement UI has data to work with.
    """

    if not _is_dev_env():
        raise HTTPException(status_code=403, detail="DEV_SEED_DISABLED")

    db = await get_db()
    org_id = str(user["organization_id"])

    # Ensure some agencies and hotels exist
    agencies = await db.agencies.find({"organization_id": org_id}).to_list(10)
    hotels = await db.hotels.find({"organization_id": org_id}).to_list(10)

    if not agencies or not hotels:
        raise HTTPException(status_code=400, detail="NEED_AGENCIES_AND_HOTELS_FIRST")

    statuses = ["open", "confirmed_by_agency", "confirmed_by_hotel", "closed", "disputed"]

    created = 0
    now = now_utc()

    for _ in range(max(count, 1)):
        agency = random.choice(agencies)
        hotel = random.choice(hotels)

        gross = random.randint(8000, 25000)
        commission_percent = random.choice([8.0, 10.0, 12.0])
        commission_amount = round(gross * commission_percent / 100.0, 2)
        net_amount = round(gross - commission_amount, 2)

        status = random.choice(statuses)
        disputed = status == "disputed"

        agency_confirmed_at = None
        hotel_confirmed_at = None
        if status in ("confirmed_by_agency", "closed"):
            agency_confirmed_at = now
        if status in ("confirmed_by_hotel", "closed"):
            hotel_confirmed_at = now

        doc = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "month": month,
            "agency_id": agency["_id"],
            "hotel_id": hotel["_id"],
            "gross_amount": float(gross),
            "commission_amount": float(commission_amount),
            "net_amount": float(net_amount),
            "currency": "TRY",
            "status": status,
            "disputed": disputed,
            "dispute_reason": "Seed dispute" if disputed else None,
            "disputed_at": now if disputed else None,
            "disputed_by": user.get("email") if disputed else None,
            "agency_confirmed_at": agency_confirmed_at,
            "hotel_confirmed_at": hotel_confirmed_at,
            "created_at": now,
        }

        await db.booking_financial_entries.insert_one(doc)
        created += 1

    return {"ok": True, "created": created, "month": month}
