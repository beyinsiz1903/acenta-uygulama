from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc

router = APIRouter(prefix="/api/dev", tags=["dev-seed-bookings"])


def _is_dev_env() -> bool:
    """Allow seeding only in dev/preview environments.

    We use ENABLE_DEV_ROUTERS as primary switch (already used in server.py).
    """
    return os.getenv("ENABLE_DEV_ROUTERS") == "true"


@router.post(
    "/seed/agency-bookings",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def seed_agency_bookings(count: int = 30, user=Depends(get_current_user)):
    """Seed demo agencies, hotels and bookings for financial dashboards.

    - Creates up to 3 agencies, 5 hotel links
    - Inserts ~`count` bookings with various status/payment_status
    - Fills gross_amount/commission_amount/net_amount snapshots

    Only available when ENABLE_DEV_ROUTERS=true.
    """
    if not _is_dev_env():
        raise HTTPException(status_code=403, detail="DEV_SEED_DISABLED")

    db = await get_db()
    org_id = str(user["organization_id"])

    # 1) Ensure at least 3 agencies
    agencies = await db.agencies.find({"organization_id": org_id}).to_list(10)
    while len(agencies) < 3:
        now = now_utc()
        idx = len(agencies) + 1
        doc = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": f"Seed Acenta {idx}",
            "slug": f"seed-acenta-{idx}",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        await db.agencies.insert_one(doc)
        agencies.append(doc)

    agencies = agencies[:3]

    # 2) Ensure at least 5 hotels
    hotels = await db.hotels.find({"organization_id": org_id}).to_list(10)
    while len(hotels) < 5:
        now = now_utc()
        idx = len(hotels) + 1
        doc = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": f"Seed Hotel {idx}",
            "city": "İstanbul",
            "country": "TR",
            "active": True,
            "created_at": now,
            "updated_at": now,
        }
        await db.hotels.insert_one(doc)
        hotels.append(doc)

    hotels = hotels[:5]

    # 3) Ensure agency-hotel links with commission
    link_pairs = []
    for ag in agencies:
        for h in hotels:
            link_pairs.append((ag["_id"], h["_id"]))
    random.shuffle(link_pairs)
    link_pairs = link_pairs[:5]

    for agency_id, hotel_id in link_pairs:
        existing = await db.agency_hotel_links.find_one(
            {"organization_id": org_id, "agency_id": agency_id, "hotel_id": hotel_id}
        )
        if not existing:
            now = now_utc()
            await db.agency_hotel_links.insert_one(
                {
                    "_id": str(uuid.uuid4()),
                    "organization_id": org_id,
                    "agency_id": agency_id,
                    "hotel_id": hotel_id,
                    "active": True,
                    "commission_type": "percent",
                    "commission_value": random.choice([8.0, 10.0, 12.0]),
                    "created_at": now,
                    "updated_at": now,
                }
            )

    # 4) Insert demo bookings
    status_choices = ["pending", "confirmed", "rejected", "cancelled"]
    payment_status_choices = ["unpaid", "partially_paid", "paid"]

    created = 0
    today = now_utc().date()

    while created < max(count, 1):
        ag = random.choice(agencies)
        h = random.choice(hotels)

        check_in = today + timedelta(days=random.randint(1, 60))
        check_out = check_in + timedelta(days=random.randint(1, 5))

        gross = random.randint(8000, 25000)
        commission_percent = random.choice([8.0, 10.0, 12.0])
        commission_amount = round(gross * commission_percent / 100.0, 2)
        net_amount = round(gross - commission_amount, 2)

        status = random.choice(status_choices)
        payment_status = random.choice(payment_status_choices)

        booking_id = f"seed_{uuid.uuid4().hex[:10]}"
        now_ts = now_utc()

        doc = {
            "_id": booking_id,
            "organization_id": org_id,
            "agency_id": ag["_id"],
            "agency_name": ag.get("name"),
            "hotel_id": h["_id"],
            "hotel_name": h.get("name"),
            "status": status,
            "channel": "agency_extranet",
            "stay": {
                "check_in": check_in.strftime("%Y-%m-%d"),
                "check_out": check_out.strftime("%Y-%m-%d"),
            },
            "occupancy": {"adults": 2, "children": random.choice([0, 1, 2])},
            "guest": {
                "full_name": f"Seed Guest {created+1}",
                "email": f"seed.guest{created+1}@example.com",
            },
            "rate_snapshot": {
                "price": {
                    "total": float(gross),
                    "currency": "TRY",
                },
                "room_type_label": "Standard Oda",
                "board_code": "BB",
            },
            "gross_amount": float(gross),
            "commission_amount": float(commission_amount),
            "net_amount": float(net_amount),
            "currency": "TRY",
            "commission_type_snapshot": "percent",
            "commission_value_snapshot": commission_percent,
            "commission_reversed": False,
            "payment_status": payment_status,
            "created_at": now_ts - timedelta(days=random.randint(0, 45)),
            "updated_at": now_ts,
            "check_in_date": datetime.combine(check_in, datetime.min.time()),
            "check_out_date": datetime.combine(check_out, datetime.min.time()),
        }

        await db.bookings.insert_one(doc)
        created += 1

    return {"ok": True, "created": created}
