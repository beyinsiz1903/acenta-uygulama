from __future__ import annotations

import os
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc

router = APIRouter(prefix="/api/dev", tags=["dev-seed-match-proxy"])


def _env_value(*keys: str) -> str:
    for k in keys:
        v = os.getenv(k)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""


def _is_production_env() -> bool:
    v = _env_value("ENVIRONMENT", "APP_ENV", "ENV", "STAGE").lower()
    return v in {"prod", "production"}


def _dev_routers_enabled() -> bool:
    return os.getenv("ENABLE_DEV_ROUTERS", "").lower() == "true"


@router.post(
    "/seed/match-proxy",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def seed_match_proxy(
    user=Depends(get_current_user),
    db=Depends(get_db),
    to_hotel_id: Optional[str] = Query(default=None),
):
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

    If `to_hotel_id` is provided, that hotel will be used as the receiving hotel
    (hotel_id/to_hotel_id); otherwise a second hotel will be picked/created.
    """

    if _is_production_env():
        # Hard guard: never allow dev seeds in production even if ENABLE_DEV_ROUTERS was mis-set
        raise HTTPException(status_code=403, detail="DEV_SEED_DISABLED_IN_PRODUCTION")

    if not _dev_routers_enabled():
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

    # 2) Ensure hotels and resolve from/to hotels
    hotels = await db.hotels.find({"organization_id": org_id}).to_list(10)
    hotels_by_id = {str(h["_id"]): h for h in hotels}

    # If explicit to_hotel_id is provided, prefer that as receiving hotel
    to_hotel: Optional[Dict[str, Any]] = None
    if to_hotel_id is not None:
        to_hotel = hotels_by_id.get(str(to_hotel_id))
        if to_hotel is None:
            # Create that hotel id explicitly for deterministic tests
            now = now_utc()
            to_hotel = {
                "_id": str(to_hotel_id),
                "organization_id": org_id,
                "name": "P4 Seed Hotel (explicit)",
                "city": "İstanbul",
                "country": "TR",
                "active": True,
                "created_at": now,
                "updated_at": now,
            }
            await db.hotels.insert_one(to_hotel)
            hotels_by_id[str(to_hotel["_id"])] = to_hotel

    # Ensure at least 2 hotels overall
    hotels = list(hotels_by_id.values())
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
        hotels_by_id[str(hdoc["_id"])] = hdoc

    # Resolve from_hotel and to_hotel
    if to_hotel is None:
        # Pick second hotel as receiving by default
        to_hotel = hotels[1]
    # Use first different hotel as from_hotel if possible
    from_hotel = hotels[0]
    if str(from_hotel["_id"]) == str(to_hotel["_id"]) and len(hotels) >= 2:
        from_hotel = hotels[1]

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
        "dev_seed": True,
    }
