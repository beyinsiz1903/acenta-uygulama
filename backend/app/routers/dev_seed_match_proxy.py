from __future__ import annotations

import os
import uuid
from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc

router = APIRouter(prefix="/api/dev", tags=["dev-seed-match-proxy"])


def _is_dev_env() -> bool:
    """Allow seeding only in dev/preview environments.

    We use ENABLE_DEV_ROUTERS as primary switch (already used in server.py).
    """

    return os.getenv("ENABLE_DEV_ROUTERS") == "true"


@router.post(
    "/seed/match-proxy",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def seed_match_proxy(user=Depends(get_current_user), db=Depends(get_db)):
    """Seed a minimal agency_catalog_booking_requests document to act as a match proxy.

    This is dev-only and intended for P4 match-outcome/risk testing.
    It will:
    - Ensure at least 1 agency and 2 hotels exist for the organization
    - Insert a single agency_catalog_booking_requests document with:
      - string _id (uuid4)
      - organization_id, agency_id
      - from_hotel_id, to_hotel_id, hotel_id
      - created_at within a reasonable recent window
    - Return identifiers needed by proof scripts.
    """

    if not _is_dev_env():
        raise HTTPException(status_code=403, detail="DEV_SEED_DISABLED")

    org_id = str(user["organization_id"])

    # 1) Ensure at least 1 agency
    agency = await db.agencies.find_one({"organization_id": org_id})
    if not agency:
        now = now_utc()
        agency_doc = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "P4 Seed Acenta",
            "slug": "p4-seed-acenta",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        await db.agencies.insert_one(agency_doc)
        agency = agency_doc

    # 2) Ensure at least 2 hotels
    hotels = await db.hotels.find({"organization_id": org_id}).to_list(2)
    while len(hotels) < 2:
        now = now_utc()
        idx = len(hotels) + 1
        hdoc = {
            "_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": f"P4 Seed Hotel {idx}",
            "city": "İstanbul",
            "country": "TR",
            "active": True,
            "created_at": now,
            "updated_at": now,
        }
        await db.hotels.insert_one(hdoc)
        hotels.append(hdoc)

    from_hotel = hotels[0]
    to_hotel = hotels[1]

    now = now_utc()
    created_at = now - timedelta(days=1)

    match_id = str(uuid.uuid4())

    doc: Dict[str, Any] = {
        "_id": match_id,
        "organization_id": org_id,
        "agency_id": agency["_id"],
        "from_hotel_id": str(from_hotel["_id"]),
        "to_hotel_id": str(to_hotel["_id"]),
        "hotel_id": str(to_hotel["_id"]),
        "guest": {
            "full_name": "P4 Seed Guest",
            "phone": "",
            "email": "p4.seed.guest@example.com",
        },
        "dates": {
            "start": created_at.date().isoformat(),
            "end": (created_at + timedelta(days=2)).date().isoformat(),
        },
        "pax": 2,
        "status": "new",
        "created_at": created_at,
        "updated_at": created_at,
        "reference_code": f"P4-{match_id[:8]}",
    }

    await db.agency_catalog_booking_requests.insert_one(doc)

    return {
        "ok": True,
        "match_id": match_id,
        "to_hotel_id": str(to_hotel["_id"]),
        "from_hotel_id": str(from_hotel["_id"]),
        "organization_id": org_id,
        "agency_id": agency["_id"],
        "created_at": created_at.isoformat(),
    }
