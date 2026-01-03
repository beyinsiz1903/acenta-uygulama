from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc

router = APIRouter(prefix="/api/dev", tags=["dev-seed-users"])


def _is_dev_env() -> bool:
    return os.getenv("ENABLE_DEV_ROUTERS") == "true"


@router.post(
    "/seed/users/hotel",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def seed_hotel_user(hotel_id: str, email: str, password: str = "demo123", user=Depends(get_current_user)):
    """Create a second hotel_admin user for negative testing.

    Only enabled in dev/preview environments.
    """

    if not _is_dev_env():
        raise HTTPException(status_code=403, detail="DEV_SEED_DISABLED")

    db = await get_db()
    org_id = str(user["organization_id"])

    hotel = await db.hotels.find_one({"_id": hotel_id, "organization_id": org_id})
    if not hotel:
        raise HTTPException(status_code=404, detail="HOTEL_NOT_FOUND")

    existing = await db.users.find_one({"organization_id": org_id, "email": email})
    if existing:
        return {"ok": True, "user_id": str(existing["_id"]), "already_exists": True}

    now = now_utc()
    doc = {
        "_id": str(uuid.uuid4()),
        "organization_id": org_id,
        "hotel_id": hotel_id,
        "email": email,
        "password_hash": password,  # NOTE: in real system this should be hashed; for dev only
        "roles": ["hotel_admin"],
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    await db.users.insert_one(doc)

    return {"ok": True, "user_id": doc["_id"], "already_exists": False}
